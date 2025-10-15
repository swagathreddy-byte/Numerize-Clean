from .models import *
from rest_framework import serializers
from django.utils import timezone
import pytz

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model=APIEvent
        fields=[]

class QBEventSerializer(serializers.ModelSerializer):
    crm=serializers.CharField(source='crm.username')
    class Meta:
        model=QbEvent
        fields=['name','status','date','message','type','id','crm','legalentity','qb_id']