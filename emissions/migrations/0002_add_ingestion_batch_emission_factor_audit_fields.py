import django.db.models.deletion
import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Replaces DataSource with IngestionBatch, adds EmissionFactor,
    and extends EmissionRecord with audit trail + flag fields.

    Operation order matters:
    1. Make EmissionRecord.source nullable first (it was CASCADE non-null),
       so we can safely remove DataSource without a FK violation.
    2. Create new models (EmissionFactor, IngestionBatch).
    3. Add new fields to Company and EmissionRecord.
    4. Remove the source field from EmissionRecord.
    5. Delete DataSource.
    """

    dependencies = [
        ('emissions', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: Make EmissionRecord.source nullable so we can drop DataSource
        migrations.AlterField(
            model_name='emissionrecord',
            name='source',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='emissions.datasource',
            ),
        ),

        # Step 2a: Create EmissionFactor
        migrations.CreateModel(
            name='EmissionFactor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity_type', models.CharField(max_length=100)),
                ('unit_from', models.CharField(max_length=20)),
                ('unit_to', models.CharField(default='kgCO2e', max_length=20)),
                ('factor_value', models.DecimalField(decimal_places=6, max_digits=12)),
                ('source_name', models.CharField(max_length=300)),
                ('source_url', models.URLField(blank=True)),
                ('valid_from', models.DateField()),
                ('notes', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-valid_from'],
            },
        ),

        # Step 2b: Create IngestionBatch
        migrations.CreateModel(
            name='IngestionBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_type', models.CharField(
                    choices=[
                        ('SAP', 'SAP Flat File (MB51)'),
                        ('UTILITY', 'Utility Portal CSV'),
                        ('TRAVEL', 'Corporate Travel (Concur)'),
                    ],
                    max_length=20,
                )),
                ('original_filename', models.CharField(blank=True, max_length=255)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('total_rows', models.IntegerField(default=0)),
                ('rows_ingested', models.IntegerField(default=0)),
                ('rows_failed', models.IntegerField(default=0)),
                ('rows_flagged', models.IntegerField(default=0)),
                ('status', models.CharField(
                    choices=[
                        ('PROCESSING', 'Processing'),
                        ('COMPLETE', 'Complete'),
                        ('PARTIAL', 'Partial \u2014 some rows failed'),
                        ('FAILED', 'Failed'),
                    ],
                    default='PROCESSING',
                    max_length=20,
                )),
                ('error_log', models.JSONField(default=list)),
                ('company', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='batches',
                    to='emissions.company',
                )),
                ('uploaded_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name_plural': 'Ingestion Batches',
                'ordering': ['-uploaded_at'],
            },
        ),

        # Step 3a: Add new fields to Company
        migrations.AddField(
            model_name='company',
            name='slug',
            field=models.SlugField(blank=True),
        ),
        migrations.AddField(
            model_name='company',
            name='reporting_year',
            field=models.IntegerField(default=2026),
        ),

        # Step 3b: Add new fields to EmissionRecord
        migrations.AddField(
            model_name='emissionrecord',
            name='batch',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='records',
                to='emissions.ingestionbatch',
            ),
        ),
        migrations.AddField(
            model_name='emissionrecord',
            name='flag',
            field=models.CharField(
                choices=[
                    ('NONE', 'No Flag'),
                    ('SUSPICIOUS', 'Suspicious \u2014 Outlier Detected'),
                    ('DUPLICATE', 'Possible Duplicate'),
                ],
                default='NONE',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='emissionrecord',
            name='flag_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='emissionrecord',
            name='raw_row_data',
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name='emissionrecord',
            name='co2e_kg',
            field=models.FloatField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='emissionrecord',
            name='emission_factor_ref',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='emissions.emissionfactor',
            ),
        ),
        migrations.AddField(
            model_name='emissionrecord',
            name='emission_factor_used',
            field=models.FloatField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='emissionrecord',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # Step 3c: Update scope choice labels to be more descriptive
        migrations.AlterField(
            model_name='emissionrecord',
            name='scope',
            field=models.CharField(
                choices=[
                    ('SCOPE_1', 'Scope 1 \u2014 Direct Combustion'),
                    ('SCOPE_2', 'Scope 2 \u2014 Purchased Electricity'),
                    ('SCOPE_3', 'Scope 3 \u2014 Business Travel'),
                ],
                max_length=20,
            ),
        ),

        # Step 3d: Update status choices
        migrations.AlterField(
            model_name='emissionrecord',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pending Review'),
                    ('APPROVED', 'Approved'),
                    ('REJECTED', 'Rejected'),
                ],
                default='PENDING',
                max_length=20,
            ),
        ),

        # Step 4: Remove the old source FK from EmissionRecord
        migrations.RemoveField(
            model_name='emissionrecord',
            name='source',
        ),

        # Step 5: Delete DataSource — no longer needed
        migrations.DeleteModel(
            name='DataSource',
        ),
    ]
