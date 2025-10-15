from .models import *
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework import serializers
from django.utils import timezone
import pytz

class ReportSerializer(serializers.ModelSerializer):
    customer = serializers.StringRelatedField()
    report_type=serializers.CharField(source='get_report_type_display')
    tz = pytz.timezone('Asia/Kolkata')
    generated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S",default_timezone=tz)
    owner=serializers.CharField(source='owner.username')
    class Meta:
        model = Report
        fields = ['id', 'report_type', 'generated_at', 'customer','status','owner','month','year']

class PayableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payables
        fields = ['id','generated_at','legalentity', 'customer','results','day','month','year']

class ReceivableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receivables
        fields = ['id','generated_at','legalentity', 'customer','results','day','month','year']


class ResultSerializer(serializers.ModelSerializer):
    report_type=serializers.CharField(source='get_report_type_display')
    tz = pytz.timezone('Asia/Kolkata')
    generated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S",default_timezone=tz)
    class Meta:
        model = Report
        fields = ['id','report_type','generated_at','results','qb_api','comments','month','year']

class CustomDateTimeField(serializers.DateTimeField):
    def to_representation(self, value):
        tz = timezone.get_default_timezone()
        print(tz)
        # timezone.localtime() defaults to the current tz, you only
        # need the `tz` arg if the current tz != default tz
        value = timezone.localtime(value, timezone=tz,format="%Y-%m-%d %H:%M:%S")
        # py3 notation below, for py2 do:
        # return super(CustomDateTimeField, self).to_representation(value)
        return super().to_representation(value)

class InsightTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsightsType
        fields = ['id','name']

class InsightCategorySerializer(serializers.ModelSerializer):
    name=serializers.StringRelatedField()
    class Meta:
        model = InsightCategory
        fields = ['id','name']

class InsightNotesSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsightsNotes
        fields = ['id','notes','category','type']













