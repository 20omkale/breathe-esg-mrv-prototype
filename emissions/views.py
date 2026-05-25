from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView
from django.db.models import Sum, Count
from django.utils import timezone

from .models import Company, IngestionBatch, EmissionRecord, EmissionFactor
from .serializers import EmissionRecordSerializer, CompanySerializer, IngestionBatchSerializer

import csv
from io import TextIOWrapper
from datetime import datetime


# ─── SAP MB51 field name normalisation ───────────────────────────────────────
#
# SAP MB51 (Material Document List) exports field names in the language of the
# SAP system's logon language setting. German-configured SAP systems (very
# common in manufacturing clients) output German column names. Same data,
# different headers. This map handles both so we don't need the client to
# manually rename columns before uploading.
#
# Source: SAP Help Portal, transaction MB51, field catalog documentation.
# BUDAT = Buchungsdatum (Posting Date)
# MENGE = Menge (Quantity)
# MEINS = Mengeneinheit (Unit of Measure)
# MAKTX = Materialkurztext (Material Short Text / Description)
# WERKS = Werk (Plant)
# MATNR = Materialnummer (Material Number)
# BWART = Bewegungsart (Movement Type) — 201 = GI for cost center (consumption)
#
SAP_FIELD_MAP = {
    # German → internal key
    'Menge':              'quantity',
    'ME':                 'unit',
    'MEINS':              'unit',
    'Materialbezeichnung':'description',
    'MAKTX':              'description',
    'Buchungsdatum':      'posting_date',
    'Belegdatum':         'posting_date',
    'BUDAT':              'posting_date',
    'BLDAT':              'posting_date',
    'Werk':               'plant',
    'WERKS':              'plant',
    'Materialnummer':     'material_no',
    'MATNR':              'material_no',
    'Bewegungsart':       'movement_type',
    'BWART':              'movement_type',
    'Kostenstelle':       'cost_center',
    'KOSTL':              'cost_center',
    # English column names (some SAP configs export in English)
    'Volume':             'quantity',
    'Unit':               'unit',
    'Fuel_Type':          'description',
    'Material_Desc':      'description',
    'Posting_Date':       'posting_date',
    'Plant':              'plant',
    'Material_No':        'material_no',
}

# Material description keywords → standardised fuel category
# SAP clients rarely write "Diesel" in the material description — they use
# their own internal codes and descriptions. These keywords cover common
# Indian and international SAP configurations.
FUEL_KEYWORDS = {
    'diesel':       'Diesel',
    'hsd':          'Diesel',       # High Speed Diesel (Indian SAP standard code)
    'high speed':   'Diesel',
    'petrol':       'Petrol',
    'motor spirit': 'Petrol',       # Formal Indian petroleum term
    'gasoline':     'Petrol',
    'cng':          'CNG',
    'compressed natural gas': 'CNG',
    'lng':          'LNG',
    'furnace oil':  'Furnace Oil',
    'fo ':          'Furnace Oil',
    'lpg':          'LPG',
}

