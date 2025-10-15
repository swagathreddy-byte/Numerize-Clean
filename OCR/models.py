from django.db import models
from Workspace.storage_backend import OCRStorage
import os
from ReportManagement.models import FileValidator
from django.contrib.auth.models import User
import uuid
from django.contrib.postgres.fields import JSONField

def user_directory_path(instance,filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    actualfilename=os.path.basename(filename)
    print(actualfilename)
    return 'input/{0}/{1}/{2}/{3}'.format(instance.customer.user_account.username,instance.year,instance.month,actualfilename)


img_file=FileValidator(max_size=1024 * 10000,
                       content_types=('image/*','image/png','image/jpeg','image/jpg'))

csv_file=FileValidator(max_size=1024*10000,content_types=('text/csv','text/plain'))

json_file=FileValidator(max_size=1024*10000,content_types=('application/json','text/plain'))

# Create your models here.
class OcrImageDocument(models.Model):
    customer=JSONField(null=True,default=None,blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image_file = models.FileField(storage=OCRStorage(), upload_to=user_directory_path, validators=[img_file])
    month=models.PositiveIntegerField(default=7)
    year=models.PositiveIntegerField(default=2020)
    document_link = models.URLField(max_length=400)

class OcrCSVDocument(models.Model):
    csv_file = models.FileField(storage=OCRStorage(), upload_to=user_directory_path, validators=[csv_file])
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    customer=JSONField(null=True,default=None,blank=True)
    month=models.PositiveIntegerField(default=7)
    year=models.PositiveIntegerField(default=2020)
    document_link = models.URLField(max_length=400)

class OcrJSONDocument(models.Model):
    json_file = models.FileField(storage=OCRStorage(), upload_to=user_directory_path, validators=[json_file])
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    customer=JSONField(null=True,default=None,blank=True)
    month=models.PositiveIntegerField(default=7)
    year=models.PositiveIntegerField(default=2020)
    document_link = models.URLField(max_length=400)

class DownloadCache(models.Model):
    foldername=models.TextField(max_length=120,unique=True)
    generated_at = models.DateTimeField(auto_now_add=True)