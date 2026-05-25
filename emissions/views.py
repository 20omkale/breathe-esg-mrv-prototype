from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView, UpdateAPIView
from .models import Company, DataSource, EmissionRecord
from .serializers import EmissionRecordSerializer, CompanySerializer
import csv
from io import StringIO
from datetime import datetime

# --- NEW HELPER FUNCTION ---
def safe_float(value, default=0.0):
    """Safely converts messy CSV strings into floats without crashing the server."""
    if not value:
        return default
    try:
        # Strip commas or spaces just in case (e.g., "1,000.50")
        clean_value = str(value).replace(',', '').strip()
        return float(clean_value)
    except (ValueError, TypeError):
        return default

class DataIngestionView(APIView):
    def post(self, request):
        company_id = request.data.get('company_id')
        source_type = request.data.get('source_type')
        raw_csv_data = request.data.get('csv_data')
        
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response({"error": "Company not found. Database might be unseeded."}, status=404)

        data_source = DataSource.objects.create(
            company=company,
            name=f"{source_type} Upload - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            source_type=source_type,
        )

        csv_file = StringIO(raw_csv_data)
        reader = csv.DictReader(csv_file)
        records_created = 0
        
        for row in reader:
            if source_type == 'SAP':
                # Use safe_float instead of standard float
                raw_qty = safe_float(row.get('Volume', 0))
                raw_unit = row.get('Unit', 'Liters')
                fuel_type = row.get('Fuel_Type', 'Unknown Fuel')
                
                conversion_factor = 2.68 if 'diesel' in fuel_type.lower() else 2.3
                
                EmissionRecord.objects.create(
                    company=company,
                    source=data_source,
                    category=fuel_type,
                    scope='SCOPE_1',
                    raw_quantity=raw_qty,
                    raw_unit=raw_unit,
                    normalized_quantity=round(raw_qty * conversion_factor, 2),
                    normalized_unit='kgCO2e',
                    date_of_activity=row.get('Date', '2024-01-01')
                )
                records_created += 1
                
            elif source_type == 'UTILITY':
                raw_qty = safe_float(row.get('kWh_Used', 0))
                conversion_factor = 0.4 
                
                EmissionRecord.objects.create(
                    company=company,
                    source=data_source,
                    category='Electricity',
                    scope='SCOPE_2',
                    raw_quantity=raw_qty,
                    raw_unit='kWh',
                    normalized_quantity=round(raw_qty * conversion_factor, 2),
                    normalized_unit='kgCO2e',
                    date_of_activity=row.get('Bill_Date', '2024-01-01')
                )
                records_created += 1

            elif source_type == 'TRAVEL':
                trip_type = row.get('Trip_Type', 'Unknown')
                distance = safe_float(row.get('Distance_km', 0))
                flight_class = row.get('Flight_Class', 'Economy')
                
                if trip_type.lower() == 'air':
                    category = f"Flight - {flight_class}"
                    conversion_factor = 0.15 if flight_class.lower() == 'economy' else 0.45 
                else:
                    category = "Ground Transport"
                    conversion_factor = 0.12 
                
                EmissionRecord.objects.create(
                    company=company,
                    source=data_source,
                    category=category,
                    scope='SCOPE_3',
                    raw_quantity=distance,
                    raw_unit='km',
                    normalized_quantity=round(distance * conversion_factor, 2),
                    normalized_unit='kgCO2e',
                    date_of_activity=row.get('Date', '2024-01-01')
                )
                records_created += 1    

        return Response({
            "message": f"Successfully processed {records_created} records.",
            "source_id": data_source.id
        }, status=status.HTTP_201_CREATED)

class PendingReviewListView(ListAPIView):
    serializer_class = EmissionRecordSerializer
    def get_queryset(self):
        return EmissionRecord.objects.filter(status='PENDING').order_by('-created_at')

class ReviewRecordView(UpdateAPIView):
    queryset = EmissionRecord.objects.all()
    serializer_class = EmissionRecordSerializer
    lookup_field = 'id'

class CompanyListView(APIView):
    def get(self, request):
        companies = Company.objects.all()
        serializer = CompanySerializer(companies, many=True)
        return Response(serializer.data)