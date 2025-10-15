from django.shortcuts import render
from django.http import HttpResponse,JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User,Group
from .models import *
from Workspace.utilities import *
# Create your views here.
from rest_framework.decorators import api_view
from .Serializer import *
from rest_framework.response import Response

@login_required(login_url='/accounts/login')

def add_employee(request):
    user=request.user
    if(user.groups.filter(name__in=['Admin','Manager']).exists()):
        if(request.method=="POST"):
            if "emp_username" not in request.POST:
                response = JsonResponse({'status': 'Invalid', 'message': 'Username not provided',})
                response.status_code = 401
                return response
            elif "emp_password" not in request.POST:
                response = JsonResponse({'status': 'Invalid', 'message': 'Password not provided',})
                response.status_code = 401
                return response
            elif "emp_email" not in request.POST:
                response = JsonResponse({'status': 'Invalid', 'message': 'Email not provided',})
                response.status_code = 401
                return response
            else:
                emp_username=request.POST.get("emp_username")
                emp_password=request.POST.get("emp_password")
                emp_email=request.POST.get("emp_email")
                user = User.objects.create_user(emp_username, emp_email, emp_password)
                emp_first_name=request.POST.get("emp_first_name")
                emp_second_name=request.POST.get("emp_second_name")
                emp_team=request.POST.get("emp_team")
                emp_role=request.POST.get("emp_role")
                user.first_name=emp_first_name
                user.last_name=emp_second_name
                group = Group.objects.get(name=emp_role)
                user.groups.set([group])
                user.save()
                emp=Employee(user=user)
                emp.save()
                if "emp_desc" in request.POST:
                    emp_desc=request.POST.get("emp_desc")
                    emp.aboutme=emp_desc
                    emp.save()
                if "profile_picture" in request.FILES:
                    emp_pp=request.FILES.get("profile_picture")
                    emp.profile_picture=emp_pp
                    emp.save()
                if "background" in request.FILES:
                    emp_bg=request.FILES.get("background")
                    emp.background=emp_bg
                    emp.save()
                response = JsonResponse({'status': 'Valid', 'message': 'Employee processed'})
                response.status_code = 200
                return response
    else:
        result={
            "status":400,
            "logged":False,
        }
        return JsonResponse(result)

@login_required(login_url='/accounts/login')
@user_passes_test(is_manager)
@api_view(['GET'])
def admin_get_users(request):
    employees=Employee.objects.all()
    emp_serializer = EmployeeSerializer(employees, many=True)
    return Response(emp_serializer.data)

@api_view(['GET'])
@login_required(login_url='/accounts/login')
@user_passes_test(is_manager)
def admin_get_groups(request):
    employees=Group.objects.all()
    emp_serializer = GroupSerializer(employees, many=True)
    return Response(emp_serializer.data)


@login_required(login_url='/accounts/login')
@user_passes_test(is_admin)
@api_view(['GET'])
def get_users(request):
    employees=Employee.objects.all()
    emp_serializer = EmployeeSerializer(employees, many=True)
    return Response(emp_serializer.data)


@login_required(login_url='/accounts/login')
@api_view(['GET'])
def get_employees(request,role):
    if(role == "Accountant"):
        employees=User.objects.filter(groups__name='Accountant')
        emp_serializer = UserSerializer(employees, many=True)
        return Response(emp_serializer.data)
    if(role == "QC"):
        employees=User.objects.filter(groups__name='QC')
        emp_serializer = UserSerializer(employees, many=True)
        return Response(emp_serializer.data)
    if(role == "CRM"):
        employees=User.objects.filter(groups__name='CRM')
        emp_serializer = UserSerializer(employees, many=True)
        return Response(emp_serializer.data)


@login_required(login_url='/accounts/login')
@api_view(['GET'])
def get_myinfo(request):
    u=User.objects.get(username=request.user.username)
    user=UserSerializer(request.user)
    print(user.data)
    return Response(user.data)


@login_required(login_url='/accounts/login')
@user_passes_test(is_manager)
def check_if_username_exists(request):
    if(request.method=="POST"):
        username=request.POST.get("emp_username")
        try:
            user= User.objects.get(username=username)
            response = JsonResponse({'status': 'false', 'message': 'User Exists'})
            response.status_code = 200
            return response
        except User.DoesNotExist:
            response = JsonResponse({'status': 'true', 'message': 'User Does Not Exists'})
            response.status_code = 200
            return response


@login_required(login_url='/accounts/login')
@user_passes_test(is_manager)
def check_if_email_exists(request):
    if(request.method=="POST"):
        email=request.POST.get("emp_email")
        try:
            user= User.objects.get(email=email)
            response = JsonResponse({'status': 'false', 'message': 'User Exists'})
            response.status_code = 200
            return response
        except User.DoesNotExist:
            response = JsonResponse({'status': 'true', 'message': 'User Does Not Exists'})
            response.status_code = 200
            return response
        except User.MultipleObjectsReturned:
            response = JsonResponse({'status': 'false', 'message': 'Multiple Users exist'})
            response.status_code = 200
            return response