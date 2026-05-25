from django.contrib import admin
from .models import Company, DataSource, EmissionRecord

admin.site.register(Company)
admin.site.register(DataSource)
admin.site.register(EmissionRecord)