from rest_framework import serializers
from .models import *

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model=Group
        fields= ["id","name"]

# class OutletSerializer(serializers.ModelSerializer):
#     brands=serializers.StringRelatedField(many=True)
#     class Meta:
#         model = Outlet
#         fields = ["name","brands",'active']
#
# class LegalEntitySerializer(serializers.ModelSerializer):
#     outlets=OutletSerializer(many=True)
#     customer=serializers.CharField(source='customer.name')
#     class Meta:
#         model = LegalEntity
#         fields = ['id','name','gst','qb_id','outlets','customer','active']
#
#
# class CustomerSerializer(serializers.ModelSerializer):
#     email=serializers.EmailField(source='user_account.email')
#     accountant=serializers.CharField(source='accountant.username')
#     qc=serializers.CharField(source='qc.username')
#     crm=serializers.CharField(source='crm.username')
#     subscriptions=serializers.JSONField(source='subscription.subscription')
#     legal_entities=LegalEntitySerializer(many=True)
#     start_date=serializers.CharField(source="onboarding.start_date")
#     class Meta:
#         model = Customer
#         fields = ['id','name','accountant','qc','crm','email','subscriptions','legal_entities','start_date','active']


class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True)
    class Meta:
        model = User
        fields = ('id','username', 'email', 'is_staff', 'groups',)
