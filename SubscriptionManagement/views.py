from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from django.contrib.auth.decorators import login_required
from .choices import *
from django.http import HttpResponse,JsonResponse
from Workspace.utilities import *

@api_view(['GET'])
@login_required
def choices_list(request,format=None):
    user=request.user
    if(not user.groups.filter(name__in=["Customer"]).exists()):
            if(request.method=='GET'):
                cycle_types=[]
                count=1
                for i in CYCLE_TYPE:
                    cycle_types.append([i[0],i[1]])
                    count+=1
                input_types=[]
                count=1
                for j in INPUT_TYPE:
                    input_types.append({"id":j[0],"text":j[1]})
                options={
                    "cycle_type":cycle_types,
                    "input_type":input_types,
                    "status":200
                }
                return JsonResponse(options)
    else:
        options={
            "message":"Not Allowed",
            "status":400
        }
        return JsonResponse(options)

@api_view(['GET'])
@login_required
def get_reports(request,format=None):
    if(request.method=='GET'):
        report_types=[]
        for i in SUBSCRIPTION_REPORT_TYPE:
            report_types.append([i[0],i[1]])
        options={
            "report_type":report_types,
            "status":200
        }
        return JsonResponse(options)

@api_view(['GET'])
@login_required
def get_subscription_template(request,format=None):
    if(request.method=='GET'):
        template=SUBSCRIPTIONS
        return JsonResponse(template,safe=False)