# ─── IATA airport pair distances (km, great circle) ──────────────────────────
#
# Concur's Standard Accounting Extract (SAE) gives origin/destination city or
# airport code, NOT distance. You have to compute it yourself.
#
# These distances were calculated using the haversine formula from the
# OurAirports dataset (ourairports.com), which is CC0 licensed.
# I picked the routes that appear in this client's travel data.
# In production this would be a live API call (e.g. OpenFlights, Google Maps
# Distance Matrix) but that adds latency and rate-limit risk to the ingestion
# path, which isn't worth it for a prototype.
#
AIRPORT_DISTANCES = {
    # Domestic India
    ('BOM', 'DEL'): 1148,   ('DEL', 'BOM'): 1148,
    ('BOM', 'BLR'): 844,    ('BLR', 'BOM'): 844,
    ('BOM', 'MAA'): 1033,   ('MAA', 'BOM'): 1033,
    ('BOM', 'HYD'): 624,    ('HYD', 'BOM'): 624,
    ('BOM', 'CCU'): 1659,   ('CCU', 'BOM'): 1659,
    ('DEL', 'BLR'): 1740,   ('BLR', 'DEL'): 1740,
    ('DEL', 'MAA'): 1760,   ('MAA', 'DEL'): 1760,
    ('DEL', 'CCU'): 1305,   ('CCU', 'DEL'): 1305,
    ('DEL', 'HYD'): 1251,   ('HYD', 'DEL'): 1251,
    ('BLR', 'HYD'): 499,    ('HYD', 'BLR'): 499,
    ('BOM', 'GOI'): 449,    ('GOI', 'BOM'): 449,
    # International
    ('BOM', 'DXB'): 1929,   ('DXB', 'BOM'): 1929,
    ('BOM', 'LHR'): 7190,   ('LHR', 'BOM'): 7190,
    ('DEL', 'LHR'): 6710,   ('LHR', 'DEL'): 6710,
    ('BOM', 'SIN'): 4007,   ('SIN', 'BOM'): 4007,
    ('BLR', 'SIN'): 3150,   ('SIN', 'BLR'): 3150,
    ('DEL', 'JFK'): 11760,  ('JFK', 'DEL'): 11760,
    ('BOM', 'FRA'): 6260,   ('FRA', 'BOM'): 6260,
    ('DEL', 'FRA'): 5857,   ('FRA', 'DEL'): 5857,
    ('BOM', 'CDG'): 6666,   ('CDG', 'BOM'): 6666,
    ('DEL', 'SIN'): 4145,   ('SIN', 'DEL'): 4145,
}


def safe_float(value, default=0.0):
    """
    Parse messy number strings. SAP German locale uses period as thousands
    separator and comma as decimal: '1.234,56' means 1234.56.
    English locale is the opposite. We try to figure out which is which
    based on the positions of the separators.
    """
    if not value:
        return default
    try:
        cleaned = str(value).strip().replace('\xa0', '')  # strip non-breaking spaces
        if ',' in cleaned and '.' in cleaned:
            # Whichever comes last is the decimal separator
            if cleaned.rindex(',') > cleaned.rindex('.'):
                # German: 1.234,56
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                # English: 1,234.56
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            parts = cleaned.split(',')
            # If > 2 digits after comma, it's probably a thousands separator
            if len(parts[-1]) > 2:
                cleaned = cleaned.replace(',', '')
            else:
                cleaned = cleaned.replace(',', '.')
        return float(cleaned)
    except (ValueError, TypeError):
        return default


