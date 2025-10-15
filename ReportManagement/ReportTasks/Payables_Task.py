import json
from django.contrib.auth.models import User
from ReportManagement.models import *
from QbApplication.tasks import getPayablesbyReportID
from ThirdParty_APIManagement.tasks import publish_payables
from ZohoApplication.tasks import getZohoPayablesbyReportID
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

from reportbuilders.Payables  import Payables_Builder
from reportbuilders.Notifications  import Email_Notification_Generator
from Report_Task import Task



'''Payables Task for Generating the Payables'''
class Payables_Task(Task):
    def __init__(self,user_id,report_id,cust_info,add_data={}):
        super().__init__()
        self.report_type="Payables"
        if("file_suffix" in add_data):
            self.file_suffix=add_data["file_suffix"]
        print("Additional data is",add_data)
        self.add_data=add_data
        self.data={}
        self.pdfresult={}
        self.dashboardresult={}
        self.details=[]

        # self.prepare_task(user_id,report_id,cust_info,add_data)
        # self.get_data()
        # print("Data after assignment is",self.data)
        # self.perform_task()
        # self.update_report_status()
        # self.add_event()

        # self.complete_process()
        # self.call_particulars_api()
        self.prepare_task(user_id,report_id,cust_info,add_data)
        self.get_data()
        # print("Data after assignment is",self.data)
        self.perform_task()
        self.post_process()
        self.update_report_status()
        self.setup_report_headers()
        self.add_event()
        # self.setup_reportengine_headers("pdf")
        # self.generate_outputs("pdf")
        # self.attach_outputs("pdf")
        # self.notify_users(["email"])
        self.complete_process()
    def prepare_task(self,user_id,report_id,cust_info,add_data):
        print("Preparing the Task")
        try:
            self.user_id=user_id
            self.report_id=report_id
            self.cust_id=cust_info["_id"]
            self.user=User.objects.get(id=self.user_id)
            self.report=Payables.objects.get(id=self.report_id)
            self.customer=cust_info
        except Exception as e:
            print(e)
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)
        pass
    def get_data(self):
        print("getting the data")
        def save_data(qb_api,name):
            input_path=self.input_json_path(slugify(self.user.username),self.report.year,self.report.month)
            input_path=settings.BASE_DIR+"/"+input_path
            if(not os.path.isdir(input_path)):
                os.makedirs(input_path)
            #Dump the current json into a file

            json_file=slugify(self.customer["name"])+"-"+slugify(self.report.legalentity["name"])+name
            json_file_path=input_path+"/"+json_file
            with open(json_file_path,"w") as outputfile:
                json.dump(qb_api,outputfile)
            return json_file_path
        def pull_cur_payables():
            print("******************************************************************")
            print(self.report.accounting_software)

            if self.report.accounting_software=='qb':
                output_pl=getPayablesbyReportID(report_id=self.report_id)
            elif self.report.accounting_software=='zoho':
                print(self.add_data["zoho_access_token"])
                output_pl=getZohoPayablesbyReportID(report_id=self.report_id,zoho_access_token=self.add_data["zoho_access_token"],zoho_org_id=self.add_data["zoho_org_id"],pull_vendor_list=self.add_data["vendor_list"])
            else:
                self.report.last_run_status="Error"
                self.report.save()
                raise("No Payables API call for accounting software "+self.report.accounting_software)

            print(output_pl)
            if(output_pl["status"]==200):
                self.report=Payables.objects.get(id=self.report_id)
                print(self.report)
                # r=Report.objects.get(id=self.report_id)
                qb_api=self.report.input_api
                return qb_api
            else:
                self.report.last_run_status="Error"
                self.report.save()
                raise Exception("Unable to pull the Payables data")

        try:
            qb_api=pull_cur_payables()
            cur_file_path=save_data(qb_api,'.json')
            # cur_file_path="/home/data/Projects/firstcourse/Data/Reports/PYBLS/Fruitfull-Sameena-Soudagar.json"
            print("**************************")
            print(cur_file_path)
            self.filepaths={
                "current_payables":cur_file_path,
            }
            self.data={
                "filepaths":self.filepaths,
            }
            print(self.data)
        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            print(e)
            raise(e)
    def perform_task(self):
        try:
            print("Performing the task")
            output=Payables_Builder()
            output.init_data(self.data)
            output.process_tree()
            self.dashboardresult=output.get_result("Dashboard")
            self.details={
                "values":{
                    "invoice_list":output.reportgenerator.tree.invoice_list,
                    "journal_list":output.reportgenerator.tree.journal_list,
                    "bill_list":output.reportgenerator.tree.bill_list,
                    "receipt_list":output.reportgenerator.tree.receipt_list,
                    "expense_list":output.reportgenerator.tree.expense_list,
                    "deposit_list":output.reportgenerator.tree.deposit_list,
                    "billpayment_list":output.reportgenerator.tree.billpayment_list
                }
            }
            # print(json.dumps(self.dashboardresult))
        except Exception as e:
            print("Error in Perform Task")
            print(e)
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
    def update_report_status(self):
        try:
            print("Updating the report status")
            self.report.results=self.pdfresult
            self.report.qb_api=self.dashboardresult
            self.report.details=self.details
            self.report.save()
        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)
    def setup_report_headers(self):
        try:


            print("Setting up the headers")
            #result=json.loads(json.dumps(self.result))
            if("headers" in self.pdfresult):
                self.pdfresult["header"]["month1"]=calendar.month_name[self.report.month]
                self.pdfresult["header"]["month2"]=calendar.month_name[self.prev_date.month]
                self.pdfresult["header"]["customer"]=str(self.report.customer["name"])+","+str(self.report.outlet["name"])
                self.pdfresult["header"]["month_year"]=str(calendar.month_name[self.report.month])+" "+str(self.report.year)
                self.pdfresult["header"]["report_type"]=self.report_type
        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)
    def add_event(self):
        try:
            print("Adding event")
            d = datetime.now().astimezone(timezone('Asia/Kolkata'))
            mon=d.strftime("%b")
            message=self.report_type+ " Report has been created"
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
    def setup_reportengine_headers(self,format):
        try:
            print("Setting up the report engine headers")
            if(format == "pdf"):
                self.jsparams={
                    "template": { "name" : "PL-Main-New","recipe": "chrome-pdf" },
                    "data" : {"result":self.pdfresult},
                    "options": { "reports": { "save": True },"reportName": "myreport"}
                }
        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)
    def attach_outputs(self,format):
        print("Attaching the outputs")
        try:
            if(format == "PDF" or format == "pdf"):
                jsreportdata=settings.JSREPORTENGINE_DATA
                fileurl_pdf=jsreportdata+self.pdf_link
                rename_pdf_url=jsreportdata+self.file_suffix+"_"+self.pdf_link
                os.rename(fileurl_pdf,rename_pdf_url)
                fileurl_pdf=rename_pdf_url
                localfile=open(fileurl_pdf,"rb")
                djangofile=File(localfile)
                filepath=self.get_file_path(self.user.username,localfile.name)
                fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
                fileurl+=filepath
                pdffile=PrivatePdfDocument(user=self.user,record=self.report,upload=djangofile,document_link=filepath)
                pdffile.save()
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
            self.report.last_run_status="Success"
            self.report.status="Review"
            self.report.save()
            print("Process Complete")
            publish_payables(self.report_id)
            # x=pull_Payables_particulars_api.apply_async(args=(self.report_id,),queue="qbapi")
            # pull_Payables_particulars_api(self.report_id)
            # x=pull_Payables_particulars_api.apply_async(args=(self.report_id,))
        except Exception as e:
            print("-----------------------------complete_process exception-------------------")
            print(e)
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)
