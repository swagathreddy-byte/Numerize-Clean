from django.db import models
import datetime
from .choices import *
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.template.defaultfilters import filesizeformat
import magic
import os
from django.contrib.postgres.fields import JSONField
from smart_selects.db_fields import ChainedManyToManyField
from CustomerManagement.models import *
from Workspace.storage_backend import PrivateMediaStorage
from django.conf import settings


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    d = datetime.date.today()
    mon=d.strftime("%b")
    actualfilename=os.path.basename(filename)
    return 'input/{0}/{1}/{2}'.format(instance.user.username,mon,actualfilename)

@deconstructible
class FileValidator(object):
    error_messages = {
        'max_size': ("Ensure this file size is not greater than %(max_size)s."
                     " Your file size is %(size)s."),
        'min_size': ("Ensure this file size is not less than %(min_size)s. "
                     "Your file size is %(size)s."),
        'content_type': "Files of type %(content_type)s are not supported. Please upload only excel type files",
    }

    def __init__(self, max_size=None, min_size=None, content_types=()):
        self.max_size = max_size
        self.min_size = min_size
        self.content_types = content_types

    def __call__(self, data):
        if self.max_size is not None and data.size > self.max_size:
            params = {
                'max_size': filesizeformat(self.max_size),
                'size': filesizeformat(data.size),
            }
            raise ValidationError(self.error_messages['max_size'],
                                  'max_size', params)

        if self.min_size is not None and data.size < self.min_size:
            params = {
                'min_size': filesizeformat(self.mix_size),
                'size': filesizeformat(data.size)
            }
            raise ValidationError(self.error_messages['min_size'],
                                  'min_size', params)

        if self.content_types:
            content_type = magic.from_buffer(data.read(), mime=True)
            data.seek(0)

            if content_type not in self.content_types:
                params = { 'content_type': content_type }
                raise ValidationError(self.error_messages['content_type'],
                                      'content_type', params)

    def __eq__(self, other):
        return (
                isinstance(other, FileValidator) and
                self.max_size == other.max_size and
                self.min_size == other.min_size and
                self.content_types == other.content_types
        )

validate_file = FileValidator(max_size=1024 * 10000,
                              content_types=('application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))

pdf_file=FileValidator(max_size=1024 * 10000,
                       content_types=('application/pdf'))

# Create your models here.
class Report(models.Model):
    report_type=models.CharField(choices=REPORT_TYPE,max_length=100)
    generated_at=models.DateTimeField(auto_now_add=True)
    status=models.CharField(choices=STATUS_TYPE,max_length=100,default="Initiated")
    month=models.PositiveIntegerField(default=7)
    year=models.PositiveIntegerField(default=2020)
    comments=JSONField(null=True,default=None,blank=True)
    anomalies=JSONField(null=True,default=None,blank=True)
    checklists=JSONField(null=True,default=list,blank=True)
    results=JSONField(null=True,default=None,blank=True)
    qb_api=JSONField(null=True,default=None,blank=True)
    invoice_list=JSONField(null=True,default=list,blank=True)
    tl=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="tl_reports",default=18,limit_choices_to={'groups__name': "TeamLead"},null=True,blank=True)
    qc=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="qc_reports",default=43,limit_choices_to={'groups__name': "QC"})
    crm=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="crm_reports",default=44,limit_choices_to={'groups__name': "CRM"})
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,default=2)
    #customer=models.ForeignKey(Customer,on_delete=models.CASCADE,default="1")
    #legalentity=models.ForeignKey(LegalEntity,on_delete=models.CASCADE,default=None,blank=True,null=True)
    #outlet=models.ForeignKey(Outlet,on_delete=models.CASCADE,default=None,blank=True,null=True)
    #brand=models.ForeignKey(Brand,on_delete=models.CASCADE,default=None,blank=True,null=True)
    customer=JSONField(null=True,default=None,blank=True)
    legalentity=JSONField(null=True,default=None,blank=True)
    outlet=JSONField(null=True,default=None,blank=True)
    brand=JSONField(null=True,default=None,blank=True)
    activity=JSONField(null=True,default=list,blank=True)
    def __str__(self):
        if(self.outlet!=None):
            return "%s-%s-%s-%s-%s" % (self.report_type,self.customer["name"],self.month,self.year,self.outlet["name"])
        else:
            return "%s-%s-%s-%s" % (self.report_type,self.customer["name"],self.month,self.year)


class Payables(models.Model):
    generated_at=models.DateTimeField(auto_now_add=True)
    month=models.PositiveIntegerField(default=7)
    year=models.PositiveIntegerField(default=2020)
    day=models.PositiveIntegerField(default=1)
    results=JSONField(null=True,default=None,blank=True)
    customer=JSONField(null=True,default=None,blank=True)
    legalentity=JSONField(null=True,default=None,blank=True)
    outlet=JSONField(null=True,default=None,blank=True)
    brand=JSONField(null=True,default=None,blank=True)
    def __str__(self):
        return "%s-%s-%s-%s-%s" % (self.legalentity.name,self.customer.name,self.day,self.month,self.year)

class Receivables(models.Model):
    generated_at=models.DateTimeField(auto_now_add=True)
    month=models.PositiveIntegerField(default=7)
    year=models.PositiveIntegerField(default=2020)
    day=models.PositiveIntegerField(default=1)
    results=JSONField(null=True,default=None,blank=True)
    customer=JSONField(null=True,default=None,blank=True)
    legalentity=JSONField(null=True,default=None,blank=True)
    outlet=JSONField(null=True,default=None,blank=True)
    brand=JSONField(null=True,default=None,blank=True)
    def __str__(self):
        return "%s-%s-%s-%s-%s" % (self.legalentity.name,self.customer.name,self.day,self.month,self.year)

class PrivateExcelDocument(models.Model):
    uploaded_at = models.DateField(auto_now_add=True)
    upload = models.FileField(storage=PrivateMediaStorage(),upload_to=user_directory_path,validators=[validate_file])
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    document_link=models.URLField(max_length=400)
    record=models.ForeignKey(Report,on_delete=models.CASCADE,default="1",related_name="excel_attachments")


class PrivatePdfDocument(models.Model):
    uploaded_at = models.DateField(auto_now_add=True)
    upload = models.FileField(storage=PrivateMediaStorage(),upload_to=user_directory_path,validators=[pdf_file])
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    document_link=models.URLField(max_length=400)
    record=models.ForeignKey(Report,on_delete=models.CASCADE,default="1",related_name="pdf_attachments")


class InsightCategory(models.Model):
    name=models.CharField(choices=INSIGHT_CATEGORY,max_length=100)
    def __str__(self):
        return self.name


class InsightsType(models.Model):
    name=models.CharField(choices=INSIGHT_TYPE,max_length=100)
    incategory=models.ManyToManyField(InsightCategory,blank=True, null=True)
    def __str__(self):
        return self.name


class InsightsNotes(models.Model):
    notes=models.TextField(max_length=300)
    category=models.ForeignKey(InsightCategory,on_delete=models.CASCADE)
    type=ChainedManyToManyField(
        InsightsType,
        verbose_name='insighttype',
        horizontal=True,
        chained_field="category",
        chained_model_field="incategory")
    def __str__(self):
        return '%s: %s' % (self.category, self.type.name)