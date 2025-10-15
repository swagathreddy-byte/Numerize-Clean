from Report_Task import Task
from reportbuilders.Sales_Channel_Reconciliation  import Sales_Channel_Reconciliation_Builder
from django.contrib.auth.models import User
from ReportManagement.models import *
from slugify import Slugify,slugify
import requests
import json
from pytz import timezone
from itertools import groupby
import calendar
import boto3
from datetime import datetime,date
from dateutil.relativedelta import *
from django.core.files import File

from QbApplication.services import insert_report
from botocore.client import Config
from reportbuilders.Notifications  import Email_Notification_Generator

'''Profit Loss Task for Generating the PL Report'''
class Sales_Channel_Reconciliation_Task(Task):
    def __init__(self,user_id,report_id,cust_info,add_data={}):
        super().__init__()
        print("Hey welcome to the SCR Task")
        self.report_type="Sales Channel Reconciliation"
        if("file_suffix" in add_data):
            self.file_suffix=add_data["file_suffix"]
        print("Additional data is",add_data)
        self.report=None
        self.add_data=add_data
        self.data={}
        self.pdfresult={}
        self.dashboardresult={}
        self.details=[]
        self.prepare_task(user_id,report_id,cust_info,add_data)
        self.get_data()
        print("Data after assignment is",self.data)
        self.perform_task()
        # self.post_process()
        self.update_report_status()
        self.add_event()
        # self.notify_users(["email"])
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
        def save_data(qb_api,name):
            input_path=self.input_json_path(slugify(self.user.username),self.report.year,self.report.month)
            input_path=settings.BASE_DIR+"/"+input_path
            if(not os.path.isdir(input_path)):
                os.makedirs(input_path)
            #Dump the current json into a file

            json_file=slugify(self.customer["name"])+name
            json_file_path=input_path+"/"+json_file
            with open(json_file_path,"w") as outputfile:
                json.dump(qb_api,outputfile)
            return json_file_path

        try:
            # id="customers/"+str(id)
            name="scr"
            cur_file_path=save_data(self.report.input_api,name+'.json')
            self.data["current_scr_path"]=cur_file_path
            print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$Current path is")
            print(cur_file_path)
                    # cur_file_path="/home/data/Projects/firstcourse/Data/Reports/PL/ShaSha-Kondapur.json"
                    # prev_file_path="/home/data/Projects/firstcourse/Data/Reports/PL/ShaSha-Kondapur_prev.json"
                    # filepath="media/category_list/"+slugify(cust)+"/"+slugify(outlet_name)+"/"
                    # cat_url=filepath+"category_list.xlsx"
                    # cat_url="/home/data/Projects/firstcourse/Data/Reports/PL/category_list_shasha_kondapur.xlsx"
                # self.data["kphb"]="/home/data/Projects/firstcourse/Data/Reports/PL/Fruitfullcon_HimayatNagar.json"
                # self.data["kukatpally"]="/home/data/Projects/firstcourse/Data/Reports/PL/Fruitfullcon_Madhapur.json"
            # return

        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            print(e)
            raise(e)
    def perform_task(self):
        try:
            print("Performing the task")
            output=Sales_Channel_Reconciliation_Builder()
            output.init_data(self.data)
            output.process_tree()
            self.dashboardresult=output.get_result("Dashboard")
            print("CHecking Dashboard Result")
            out_file = open("myfile.json", "w")
            json.dump(self.dashboardresult,out_file)
            out_file.close()

        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)
    def setup_report_headers(self):
        try:
            print("Setting up the headers")
            #result=json.loads(json.dumps(self.result))
            self.pdfresult["header"]["month1"]=calendar.month_name[self.report.month]
            self.pdfresult["header"]["month2"]=calendar.month_name[self.prev_date.month]
            self.pdfresult["header"]["customer"]=str(self.report.customer["name"])
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
            self.report.qb_api=self.dashboardresult
            self.report.results={}
            self.report.status="Review"
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
            def delete_old_attachments():
                #Deleting old output files
                links=self.report.pdf_attachments.all()
                s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
                for i in range(len(links)):
                    attach=links[i]
                    fileurl=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+attach.document_link
                    s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=fileurl)
                    attach.delete()
            delete_old_attachments()
            d = datetime.now().astimezone(timezone('Asia/Kolkata'))
            self.report.last_run_status="Success"
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
            pdflink=""
            excellink=""
            print("pdf attachments")
            pdf = self.report.pdf_attachments.all()
            print(len(pdf))
            if len(pdf) >0 :
                pdflink=pdf[len(pdf)-1].document_link
            print(pdflink)
            print("excel attachments")
            excel = self.report.excel_attachments.all()

            print(len(excel))
            if len(excel) >0 :
                excellink=excel[len(excel)-1].document_link

            if (self.report.brand):
                reportEntity = self.report.brand["id"]
            elif (self.report.outlet):
                reportEntity = self.report.outlet["id"]
            elif (self.report.legalentity):
                reportEntity = self.report.legalentity["id"]
            else:
                reportEntity = self.report.customer["id"]
            d = datetime.now().astimezone(timezone('Asia/Kolkata'))

            apiRes = insert_report(reportid=self.report_id,pdflink=pdflink,excellink=excellink,entity=reportEntity, day="1", month=self.report.month, year=self.report.year,report_type=self.report.report_type, version=self.report.version, report_generated_at=self.report.generated_at.strftime("%m/%d/%Y, %H:%M:%S"),created_at=d.strftime("%m/%d/%Y, %H:%M:%S"),modified_at=d.strftime("%m/%d/%Y, %H:%M:%S"), result=json.dumps(self.dashboardresult),details=json.dumps(self.report.details),notes=[])
            if apiRes.status_code != 200:
                response = ''
                self.report.last_run_status="Success"
                self.report.save()
                print("Process Complete")
            else:
                self.report.last_run_status="Error"
                self.report.save()
                print("Process Complete")

        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)