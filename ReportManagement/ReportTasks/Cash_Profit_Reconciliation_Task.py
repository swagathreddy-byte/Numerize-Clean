import json
from django.contrib.auth.models import User
from ReportManagement.models import *
import os
from datetime import datetime,date
from slugify import Slugify,slugify
from django.conf import settings
import calendar
from dateutil.relativedelta import *
from django.core.files import File
import boto3
from botocore.client import Config
from pytz import timezone
from itertools import groupby
import requests
from django.core.mail import send_mail
import sys
sys.path.insert(0, '../reportgeneration')
sys.path.insert(0,'../')
sys.path.insert(0, 'ReportManagement/ReportTasks')

from QbApplication.tasks import pull_QB_CashFlow_Info
from ZohoApplication.tasks import pull_Zoho_CashFlow_Info
from reportbuilders.Cash_Profit_Reconciliation  import CPR_Builder
from reportbuilders.Notifications  import Email_Notification_Generator
from Report_Task import Task


'''Cash Profit Reconciliation Task for Generating the CPR Report'''
class Cash_Profit_Reconciliation_Task(Task):
    def __init__(self,user_id,report_id,cust_info,add_data={}):
        super().__init__()
        self.report_type="Cash Profit Reconciliation"
        if("file_suffix" in add_data):
            self.file_suffix=add_data["file_suffix"]
        print("Additional data is",add_data)
        self.add_data=add_data
        self.data={}
        self.pdfresult={}
        self.dashboardresult={}
        self.details=[]


        self.prepare_task(user_id,report_id,cust_info,add_data)
        self.get_data()
        print("Data after assignment is",self.data)
        self.perform_task()
        self.post_process()
        self.update_report_status()
        # self.setup_report_headers()
        self.add_event()
        # self.setup_reportengine_headers("pdf")
        # self.generate_outputs("pdf")
        # self.attach_outputs("pdf")
        self.notify_users(["email"])
        self.complete_process()
        # self.call_particulars_api()
    def prepare_task(self,user_id,report_id,cust_info,add_data):
        print("Preparing the Task")
        try:
            self.user_id=user_id
            self.report_id=report_id
            self.cust_id=cust_info["_id"]
            self.user=User.objects.get(id=self.user_id)
            self.report=Report.objects.get(id=self.report_id)
            self.customer=cust_info
        except Exception as e:
            print(e)
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)
        pass
    def get_data(self):
        print("getting the data")
        #STores the json to a local filesystem
        def save_data(input_api,name):
            print("Save data")
            print(name)
            input_path=self.input_json_path(slugify(self.user.username),self.report.year,self.report.month)
            input_path=settings.BASE_DIR+"/"+input_path
            if(not os.path.isdir(input_path)):
                os.makedirs(input_path)
            #Dump the current json into a file

            json_file=slugify(self.customer["name"])+"-CPR-"+slugify(self.report.legalentity["name"])+name
            json_file_path=input_path+"/"+json_file
            print(json_file_path)
            with open(json_file_path,"w") as outputfile:
                json.dump(input_api,outputfile)
            return json_file_path
        def pull_data():
            print("-------pull_data----------------")
            print(self.report.accounting_software)
            curr_month=self.report.month
            curr_year=self.report.year
            curr_from_date=date(month=curr_month,day=1,year=curr_year).strftime("%Y-%m-%d")
            curr_last_day = calendar.monthrange(curr_year, curr_month)[1]
            curr_to_date=date(month=curr_month,day=curr_last_day,year=curr_year).strftime("%Y-%m-%d")
            if self.report.accounting_software == "qb":
                curr_response, curr_data = pull_QB_CashFlow_Info(self.report_id, curr_from_date, curr_to_date)
            elif self.report.accounting_software=='zoho':
                curr_response, curr_data = pull_Zoho_CashFlow_Info(self.report_id, curr_from_date, curr_to_date)
            else:
                self.report.last_run_status="Error"
                self.report.save()
                raise("No Cash Flow API call for accounting software "+self.report.accounting_software)

            print("-----------------curr_response-------------------------------------")
            print(curr_response)
            if curr_response["status"]==200:
                curr_report=Report.objects.get(id=self.report_id)
                curr_report.input_api=curr_data
                curr_report.save()

            self.report=Report.objects.get(id=self.report_id)
            input_api=self.report.input_api
            # print(input_api)
            return input_api
        try:
            input_api=pull_data()
            cur_file_path=save_data(input_api,'.json')
            self.filepaths={
                "cur_file_path":cur_file_path
            }
            self.data={
                "filepaths":self.filepaths,
                "cash_funds_data":self.add_data
            }
        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            print(e)
            raise(e)
    def perform_task(self):
        try:
            print("Performing the task")
            output=CPR_Builder()

            output.init_data(self.data)
            output.process_tree()
            self.dashboardresult=output.get_result("Dashboard")
        except Exception as e:
            self.report.last_run_status="Error"
            self.report.celery_task_id = ""
            self.report.save()
            raise(e)
    def setup_report_headers(self):
        try:
            print("Setting up the headers")

        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)
    def update_report_status(self):
        try:
            print("Updating the report status")
            accountant = User.objects.get(id=self.customer['accountant'])
            self.report.qc = User.objects.get(id=self.customer['qc'])
            self.report.crm = User.objects.get(id=self.customer['crm'])
            self.report.qb_api=self.dashboardresult
            self.report.results={}
            self.report.save()
        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)
    def add_event(self):
        try:
            print("Adding event")
            d = datetime.now().astimezone(timezone('Asia/Kolkata'))
            mon=d.strftime("%b")
            message=self.report_type+ " Report Version - "+ str(self.report.version) +"has been created"
            event={
                "modifierid" : self.user.id,
                "modifiername" : self.user.username,
                "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                "month" : mon,
                "eventtype" : "lifecycle",
                "eventvalue" : "Updated",
                "message" : message,
                "status" : "Review"
            }
            self.report.activity.append(event)
            self.report.save()
        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)
    def post_process(self):
        try:
            d = datetime.now().astimezone(timezone('Asia/Kolkata'))
            self.report.generated_at=d
            self.report.save()
        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)
    def setup_reportengine_headers(self,format):
        try:
            print("Setting up the report engine headers")
        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)
    def attach_outputs(self,format):
        try:
            print("Attaching the outputs")

        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)
    def notify_users(self,channel):
        try:
            print("Notifying the users")
            if("email" in channel):
                subject='Report Created'
                body='Hi, A new report has been created and has been sent for your approval. Please login to your firstcourse workflow to check it.'
                sender="tech@firstcourse.in"
                accountant = User.objects.get(id=self.customer['accountant'])
                receiver=[accountant.email]
                Email_Notification_Generator(sender,receiver,subject,body)
        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)
    def complete_process(self):
        try:
            print("------------------complete process--------------------")
            self.report.last_run_status="Success"
            self.report.status="Review"
            self.report.celery_task_id = ""
            self.report.save()
            print("----------------------deleted celery task id----------------------")

        except Exception as e:
            self.report.last_run_status="Error"
            self.report.status="Processing"
            self.report.save()
            raise(e)
