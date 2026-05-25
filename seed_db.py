"""
Database seed script.

Run this after migrations to create the admin user, the test company,
and the emission factors table. Designed to be idempotent — safe to run
multiple times on the same database (uses get_or_create throughout).

Emission factor sources:
- Diesel, Petrol, CNG:      DEFRA 2024 Greenhouse Gas Reporting Conversion Factors
- Grid Electricity (India): CEA CO2 Baseline Database, Version 18 (FY 2022-23)
- Flights:                  DEFRA 2024 Table 10 (Aviation), with radiative forcing
- Hotel:                    GHG Protocol Scope 3 Calculation Guidance, Category 6
- Taxi/Car, Rail:           DEFRA 2024 Table 6 & Table 9
"""

import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from emissions.models import Company, EmissionFactor


def seed():
    # ── Admin user ───────────────────────────────────────────────────────────
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@breatheesg.com', 'Breathe2026!')
        print('Created admin user (admin / Breathe2026!)')
    else:
        print('Admin user already exists')

    # ── Tenant company ───────────────────────────────────────────────────────
    company, created = Company.objects.get_or_create(
        slug='abc-construction',
        defaults={
            'name': 'ABC Construction PVT. LTD',
            'reporting_year': 2026,
        }
    )
    if created:
        print(f'Created company: {company.name} (ID: {company.id})')
    else:
        print(f'Company already exists: {company.name} (ID: {company.id})')

    # ── Emission factors ─────────────────────────────────────────────────────
    #
    # Factor selection rationale:
    #
    # DEFRA vs EPA vs IPCC: DEFRA (UK) factors are the most commonly used
    # in Indian ESG consulting for two reasons — they're published annually
    # with a clear versioning system (April release), and they cover the
    # widest range of activity types including India-specific modes like
    # three-wheelers. The GHG Protocol explicitly recommends DEFRA factors
    # when national-specific factors aren't available.
    #
    # Indian grid electricity: We use the CEA Combined Margin factor rather
    # than DEFRA's UK grid factor because India's grid is roughly 2x more
    # carbon-intensive than the UK's. Using the UK factor here would
    # understate Scope 2 by ~50%.
    #
    # Radiative forcing for flights: DEFRA 2024 includes RF in Table 10.
    # RF accounts for the warming effect of contrails and other non-CO2
    # impacts at altitude, which roughly doubles the climate impact of
    # flying vs. the CO2 alone. We include it because the GHG Protocol
    # Scope 3 Technical Guidance recommends including RF for air travel.
    #
    FACTORS = [
        {
            'activity_type': 'Diesel',
            'unit_from':     'L',
            'factor_value':  '2.687960',
            'source_name':   'DEFRA 2024 GHG Conversion Factors — Table 3a, Fuel Combustion',
            'source_url':    'https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024',
            'valid_from':    date(2024, 4, 1),
            'notes':         'kg CO2e per litre of diesel. Includes CO2, CH4, N2O. Market-based approach.',
        },
        {
            'activity_type': 'Petrol',
            'unit_from':     'L',
            'factor_value':  '2.316400',
            'source_name':   'DEFRA 2024 GHG Conversion Factors — Table 3a, Fuel Combustion',
            'source_url':    'https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024',
            'valid_from':    date(2024, 4, 1),
            'notes':         'kg CO2e per litre of motor petrol (motor spirit). Includes CO2, CH4, N2O.',
        },
        {
            'activity_type': 'CNG',
            'unit_from':     'kg',
            'factor_value':  '2.544000',
            'source_name':   'DEFRA 2024 GHG Conversion Factors — Table 3a, Fuel Combustion',
            'source_url':    'https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024',
            'valid_from':    date(2024, 4, 1),
            'notes':         'kg CO2e per kg of compressed natural gas.',
        },
        {
            'activity_type': 'Furnace Oil',
            'unit_from':     'L',
            'factor_value':  '2.763000',
            'source_name':   'DEFRA 2024 GHG Conversion Factors — Table 3a, Fuel Combustion',
            'source_url':    'https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024',
            'valid_from':    date(2024, 4, 1),
            'notes':         'kg CO2e per litre of fuel oil (residual). Used for large industrial burners.',
        },
        {
            'activity_type': 'Grid Electricity - India',
            'unit_from':     'kWh',
            'factor_value':  '0.716000',
            'source_name':   'CEA CO2 Baseline Database for India — Version 18 (FY 2022-23)',
            'source_url':    'https://cea.nic.in/old/reports/others/thermal/tpece/cdm_co2/user_guide_ver18.pdf',
            'valid_from':    date(2023, 4, 1),
            'notes':         'Combined Margin (CM) factor for the Indian grid. CO2 only — CH4 and N2O from Indian grid are negligible per CEA methodology.',
        },
        {
            'activity_type': 'Flight - Economy Short-Haul',
            'unit_from':     'km',
            'factor_value':  '0.151000',
            'source_name':   'DEFRA 2024 GHG Conversion Factors — Table 10, Aviation',
            'source_url':    'https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024',
            'valid_from':    date(2024, 4, 1),
            'notes':         'kg CO2e per passenger-km, economy, short-haul (<1500 km). Includes radiative forcing (RF multiplier ~1.9x applied).',
        },
        {
            'activity_type': 'Flight - Economy Long-Haul',
            'unit_from':     'km',
            'factor_value':  '0.195000',
            'source_name':   'DEFRA 2024 GHG Conversion Factors — Table 10, Aviation',
            'source_url':    'https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024',
            'valid_from':    date(2024, 4, 1),
            'notes':         'kg CO2e per passenger-km, economy, long-haul (>=1500 km). Includes RF.',
        },
        {
            'activity_type': 'Flight - Business Short-Haul',
            'unit_from':     'km',
            'factor_value':  '0.228600',
            'source_name':   'DEFRA 2024 GHG Conversion Factors — Table 10, Aviation',
            'source_url':    'https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024',
            'valid_from':    date(2024, 4, 1),
            'notes':         'Business class seat area allocation is ~1.5x economy on short-haul. With RF.',
        },
        {
            'activity_type': 'Flight - Business Long-Haul',
            'unit_from':     'km',
            'factor_value':  '0.429000',
            'source_name':   'DEFRA 2024 GHG Conversion Factors — Table 10, Aviation',
            'source_url':    'https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024',
            'valid_from':    date(2024, 4, 1),
            'notes':         'Business class long-haul is ~2.2x economy because of seat area allocation method. With RF.',
        },
        {
            'activity_type': 'Flight - First Long-Haul',
            'unit_from':     'km',
            'factor_value':  '0.616000',
            'source_name':   'DEFRA 2024 GHG Conversion Factors — Table 10, Aviation',
            'source_url':    'https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024',
            'valid_from':    date(2024, 4, 1),
            'notes':         'First class factor is highest due to largest seat/cabin area. With RF.',
        },
        {
            'activity_type': 'Hotel Stay',
            'unit_from':     'nights',
            'factor_value':  '20.800000',
            'source_name':   'GHG Protocol Scope 3 Calculation Guidance v1.4 — Category 6, Business Travel',
            'source_url':    'https://ghgprotocol.org/sites/default/files/2023-03/Scope3_Calculation_Guidance_0.pdf',
            'valid_from':    date(2023, 1, 1),
            'notes':         'kg CO2e per hotel-night, Asia-Pacific average. GHG Protocol recommends moving to supplier-specific data when available.',
        },
        {
            'activity_type': 'Taxi/Car',
            'unit_from':     'km',
            'factor_value':  '0.148500',
            'source_name':   'DEFRA 2024 GHG Conversion Factors — Table 6, Average Car',
            'source_url':    'https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024',
            'valid_from':    date(2024, 4, 1),
            'notes':         'Average car, average fuel mix. Used as proxy for taxi and rideshare. kg CO2e per km.',
        },
        {
            'activity_type': 'Rail Travel',
            'unit_from':     'km',
            'factor_value':  '0.035490',
            'source_name':   'DEFRA 2024 GHG Conversion Factors — Table 9, Rail',
            'source_url':    'https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024',
            'valid_from':    date(2024, 4, 1),
            'notes':         'National rail, per passenger-km. Significantly lower than road/air due to electrification.',
        },
    ]

    created_count = 0
    for f_data in FACTORS:
        _, created = EmissionFactor.objects.get_or_create(
            activity_type=f_data['activity_type'],
            valid_from=f_data['valid_from'],
            defaults=f_data,
        )
        if created:
            created_count += 1
            print(f"  + {f_data['activity_type']} ({f_data['factor_value']} {f_data['unit_from']})")

    print(f'\nSeeded {created_count} new emission factors ({len(FACTORS)} total defined)')
    print('\nAll done.')
    print(f'  Company: {company.name} (use ID={company.id} in the frontend)')
    print('  Admin login: admin / Breathe2026!')


if __name__ == '__main__':
    seed()