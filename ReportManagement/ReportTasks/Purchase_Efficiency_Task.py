from Report_Task import Task
from reportbuilders.Purchase_Efficiency  import Purchase_Efficiency_Builder
from django.contrib.auth.models import User
from django.conf import settings
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
from QbApplication.tasks import pull_PL_Detail_specific1
from botocore.client import Config
from reportbuilders.Notifications  import Email_Notification_Generator

'''Profit Loss Task for Generating the PL Report'''
class Purchase_Efficiency_Task(Task):
    def __init__(self,user_id,report_id,cust_info,add_data={}):
        super().__init__()
        print("Hey welcome to the Purchase Efficiency")
        self.report_type="Purchase Efficiency Report"
        self.var_report_type="PUR_EFF"
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
    def prepare_task(self,user_id,report_id,cust_info,add_data):
        print("Preparing the Task")
        try:
            self.user_id=user_id
            self.report_id=report_id
            self.cust_id=cust_info["_id"]
            self.user=User.objects.get(id=self.user_id)
            self.report=Report.objects.get(id=self.report_id)
            self.customer=cust_info
            prev_date = date(self.report.year, self.report.month, 1) - relativedelta(months=1)
            self.prev_date=prev_date
        except Exception as e:
            print(e)
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)
        pass
    def get_data(self):
        print("getting the data")
        def pull_data():
            print(self.report.legalentity["id"])
            status = ['Review', 'QC', 'CRM', 'Published']
            apiUrl = settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.OT_LE_GET_TO_API_URL \
                     + "?id=" + self.report.legalentity["id"]
            headers = {'Accept': 'application/json', 'accept': 'application/json'}
            apiReq = requests.get(apiUrl, headers=headers)
            api_status_code = apiReq.status_code
            # print(json.loads(apiReq.text))
            if api_status_code == 200:
                outlets = [ol['_id'] for ol in json.loads(apiReq.text)['result']]
                if outlets:
                    records = Report.objects.filter(
                        month=self.report.month, year=self.report.year, report_type="P_L",
                        active=True, status__in=status, customer__id=self.report.customer["id"]).filter(outlet__id__in=outlets)
                else:
                    self.report.last_run_status = "Error"
                    self.report.save()
                    raise Exception("No outlets created for {}".format(self.report.legalentity['name']))
            else:
                self.report.last_run_status = "Error"
                self.report.save()
                raise Exception(apiReq.text)
            details_list = {
                "details": {},
                "accounting":self.report.accounting_software
            }
            print("###############################")
            print(len(records))
            if not len(records):
                self.report.last_run_status = "Error"
                self.report.save()
                raise Exception("No records found for Profit Statement, Please try again after generating Profit Statement report.")
                # raise(ValueError("Profit & Loss Statement is not ready. Please check the profit and loss report"))
            for rec in records:
                if "details" in rec.details:
                    details_list["details"][rec.outlet["name"]]=rec.details
                    print(details_list)
                else:
                    self.report.last_run_status = "Error"
                    self.report.save()
                    raise Exception("No Transaction records found for Profit Statement, Please try again after all the transactions are generated for Profit Statement report.")




            #prev_qb_api=record.details

            # prev_qb_api={
            #     "details":"/home/data/Projects/firstcourse/Data/Reports/PE/2021_10_Theory Cafe_Jubliee Hills_details.json"
            # }
            return details_list
        try:
            self.data=pull_data()

        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            print(e)
            raise(e)
    def perform_task(self):
        try:
            print("Performing the task")
            output=Purchase_Efficiency_Builder()
            output.init_data(self.data)
            output.process_tree()
            self.pdfresult=output.get_result("PDF")
            self.dashboardresult=output.get_result("Dashboard")
            out_file = open("myfile_final.json", "w")
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
            self.report.results=self.pdfresult
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
                    "template": { "name" : "PE-Main","recipe": "chrome-pdf" },
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
            self.report.celery_task_id = ""
            self.report.save()
        except Exception as e:
            self.report.last_run_status="Error"
            self.report.save()
            raise(e)
