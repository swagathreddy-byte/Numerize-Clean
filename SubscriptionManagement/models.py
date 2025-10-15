from django.db import models
from .choices import *
from django.contrib.postgres.fields import JSONField
from Workspace.utilities import *
# Create your models here.
class Subscription(models.Model):
    subscription=JSONField(default=initiatize_subscription)






