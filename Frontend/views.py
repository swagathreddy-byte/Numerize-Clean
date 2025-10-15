from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from Workspace.utilities import *

# Create your views here.
def index(request):
    return render(request,"Landing/wrkflow/index.html")

@login_required(login_url='/accounts/login')
@user_passes_test(is_manager)
def system_admin_dashboard(request):
    if(request.method=="GET"):
        return render(request,"Administration/Administration.html")


@login_required(login_url='/accounts/login')
def dashboard(request):
    if(request.method=="GET"):
        if request.user.groups.filter(name='Customer').exists():
            return redirect("/reports/summary/")
            #return render(request,"client_dashboard/client_dashboard.html")
        elif request.user.groups.filter(name='Manager').exists():
            return redirect("/administration/")
        else:
            return render(request,"Workspace/dashboard.html")

# @login_required(login_url='/accounts/login')
# def initiate_tasks(request):
#     if(request.method=="GET"):
#         if request.user.groups.filter(name='Customer').exists():
#             return redirect("/reports/summary/")
#         else:
#             return render(request,"home/initiate_tasks.html")
#
# @login_required(login_url='/accounts/login')
# def review_tasks(request):
#     if(request.method=="GET"):
#         if request.user.groups.filter(name='Customer').exists():
#             return redirect("/reports/summary/")
#         else:
#             return render(request,"home/review_tasks.html")

@login_required(login_url='/accounts/login')
def overview_tasks(request):
    if(request.method=="GET"):
        stage = ''
        if ('stage' in request.GET):
            stage = request.GET.get("stage")
        print("stage : " + stage)
        return render(request,"Workspace/task_overview.html",{'stage':stage})


# @login_required(login_url='/accounts/login')
# def peer_review_tasks(request):
#     if(request.method=="GET"):
#         return render(request,"home/peer_review_tasks.html")


@login_required(login_url='/accounts/login')
def view_task(request,id):
    if(request.method=="GET"):
        if request.user.groups.filter(name='Customer').exists():
            return redirect("/reports/summary/")
        else:
            return render(request,"Workspace/view_task.html",{"id":id})

@login_required(login_url='/accounts/login')
def view_qbstatus(request):
    if(request.method=="GET"):
        return render(request,"Administration/QbAPI.html")

@login_required(login_url='/accounts/login')
def helpdesk(request):
    if(request.method=="GET"):
        if request.user.groups.filter(name='Customer').exists():
            return redirect("/reports/summary/")
        else:
            return render(request,"home/helpdesk.html")


@login_required(login_url='/accounts/login')
def reports_summary(request):
    if(request.method=="GET"):
        if request.user.groups.filter(name='Customer').exists():
            if(request.user_agent.is_mobile):
                return render(request,"ClientDashboard/ui8-nazox/mobile/report-summary.html")
            else:
                return render(request,"ClientDashboard/ui8-nazox/Desktop/client_dashboard.html")
        else:
            response = JsonResponse({'status': 'Invalid', 'message': 'Not Allowed'})
            response.status_code = 400
            return response


@login_required(login_url='/accounts/login')
def reports_detail(request,reporttype):
    print("Report Detail Dashboard called : ",reporttype)
    month = ''
    year=''
    if ('month' in request.GET):
        month=request.GET.get("month")
    print("month : "+month)
    if ('year' in request.GET):
        year = request.GET.get("year")
    print("year : " + year)
    if(request.method=="GET"):
        if request.user.groups.filter(name='Customer').exists():
            if(request.user_agent.is_mobile):
                return render(request,"ClientDashboard/ui8-nazox/mobile/report-dashboard.html",{'reporttype': str(reporttype),'month':month,'year':year})
            else:
                return render(request,"ClientDashboard/client_dashboard.html")
        else:
            response = JsonResponse({'status': 'Invalid', 'message': 'Not Allowed'})
            response.status_code = 400
            return response


@login_required(login_url='/accounts/login')
def reports_home(request):
    print("Client dashboard called")
    if(request.method=="GET"):
        if request.user.groups.filter(name='Customer').exists():
            return render(request,"ClientDashboard/ui8-nazox/mobile/reports-home.html")
        else:
            response = JsonResponse({'status': 'Invalid', 'message': 'Not Allowed'})
            response.status_code = 400
            return response


@login_required(login_url='/accounts/login')
def ocrhome(request):
    # print("Hey its ocr home")
    if request.method == 'GET':
        return render(request,"OCR/imglist.html")


@login_required(login_url='/accounts/login')
def process_image(request):
    if(request.method=='GET'):
        # img_rel_path = request.GET.get('path')
        # img_url=request.GET.get('imgsrc')
        # img_url = s3util.public_url_base + urllib.parse.unquote(img_rel_path)
        # img_path = s3util.download_file(urllib.parse.unquote(img_rel_path))
        # img_path=settings.BASE_DIR +"/"+ img_rel_path
        # print(img_path)
        # data = visionDetect.getValueMap(img_path)
        # data = {"invoice_no": "123123123"}
        # data["imgpath"] = img_path
        return render(request,'OCR/result.html')


@login_required(login_url='/accounts/login')
@user_passes_test(is_manager)
def add_customer(request):
    if(request.method=="GET"):
        return render(request,"Administration/AddCustomer.html")

@login_required(login_url='/accounts/login')
@user_passes_test(is_manager)
def manage_customer(request,id):
    if(request.method=="GET"):
        return render(request,"Administration/ManageCustomer.html")

@login_required(login_url='/accounts/login')
@user_passes_test(is_manager)
def add_employee(request):
    if(request.method=="GET"):
        return render(request,"Administration/AddEmployee.html")
