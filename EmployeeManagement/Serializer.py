from rest_framework import serializers
from .models import *
from django.contrib.auth.models import User,Group

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model=Group
        fields= ["id","name"]

class EmployeeSerializer(serializers.ModelSerializer):
    first_name=serializers.CharField(source='user.first_name')
    last_name=serializers.CharField(source='user.last_name')
    email=serializers.EmailField(source='user.email')
    username=serializers.CharField(source='user.username')
    all_groups=GroupSerializer(source="user.groups",many=True)
    class Meta:
        model=Employee
        fields = ["aboutme","first_name","last_name","email","all_groups","username"]



class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True)
    class Meta:
        model = User
        fields = ('id','username', 'email', 'is_staff', 'groups',)