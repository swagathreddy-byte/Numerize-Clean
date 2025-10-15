from django.contrib import admin

# Register your models here.
from .models import *
# Register your models here.

admin.site.register(OcrImageDocument)
admin.site.register(OcrCSVDocument)
admin.site.register(OcrJSONDocument)
admin.site.register(DownloadCache)
