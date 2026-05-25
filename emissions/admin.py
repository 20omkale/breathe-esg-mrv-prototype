from django.contrib import admin
from .models import Company, EmissionFactor, IngestionBatch, EmissionRecord


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'reporting_year', 'created_at']


@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    list_display = ['activity_type', 'factor_value', 'unit_from', 'source_name', 'valid_from']
    list_filter = ['unit_from', 'valid_from']


@admin.register(IngestionBatch)
class IngestionBatchAdmin(admin.ModelAdmin):
    list_display = ['company', 'source_type', 'original_filename', 'uploaded_at',
                    'total_rows', 'rows_ingested', 'rows_failed', 'status']
    list_filter = ['source_type', 'status']
    readonly_fields = ['error_log']


@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = ['category', 'scope', 'co2e_kg', 'date_of_activity',
                    'status', 'flag', 'company']
    list_filter = ['scope', 'status', 'flag', 'batch__source_type']
    readonly_fields = ['raw_row_data', 'reviewed_at']