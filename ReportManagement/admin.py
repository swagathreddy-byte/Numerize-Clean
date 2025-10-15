from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(Report)
admin.site.register(Payables)
admin.site.register(Receivables)
admin.site.register(PrivatePdfDocument)
admin.site.register(PrivateExcelDocument)
admin.site.register(InsightCategory)
admin.site.register(InsightsType)
admin.site.register(InsightsNotes)
