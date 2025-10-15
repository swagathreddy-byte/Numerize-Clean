from django.db import models
from EmployeeManagement.models import Employee
from django.conf import settings
from django.contrib.postgres.fields import JSONField
# Create your models here.
class Bearer:
    def __init__(self, refreshExpiry, accessToken, tokenType, refreshToken, accessTokenExpiry, idToken=None):
        self.refreshExpiry = refreshExpiry
        self.accessToken = accessToken
        self.tokenType = tokenType
        self.refreshToken = refreshToken
        self.accessTokenExpiry = accessTokenExpiry
        self.idToken = idToken


class APIEvent(models.Model):
    name=models.CharField(max_length=50)
    status=models.BooleanField()
    date=models.DateTimeField(auto_now_add=True)
    message=models.CharField(max_length=200)
    type=models.CharField(max_length=50)

    class Meta:
        abstract = True


class QbEvent(APIEvent):
    legalentity=JSONField(null=True,default=None,blank=True)
    crm=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="crm_qb_events",limit_choices_to={'groups__name': "CRM"},null=True)
    qb_id=models.CharField(max_length=500)
    def _str__(self):
        return "QB- %s" % self.name

    def save(self, *args, **kwargs):
        # self.type="qb"
        super().save(*args, **kwargs)  # Call the "real" save() method.