def parse_date(date_str):
    """
    Try multiple date formats. SAP German configs default to DD.MM.YYYY.
    Utility portals tend to use YYYY-MM-DD. We try both, plus a few others.
    """
    if not date_str or not str(date_str).strip():
        return None
    formats = [
        '%d.%m.%Y',   # SAP German default
        '%Y-%m-%d',   # ISO 8601 (utility portals, Concur)
        '%d/%m/%Y',   # European
        '%m/%d/%Y',   # US format
        '%d-%m-%Y',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(str(date_str).strip(), fmt).date()
        except ValueError:
            continue
    return None


def detect_fuel_type(description):
    """Map SAP material descriptions to standardised fuel categories."""
    if not description:
        return None
    desc_lower = description.lower()
    for keyword, fuel_name in FUEL_KEYWORDS.items():
        if keyword in desc_lower:
            return fuel_name
    # Return the raw description trimmed — better than 'Unknown'
    return description.strip()[:80]


def get_emission_factor(activity_type):
    """Fetch the most recently valid emission factor for a given activity."""
    return (
        EmissionFactor.objects
        .filter(activity_type__iexact=activity_type)
        .order_by('-valid_from')
        .first()
    )


def check_for_outlier(company, category, value):
    """
    Flag a record as suspicious if its value is more than 2.5x the average
    of the last 20 records for that category and company.

    This is a simple heuristic, not a statistical test. The point is to
    catch obvious data entry errors (e.g., 45,000 kWh when the norm is 4,500)
    before they go to the auditor. The analyst still has to make the call —
    we just surface it.

    Threshold of 2.5x is intentionally conservative to avoid false positives
    on seasonal variation.
    """
    recent_values = list(
        EmissionRecord.objects
        .filter(company=company, category=category, status__in=['APPROVED', 'PENDING'])
        .order_by('-created_at')
        .values_list('raw_quantity', flat=True)[:20]
    )
    if len(recent_values) < 3:
        return False, ''
    avg = sum(recent_values) / len(recent_values)
    if avg > 0 and value > avg * 2.5:
        ratio = value / avg
        return True, f"Value {value:.1f} is {ratio:.1f}× the recent average of {avg:.1f}. Verify source document."
    return False, ''


# ─── Ingestion view ───────────────────────────────────────────────────────────

class DataIngestionView(APIView):

    def post(self, request):
        company_id = request.data.get('company_id')
        source_type = request.data.get('source_type')
        uploaded_file = request.FILES.get('file')

        if not uploaded_file:
            return Response({'error': 'No file provided.'}, status=400)

        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response({'error': 'Company not found.'}, status=404)

        batch = IngestionBatch.objects.create(
            company=company,
            source_type=source_type,
            original_filename=uploaded_file.name,
            status='PROCESSING',
        )

        errors = []
        records_created = 0
        rows_flagged = 0

        try:
            # utf-8-sig handles files with a BOM, which Excel/SAP sometimes adds
            reader = csv.DictReader(TextIOWrapper(uploaded_file, encoding='utf-8-sig'))
            rows = list(reader)
            batch.total_rows = len(rows)

            for i, row in enumerate(rows, start=2):  # row 1 = header
                try:
                    record = None
                    if source_type == 'SAP':
                        record = self._ingest_sap_row(row, company, batch)
                    elif source_type == 'UTILITY':
                        record = self._ingest_utility_row(row, company, batch)
                    elif source_type == 'TRAVEL':
                        record = self._ingest_travel_row(row, company, batch)

                    if record:
                        records_created += 1
                        if record.flag == 'SUSPICIOUS':
                            rows_flagged += 1

                except Exception as exc:
                    errors.append({
                        'row': i,
                        'error': str(exc),
                        'data': {k: v for k, v in row.items()},
                    })

        except Exception as exc:
            batch.status = 'FAILED'
            batch.error_log = [{'error': str(exc)}]
            batch.save()
            return Response({'error': f'Could not read file: {exc}'}, status=400)

        batch.rows_ingested = records_created
        batch.rows_failed = len(errors)
        batch.rows_flagged = rows_flagged
        batch.error_log = errors
        batch.status = 'PARTIAL' if errors else 'COMPLETE'
        batch.save()

        return Response({
            'batch_id': batch.id,
            'rows_ingested': records_created,
            'rows_failed': len(errors),
            'rows_flagged': rows_flagged,
            'errors': errors[:10],
        }, status=201)

    def _normalise_sap_row(self, row):
        """Map German/English SAP field names to a consistent internal dict."""
        out = {}
        for key, value in row.items():
            mapped_key = SAP_FIELD_MAP.get(key.strip(), key.strip().lower().replace(' ', '_'))
            out[mapped_key] = (value or '').strip()
        return out

    def _ingest_sap_row(self, row, company, batch):
        """
        Parse one row from an SAP MB51 flat file export.

        MB51 is SAP's Material Document List transaction. We're interested in
        movement type 201 (Goods Issue against a cost center), which is how
        fuel consumption is tracked in SAP MM — the fuel tank is a storage
        location, and each fill of a vehicle/generator creates a 201 movement.

        The tricky parts:
        - Date format: German SAP = DD.MM.YYYY, English SAP = YYYY-MM-DD
        - Unit: most Indian SAP configs use L (litres), but we've also seen
          M3 (cubic metres) for bulk storage and KG for CNG/LPG
        - Material description is an internal code ('Diesel HSD') not a
          standardised fuel name, so we detect fuel type from keywords
        """
        n = self._normalise_sap_row(row)

        quantity = safe_float(n.get('quantity') or n.get('menge', ''))
        raw_unit = (n.get('unit') or n.get('meins') or 'L').strip().upper()
        description = n.get('description') or n.get('maktx') or ''
        date_str = n.get('posting_date') or n.get('budat') or ''

        if not quantity or quantity <= 0:
            raise ValueError(f"Missing or zero quantity — row skipped")

        activity_date = parse_date(date_str)
        if not activity_date:
            raise ValueError(f"Could not parse date: '{date_str}' (tried DD.MM.YYYY, YYYY-MM-DD)")

        fuel_type = detect_fuel_type(description)
        if not fuel_type:
            raise ValueError(f"Could not determine fuel type from description: '{description}'")

        # Unit normalisation to litres where possible
        norm_qty = quantity
        norm_unit = raw_unit
        if raw_unit in ('M3', 'M³', 'CBM'):
            norm_qty = quantity * 1000
            norm_unit = 'L'
        elif raw_unit == 'GAL':
            norm_qty = round(quantity * 3.785, 4)
            norm_unit = 'L'
        # KG stays as KG for CNG/LPG — factor is per KG

        factor = get_emission_factor(fuel_type)
        if not factor:
            raise ValueError(f"No emission factor for '{fuel_type}'. Add it to the EmissionFactor table.")

        co2e_kg = round(norm_qty * factor.factor_value, 4)
        is_outlier, reason = check_for_outlier(company, fuel_type, norm_qty)

        return EmissionRecord.objects.create(
            company=company,
            batch=batch,
            category=fuel_type,
            scope='SCOPE_1',
            raw_quantity=quantity,
            raw_unit=raw_unit,
            raw_row_data=dict(row),
            normalized_quantity=norm_qty,
            normalized_unit=norm_unit,
            co2e_kg=co2e_kg,
            emission_factor_ref=factor,
            emission_factor_used=float(factor.factor_value),
            date_of_activity=activity_date,
            flag='SUSPICIOUS' if is_outlier else 'NONE',
            flag_reason=reason,
        )

    def _ingest_utility_row(self, row, company, batch):
        """
        Parse one row from a utility portal CSV export.

        Key insight from researching real utility exports: billing periods
        almost never align with calendar months. A meter read taken on
        22 Jan and again on 19 Feb covers 28 days, but the month of January
        has 31. If you just use the bill date as the activity date, your
        monthly totals will be wrong.

        We use the midpoint of the billing period as the activity date.
        This isn't perfect (the consumption isn't uniformly distributed),
        but it's more correct than just using the end date, and it avoids
        the double-counting problem you get when a billing period spans
        two reporting months.

        Estimated reads are flagged automatically. The utility will send a
        corrected actual reading in the following bill — if an analyst
        approves an estimated read and then the corrected read comes in,
        you'll double-count that electricity. Better to flag and hold.
        """
        kwh = safe_float(row.get('Units_Consumed_kWh') or row.get('kWh_Used', ''))
        if not kwh or kwh <= 0:
            raise ValueError("Missing or zero kWh reading")

        period_start = parse_date(row.get('Period_Start', ''))
        period_end = parse_date(row.get('Period_End') or row.get('Bill_Date', ''))

        if not period_end:
            raise ValueError(f"No billing period date found in row")

        if period_start and period_end:
            from datetime import timedelta
            days = (period_end - period_start).days
            activity_date = period_start + timedelta(days=days // 2)
        else:
            activity_date = period_end

        read_type = row.get('Read_Type', 'ACTUAL').strip().upper()

        factor = get_emission_factor('Grid Electricity - India')
        if not factor:
            raise ValueError("No emission factor for 'Grid Electricity - India'. Run seed_db.py.")

        co2e_kg = round(kwh * factor.factor_value, 4)
        is_outlier, reason = check_for_outlier(company, 'Electricity', kwh)

        flag = 'NONE'
        flag_reason = ''

        if is_outlier:
            flag = 'SUSPICIOUS'
            flag_reason = reason

        if read_type == 'ESTIMATED':
            flag = 'SUSPICIOUS'
            suffix = ' | Estimated meter read — utility will issue correction next cycle, approve only after verifying'
            flag_reason = (flag_reason + suffix) if flag_reason else suffix.strip(' | ')

        return EmissionRecord.objects.create(
            company=company,
            batch=batch,
            category='Electricity',
            scope='SCOPE_2',
            raw_quantity=kwh,
            raw_unit='kWh',
            raw_row_data=dict(row),
            normalized_quantity=kwh,
            normalized_unit='kWh',
            co2e_kg=co2e_kg,
            emission_factor_ref=factor,
            emission_factor_used=float(factor.factor_value),
            date_of_activity=activity_date,
            flag=flag,
            flag_reason=flag_reason,
        )

    def _ingest_travel_row(self, row, company, batch):
        """
        Parse one row from a Concur Standard Accounting Extract (SAE).

        Concur's SAE doesn't include distance. You get the origin and
        destination as city names or IATA codes depending on configuration.
        We use the IATA codes and look up distance from our airport table.

        Hotel rows use 'Nights' as the activity quantity.
        Ground transport (taxi, train) uses a Distance_km column — for these
        the client's travel desk fills in the distance manually, which is
        the Concur standard practice for ground transport.

        Multi-leg flights are flagged. A single Concur row can represent a
        BOM→FRA→LHR itinerary as one line item with cabin class = 'Economy'.
        If the passenger flew economy on the first leg and business on the
        second, the per-km factor will be wrong. We flag these and let the
        analyst decide.
        """
        expense_type = row.get('Expense_Type', '').strip()
        expense_date = parse_date(row.get('Expense_Date') or row.get('Date', ''))

        if not expense_date:
            raise ValueError(f"No valid date in row")

        # ── Air travel ───────────────────────────────────────────────────────
        if expense_type.lower() in ('air travel', 'air', 'flight'):
            origin = row.get('Origin_IATA', '').strip().upper()
            dest = row.get('Dest_IATA', '').strip().upper()
            cabin = row.get('Cabin_Class', 'Economy').strip()

            if not origin or not dest:
                raise ValueError("Air travel row missing Origin_IATA or Dest_IATA")

            distance_km = AIRPORT_DISTANCES.get((origin, dest))
            if not distance_km:
                raise ValueError(
                    f"Route {origin}→{dest} not in distance lookup table. "
                    f"Add it to AIRPORT_DISTANCES in views.py, or pre-compute using the haversine formula."
                )

            # DEFRA 2024 Table 10 split: <1500 km = short-haul, ≥1500 km = long-haul
            cabin_lower = cabin.lower()
            if distance_km < 1500:
                factor_name = f"Flight - {'Business' if 'business' in cabin_lower else 'Economy'} Short-Haul"
            else:
                if 'first' in cabin_lower:
                    factor_name = 'Flight - First Long-Haul'
                elif 'business' in cabin_lower:
                    factor_name = 'Flight - Business Long-Haul'
                else:
                    factor_name = 'Flight - Economy Long-Haul'

            factor = get_emission_factor(factor_name)
            if not factor:
                raise ValueError(f"No emission factor for '{factor_name}'")

            co2e_kg = round(distance_km * float(factor.factor_value), 4)

            legs = str(row.get('Legs', '1')).strip()
            is_multi_leg = legs not in ('', '1')

            haul = 'Short' if distance_km < 1500 else 'Long'
            category = f"Flight - {cabin} ({haul}-haul, {origin}→{dest})"

            return EmissionRecord.objects.create(
                company=company,
                batch=batch,
                category=category,
                scope='SCOPE_3',
                raw_quantity=distance_km,
                raw_unit='km',
                raw_row_data=dict(row),
                normalized_quantity=distance_km,
                normalized_unit='km',
                co2e_kg=co2e_kg,
                emission_factor_ref=factor,
                emission_factor_used=float(factor.factor_value),
                date_of_activity=expense_date,
                flag='SUSPICIOUS' if is_multi_leg else 'NONE',
                flag_reason=(
                    f"Multi-leg journey ({legs} legs) — cabin class may differ across legs, "
                    f"verify per-leg details in Concur trip report"
                ) if is_multi_leg else '',
            )

        # ── Hotel ────────────────────────────────────────────────────────────
        elif expense_type.lower() in ('hotel', 'accommodation', 'lodging'):
            nights = safe_float(row.get('Nights', '1'))
            if nights <= 0:
                nights = 1.0

            factor = get_emission_factor('Hotel Stay')
            if not factor:
                raise ValueError("No emission factor for 'Hotel Stay'")

            co2e_kg = round(nights * factor.factor_value, 4)

            return EmissionRecord.objects.create(
                company=company,
                batch=batch,
                category='Hotel Stay',
                scope='SCOPE_3',
                raw_quantity=nights,
                raw_unit='nights',
                raw_row_data=dict(row),
                normalized_quantity=nights,
                normalized_unit='nights',
                co2e_kg=co2e_kg,
                emission_factor_ref=factor,
                emission_factor_used=float(factor.factor_value),
                date_of_activity=expense_date,
            )

        # ── Ground transport ─────────────────────────────────────────────────
        elif expense_type.lower() in ('taxi', 'car', 'ground transport', 'uber', 'cab', 'train', 'rail'):
            distance = safe_float(row.get('Distance_km', '') or row.get('Distance', ''))
            if distance <= 0:
                raise ValueError(f"Ground transport row missing distance")

            is_rail = expense_type.lower() in ('train', 'rail')
            factor_name = 'Rail Travel' if is_rail else 'Taxi/Car'

            factor = get_emission_factor(factor_name)
            if not factor:
                raise ValueError(f"No emission factor for '{factor_name}'")

            co2e_kg = round(distance * factor.factor_value, 4)

            return EmissionRecord.objects.create(
                company=company,
                batch=batch,
                category=expense_type.title(),
                scope='SCOPE_3',
                raw_quantity=distance,
                raw_unit='km',
                raw_row_data=dict(row),
                normalized_quantity=distance,
                normalized_unit='km',
                co2e_kg=co2e_kg,
                emission_factor_ref=factor,
                emission_factor_used=float(factor.factor_value),
                date_of_activity=expense_date,
            )

        else:
            raise ValueError(f"Unrecognised Expense_Type: '{expense_type}'")


# ─── Other views ──────────────────────────────────────────────────────────────

class CompanyListView(APIView):
    def get(self, request):
        return Response(CompanySerializer(Company.objects.all(), many=True).data)


class RecordsListView(ListAPIView):
    """
    Full record list with optional filters. The frontend uses this for the
    main table view, filtering by scope/status/source_type/flag.
    """
    serializer_class = EmissionRecordSerializer

    def get_queryset(self):
        qs = EmissionRecord.objects.select_related('batch', 'emission_factor_ref').all()
        params = self.request.query_params
        if params.get('scope'):
            qs = qs.filter(scope=params['scope'])
        if params.get('status'):
            qs = qs.filter(status=params['status'])
        if params.get('source_type'):
            qs = qs.filter(batch__source_type=params['source_type'])
        if params.get('flag'):
            qs = qs.filter(flag=params['flag'])
        if params.get('company_id'):
            qs = qs.filter(company_id=params['company_id'])
        return qs.order_by('-created_at')


class ReviewRecordView(APIView):
    def patch(self, request, pk):
        try:
            record = EmissionRecord.objects.get(pk=pk)
        except EmissionRecord.DoesNotExist:
            return Response({'error': 'Record not found'}, status=404)

        new_status = request.data.get('status')
        if new_status not in ('APPROVED', 'REJECTED', 'PENDING'):
            return Response({'error': 'Invalid status'}, status=400)

        record.status = new_status
        audit_notes = request.data.get('audit_notes', '').strip()
        if audit_notes:
            record.audit_notes = audit_notes
        record.reviewed_at = timezone.now()
        record.save()
        return Response(EmissionRecordSerializer(record).data)


class StatsView(APIView):
    """
    Dashboard summary KPIs: tCO2e by scope, counts by review status.
    Filtered by company_id to stay multi-tenant safe.
    """
    def get(self, request):
        company_id = request.query_params.get('company_id')
        qs = EmissionRecord.objects.all()
        if company_id:
            qs = qs.filter(company_id=company_id)

        scope_totals = {}
        for scope in ('SCOPE_1', 'SCOPE_2', 'SCOPE_3'):
            total = (
                qs.filter(scope=scope, status='APPROVED')
                .aggregate(t=Sum('co2e_kg'))['t'] or 0
            )
            scope_totals[scope] = round(total / 1000, 3)  # convert kg → tonnes

        counts = qs.values('status').annotate(n=Count('id'))
        status_map = {c['status']: c['n'] for c in counts}

        return Response({
            'scope_totals_tco2e': scope_totals,
            'pending':  status_map.get('PENDING', 0),
            'approved': status_map.get('APPROVED', 0),
            'rejected': status_map.get('REJECTED', 0),
            'flagged':  qs.filter(flag='SUSPICIOUS').count(),
        })


class BatchListView(ListAPIView):
    serializer_class = IngestionBatchSerializer

    def get_queryset(self):
        qs = IngestionBatch.objects.all()
        company_id = self.request.query_params.get('company_id')
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs.order_by('-uploaded_at')

