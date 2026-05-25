from rest_framework import serializers
from .models import Company, EmissionRecord, IngestionBatch, EmissionFactor


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'slug', 'reporting_year']


class EmissionFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionFactor
        fields = ['id', 'activity_type', 'unit_from', 'factor_value',
                  'source_name', 'source_url', 'valid_from', 'notes']


class EmissionRecordSerializer(serializers.ModelSerializer):
    # Pull source_type from the related batch so the frontend
    # doesn't need a separate API call to identify where a record came from
    source_type = serializers.SerializerMethodField()
    batch_filename = serializers.SerializerMethodField()

    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'company', 'batch', 'category', 'scope',
            'raw_quantity', 'raw_unit', 'raw_row_data',
            'normalized_quantity', 'normalized_unit', 'co2e_kg',
            'emission_factor_used',
            'date_of_activity', 'status', 'flag', 'flag_reason',
            'audit_notes', 'reviewed_by', 'reviewed_at',
            'created_at', 'updated_at',
            'source_type', 'batch_filename',
        ]

    def get_source_type(self, obj):
        return obj.batch.source_type if obj.batch else None

    def get_batch_filename(self, obj):
        return obj.batch.original_filename if obj.batch else None


class IngestionBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngestionBatch
        fields = [
            'id', 'company', 'source_type', 'original_filename',
            'uploaded_at', 'total_rows', 'rows_ingested',
            'rows_failed', 'rows_flagged', 'status', 'error_log',
        ]