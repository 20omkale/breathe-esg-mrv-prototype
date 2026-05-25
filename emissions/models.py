from django.db import models
from django.contrib.auth.models import User

class Company(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class DataSource(models.Model):
    SOURCE_TYPES = (
        ('SAP', 'SAP Export'),
        ('UTILITY', 'Utility Portal'),
        ('TRAVEL', 'Corporate Travel API'),
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    raw_file_reference = models.CharField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"{self.company.name} - {self.name}"

class EmissionRecord(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved for Audit'),
        ('REJECTED', 'Rejected / Suspicious'),
    )
    SCOPE_CHOICES = (
        ('SCOPE_1', 'Scope 1 (Direct)'),
        ('SCOPE_2', 'Scope 2 (Indirect - Electricity)'),
        ('SCOPE_3', 'Scope 3 (Value Chain / Travel)'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    
    category = models.CharField(max_length=100)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES)
    
    raw_quantity = models.FloatField()
    raw_unit = models.CharField(max_length=50)
    
    normalized_quantity = models.FloatField(help_text="Converted to standard unit (e.g., kgCO2e or kWh)")
    normalized_unit = models.CharField(max_length=50, default="kgCO2e")
    
    date_of_activity = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    audit_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_by = models.ForeignKey(User, related_name='reviewed_records', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.category} - {self.normalized_quantity} {self.normalized_unit}"