from django.db import models
from django.contrib.auth.models import User


class Company(models.Model):
    """
    Top-level tenant. Every table has a FK back to this.
    Multi-tenancy at the app layer means every view filters its queryset
    by company_id — no tenant can ever see another tenant's data because
    we never query without that filter. In production you'd add Postgres
    row-level security on top of this, but app-level scoping is sufficient
    for a prototype.
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, blank=True)
    reporting_year = models.IntegerField(default=2026)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Companies"


class EmissionFactor(models.Model):
    """
    Stores the conversion factors used in CO2e calculations.

    Why a DB table instead of hardcoded constants:

    1. Auditability — an auditor reviewing record #482 can see exactly which
       factor was used: "DEFRA 2024 Table 3a, 2.68796 kg CO2e per litre of
       diesel, valid from April 2024." That's not possible if the number is
       buried in a Python constant.

    2. Factor versioning — DEFRA publishes updated factors every April, CEA
       updates the Indian grid factor annually. When a new version arrives,
       we add a new row with a later valid_from. Old records still point to
       the factor that was current when they were created — we don't
       retroactively change historical calculations.

    3. Snapshot on EmissionRecord — emission_factor_used stores the decimal
       value at time of calculation. Even if this row gets updated later,
       each record knows exactly what math produced its CO2e figure.
    """
    activity_type = models.CharField(max_length=100)
    # e.g. "Diesel", "Grid Electricity - India", "Flight - Economy Long-Haul"

    unit_from = models.CharField(max_length=20)
    # The unit of the raw input: L, kWh, km, nights, kg

    unit_to = models.CharField(max_length=20, default='kgCO2e')

    factor_value = models.DecimalField(max_digits=12, decimal_places=6)

    source_name = models.CharField(max_length=300)
    source_url = models.URLField(blank=True)
    valid_from = models.DateField()
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.activity_type}: {self.factor_value} {self.unit_to}/{self.unit_from}"

    class Meta:
        ordering = ['-valid_from']


class IngestionBatch(models.Model):
    """
    One row per file upload attempt.

    This captures import-level metadata separate from individual record
    data. If a 200-row SAP export has 3 rows that fail to parse, you
    need to know that at the batch level — not just see 197 records appear
    with no explanation for the 3 that vanished.

    error_log stores a list of {row, error, data} dicts so an analyst
    can see exactly which rows failed and why, without reopening the
    original file.
    """
    SOURCE_CHOICES = [
        ('SAP', 'SAP Flat File (MB51)'),
        ('UTILITY', 'Utility Portal CSV'),
        ('TRAVEL', 'Corporate Travel (Concur)'),
    ]
    STATUS_CHOICES = [
        ('PROCESSING', 'Processing'),
        ('COMPLETE', 'Complete'),
        ('PARTIAL', 'Partial — some rows failed'),
        ('FAILED', 'Failed'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='batches')
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    original_filename = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    total_rows = models.IntegerField(default=0)
    rows_ingested = models.IntegerField(default=0)
    rows_failed = models.IntegerField(default=0)
    rows_flagged = models.IntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PROCESSING')
    error_log = models.JSONField(default=list)
    # List of: [{"row": 5, "error": "Unparseable date: '32.13.2026'", "data": {...}}]

    def __str__(self):
        return f"{self.company.name} | {self.source_type} | {self.uploaded_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name_plural = "Ingestion Batches"


class EmissionRecord(models.Model):
    """
    Core table. One row = one normalised emission activity.

    Design principles:
    - raw_quantity / raw_unit: exactly what was in the source file, never
      modified after insert.
    - normalized_quantity / normalized_unit: after unit conversion only
      (e.g. m³ → L). No CO2e here yet.
    - co2e_kg: the final output. = normalized_quantity * emission_factor_used.
    - raw_row_data: the original CSV row as JSON. Analysts can trace any
      number back to the exact source line without reopening the file.
    - emission_factor_used: snapshot of the factor value at calculation time.
      Survives factor table updates — the record always knows what produced it.
    - reviewed_at / reviewed_by: who signed off, and when. Auditors need this
      to confirm data was approved before the reporting deadline.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    SCOPE_CHOICES = [
        ('SCOPE_1', 'Scope 1 — Direct Combustion'),
        ('SCOPE_2', 'Scope 2 — Purchased Electricity'),
        ('SCOPE_3', 'Scope 3 — Business Travel'),
    ]
    FLAG_CHOICES = [
        ('NONE', 'No Flag'),
        ('SUSPICIOUS', 'Suspicious — Outlier Detected'),
        ('DUPLICATE', 'Possible Duplicate'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    batch = models.ForeignKey(
        IngestionBatch, on_delete=models.CASCADE, related_name='records'
    )

    category = models.CharField(max_length=100)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES)

    # Raw values from the source file — frozen at ingestion, never modified
    raw_quantity = models.FloatField()
    raw_unit = models.CharField(max_length=50)
    raw_row_data = models.JSONField(default=dict)

    # Intermediate: after unit normalisation, before CO2e conversion
    normalized_quantity = models.FloatField()
    normalized_unit = models.CharField(max_length=50)

    # Final CO2e output
    co2e_kg = models.FloatField()

    # Factor provenance
    emission_factor_ref = models.ForeignKey(
        EmissionFactor, on_delete=models.SET_NULL, null=True, blank=True
    )
    emission_factor_used = models.FloatField()
    # Snapshot of factor_value at time of calculation

    date_of_activity = models.DateField()

    # Review workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    flag = models.CharField(max_length=20, choices=FLAG_CHOICES, default='NONE')
    flag_reason = models.TextField(blank=True)

    audit_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User, related_name='reviewed_records',
        on_delete=models.SET_NULL, null=True, blank=True
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category} | {self.co2e_kg} kgCO2e | {self.date_of_activity}"

    class Meta:
        ordering = ['-created_at']