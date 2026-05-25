from rest_framework import serializers
from .models import Company, DataSource, EmissionRecord

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name']

class EmissionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionRecord
        fields = '__all__'

class DataSourceSerializer(serializers.ModelSerializer):
    # This allows us to fetch a data source and see all its associated records in one go
    records = EmissionRecordSerializer(many=True, read_only=True, source='emissionrecord_set')
    
    class Meta:
        model = DataSource
        fields = '__all__'