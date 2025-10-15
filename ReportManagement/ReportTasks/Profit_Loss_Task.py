import json
from django.contrib.auth.models import User
from ReportManagement.models import *
from QbApplication.tasks import pull_PL_Info,pull_PL,pull_PL_specific,pull_PL_Detail,pull_PL_Detail_specific,pull_PL_particulars_api
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

from reportbuilders.Profit_Loss_Detail  import Profit_Loss_Detail_Builder
from reportbuilders.Profit_Loss_Detail_Zoho  import Profit_Loss_Detail_Builder as Profit_Loss_Detail_Zoho_Builder
from reportbuilders.Notifications  import Email_Notification_Generator
from Report_Task import Task
from ZohoApplication.tasks import pull_zoho_PL_Detail,pull_zoho_PL_particulars_api


'''Profit Loss Task for Generating the PL Report'''
class Profit_Loss_Task(Task):
    def __init__(self,user_id,report_id,cust_info,add_data={}):
        super().__init__()
        self.report_type="Profit & Loss"
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
        self.setup_report_headers()
        self.add_event()
        self.setup_reportengine_headers("pdf")
        self.generate_outputs("pdf")
        self.attach_outputs("pdf")
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
        def save_data(qb_api,name):
            print("Save data")
            print(name)
            input_path=self.input_json_path(slugify(self.user.username),self.report.year,self.report.month)
            input_path=settings.BASE_DIR+"/"+input_path
            if(not os.path.isdir(input_path)):
                os.makedirs(input_path)
            #Dump the current json into a file

            json_file=slugify(self.customer["name"])+"-"+slugify(self.report.outlet["name"])+name
            json_file_path=input_path+"/"+json_file
            print(json_file_path)
            with open(json_file_path,"w") as outputfile:
                json.dump(qb_api,outputfile)
            return json_file_path
        def pull_cur_month():
            print("-------pull_curr_month----------------")
            print(self.report.accounting_software)
            curr_month=self.report.month
            curr_year=self.report.year
            curr_from_date=date(month=curr_month,day=1,year=curr_year).strftime("%Y-%m-%d")
            curr_last_day = calendar.monthrange(curr_year, curr_month)[1]
            curr_to_date=date(month=curr_month,day=curr_last_day,year=curr_year).strftime("%Y-%m-%d")

            if self.report.accounting_software=='qb':
                output_pl=pull_PL_Detail(report_id=self.report_id,cust_id=self.cust_id)

            elif self.report.accounting_software=='zoho':
                curr_response,curr_data=pull_zoho_PL_Detail(self.report_id,self.cust_id,curr_from_date,curr_to_date)
                if curr_response["status"]==200:
                    curr_report=Report.objects.get(id=self.report_id)
                    curr_report.input_api=curr_data
                    curr_report.save()
            else:
                self.report.last_run_status="Error"
                self.report.save()
                raise("No Profit Loss API call for accounting software "+self.report.accounting_software)


            self.report=Report.objects.get(id=self.report_id)
            qb_api=self.report.input_api
            # print(qb_api)
            return qb_api
        def pull_prev_month():
            prev_date = date(self.report.year, self.report.month, 1) - relativedelta(months=1)
            self.prev_date=prev_date
            prev_last_day = calendar.monthrange(prev_date.year, prev_date.month)[1]
            prev_start_date = date(prev_date.year, prev_date.month, 1)
            prev_end_date = date(prev_date.year, prev_date.month, prev_last_day)
            if self.report.accounting_software=='qb':
                prev_qb_api=pull_PL_Detail_specific(self.report_id,prev_start_date.strftime("%Y-%m-%d"),prev_end_date.strftime("%Y-%m-%d"),self.report.outlet["dept_id"])
            if self.report.accounting_software=='zoho':
                prev_response,prev_qb_api=pull_zoho_PL_Detail(self.report_id,self.cust_id,prev_start_date,prev_end_date)

            print("previous month qb response")
            print(prev_qb_api)
            return prev_qb_api
        try:
            qb_api=pull_cur_month()
            cur_file_path=save_data(qb_api,'.json')
            # cur_file_path="/home/data/Projects/firstcourse/Data/Reports/PL/AnTeRa-AnteraJH.json"

            qb_api=pull_prev_month()
            prev_file_path=save_data(qb_api,"_prev.json")
            # prev_file_path="/home/data/Projects/firstcourse/Data/Reports/PL/AnTeRa-AnteraJH_prev.json"
            outlet_name=self.report.outlet["name"]
            cust=self.report.customer["name"]
            # filepath="media/category_list/"+slugify(cust)+"/"+slugify(outlet_name)+"/"
            # cat_url=filepath+"category_list.xlsx"
            # cat_url="/home/data/Projects/firstcourse/Data/Reports/PL/category_list_shasha_kondapur.xlsx"
            self.filepaths={
                "current_qb_path":cur_file_path,
                "prev_qb_path":prev_file_path,
            }
            self.data={
                "filepaths":self.filepaths,
                "stock_values":self.add_data
            }
        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            print(e)
            raise(e)
    def perform_task(self):
        try:
            print("Performing the task")
            if self.report.accounting_software=='qb':
                output=Profit_Loss_Detail_Builder()
            if self.report.accounting_software=='zoho':
                output=Profit_Loss_Detail_Zoho_Builder()
            output.init_data(self.data)
            output.process_tree()
            self.pdfresult=output.get_result("PDF")
            self.dashboardresult=output.get_result("Dashboard")
            self.details={
                "values":{
                    "invoice_list":output.reportgenerator.current_tree.invoice_list,
                    "journal_list":output.reportgenerator.current_tree.journal_list,
                    "bill_list":output.reportgenerator.current_tree.bill_list,
                    "receipt_list":output.reportgenerator.current_tree.receipt_list,
                    "expense_list":output.reportgenerator.current_tree.expense_list,
                    "deposit_list":output.reportgenerator.current_tree.deposit_list
                }

            }
        except Exception as e:
            self.report.last_run_status="Error"
            self.report.celery_task_id = ""
            self.report.save()
            raise(e)
    def setup_report_headers(self):
        try:
            print("Setting up the headers")
            #result=json.loads(json.dumps(self.result))
            self.pdfresult["header"]["month1"]=calendar.month_name[self.report.month]
            self.pdfresult["header"]["month2"]=calendar.month_name[self.prev_date.month]
            self.pdfresult["header"]["customer"]=str(self.report.customer["name"])+","+str(self.report.outlet["name"])
            self.pdfresult["header"]["month_year"]=str(calendar.month_name[self.report.month])+" "+str(self.report.year)
            self.pdfresult["header"]["report_type"]=self.report_type
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
            self.report.results=self.pdfresult
            self.report.qb_api=self.dashboardresult
            self.report.details=self.details
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
            print("Adding comments etc")
            def add_comments():
                comments=self.report.comments
                comments=json.dumps(comments)
                comments=json.loads(comments)
                self.grouped_comments=[]
                self.keys=[]
                v=[]
                if comments is not None:
                    comments["values"].sort(key=lambda content: content['comment_category'])
                    gp=groupby(comments["values"],lambda content: content['comment_category'])

                    for key,g in gp:
                        types=[]
                        content=[]
                        if(key not in self.keys):
                            self.keys.append(key)

                        for con in g:

                            if(con["comment_type"] not in types):
                                types.append(con["comment_type"])
                            content.append(con)

                        v={"category":key,"types":types,"values":content}

                        self.grouped_comments.append(v)
            def delete_old_attachments():
                #Deleting old output files
                links=self.report.pdf_attachments.all()
                s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
                for i in range(len(links)):
                    attach=links[i]
                    fileurl=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+attach.document_link
                    s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=fileurl)
                    attach.delete()


            add_comments()
            delete_old_attachments()
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
            if(format == "pdf"):
                self.jsparams={
                    "template": { "name" : "PL-Main-New","recipe": "chrome-pdf" },
                    "data" : {"result":self.pdfresult,"comments":self.grouped_comments,"keys":self.keys},
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
            print("------------------complete process--------------------")
            self.report.last_run_status="Success"
            self.report.status="Review"
            self.report.celery_task_id = ""
            self.report.save()
            print("----------------------deleted celery task id----------------------")
            if self.report.accounting_software=='qb':
                pull_PL_particulars_api.apply_async(args=(self.report_id,),queue="qbapi")
            if self.report.accounting_software=='zoho':
                pull_zoho_PL_particulars_api.apply_async(args=(self.report_id,),queue="qbapi")
        except Exception as e:
            self.report.last_run_status="Error"
            self.report.status="Processing"
            self.report.save()
            raise(e)


# current_qb_path="/home/data/Projects/firstcourse/Data/Reports/PL/Proteins-Kavuri-Hills.json"
# prev_qb_path="/home/data/Projects/firstcourse/Data/Reports/PL/Proteins-Kavuri-Hills_prev.json"
# cat_file_path="/home/data/Projects/firstcourse/Data/Reports/PL/Input Bucket list-Proteins.xlsx"
# a=pl_api_tree(current_qb_path)
# b=a.tree.to_json(with_data=True)

# b=json.loads(b)
# print(len(b["root"]))
# a.tree.show(line_type="ascii-em")
# print(len(a.individual_data))
# filepaths={
#     "current_qb_path":current_qb_path,
#     "prev_qb_path":prev_qb_path,
#     "cat_file_path":cat_file_path
# }
#
# stock_values={
#     "os_cur_mon":39619,
#     "os_prev_mon": 39619,
#     "cs_cur_mon":39620,
#     "cs_prev_mon":39620,
# }
# data={
#     "filepaths":filepaths,
#     "stock_values":stock_values
# }
# Profit_Loss_Builder(data)
