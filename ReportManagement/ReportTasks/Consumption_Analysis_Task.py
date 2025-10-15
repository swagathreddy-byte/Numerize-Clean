from Report_Task import Task
from reportbuilders.Consumption_Analysis import ConsumptionAnalysisBuilder  # joy
from django.contrib.auth.models import User
from ReportManagement.models import *
import json
from pytz import timezone
import calendar
import boto3
from datetime import datetime, date
from dateutil.relativedelta import *
from django.core.files import File
from botocore.client import Config
from reportbuilders.Notifications import Email_Notification_Generator
from Tools.views import get_last_months
from django.db.models import Q

# Consumption_Analysis

'''Consumption Analysis Task for Generating the CA Report'''


class Consumption_Analysis_Task(Task):
    def __init__(self, user_id, report_id, cust_info, add_data={}):
        super().__init__()
        print("Hey welcome to the Consumption Analysis")
        self.report_type = "Consumption Analysis Report"
        self.var_report_type = "CON_ANA"
        if "file_suffix" in add_data:
            self.file_suffix = add_data["file_suffix"]
        print("Additional data is", add_data)
        self.report = None
        self.add_data = add_data
        self.data = {}
        self.pdfresult = {}
        self.dashboardresult = {}
        self.details = []

        self.prepare_task(user_id, report_id, cust_info, add_data)
        self.get_data()
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

    def prepare_task(self, user_id, report_id, cust_info, add_data):
        print("Preparing the Task")
        try:
            self.user_id = user_id
            self.report_id = report_id
            self.cust_id = cust_info["_id"]
            self.user = User.objects.get(id=self.user_id)
            self.report = Report.objects.get(id=self.report_id)
            self.customer = cust_info
            prev_date = date(self.report.year, self.report.month, 1) - relativedelta(months=1)
            self.prev_date = prev_date
        except Exception as e:
            print(e)
            self.report.last_run_status = "Error"
            self.report.save()
            raise e
        pass

    def get_data(self):
        print("getting the data")

        def pull_data():
            print(self.report.outlet["id"])
            query = Q()
            pairs = get_last_months(self.report.year, self.report.month, 3)
            status=['Review','QC','CRM','Published']
            for obj in pairs:
                query = query | Q(year=obj[0], month=obj[1])

            old_records = Report.objects.filter(report_type="CON_ANA", active=True, customer__id=self.report.customer["id"],status__in=status,
                                                outlet__id=self.report.outlet["id"]).filter(query)

            records = Report.objects.filter(month=self.report.month, year=self.report.year, report_type="P_L",status__in=status,
                                            active=True, customer__id=self.report.customer["id"],
                                            outlet__id=self.report.outlet["id"])
            if records.count()==0:
                self.report.last_run_status = "Error"
                self.report.save()
                raise Exception("No records found for Profit Statement, Please try again after generating Profit Statement report.")


            # add outlet filter #joy
            details_list = {
                "details": {},
                "accounting":self.report.accounting_software
            }
            pl_qb_api={}
            old_data={}
            print("###############################")
            print(len(records))
            for rec in records:
                details_list["details"][rec.outlet["name"]] = rec.details
                pl_qb_api=rec.qb_api

            print("----old records---",len(old_records))
            for prev in old_records:

                # mon = datetime(month=prev.month, year=prev.year, day=1).strftime('%B-%Y')
                if prev.qb_api and 'children' in prev.qb_api:
                    # print(prev.qb_api['children'])
                    lst = list(filter(lambda ele: ele['type'] == 'Consumption Table', prev.qb_api['children']))
                    # print("--list--",lst)
                    if lst:
                        for prev_mon_child in lst[0]['children']:
                            # print("----prev_mon_child-----",prev_mon_child)
                            item_name=prev_mon_child["name"]
                            # print("---item_name---")
                            if item_name in self.add_data["ca_stock_json"]:
                                # print(item_name)
                                mon_json={"month":prev.month,"year":prev.year,"avgunitprice":prev_mon_child["avgunitprice"],"consumption_qty":prev_mon_child["consumption_qty"],"consumption_value":prev_mon_child["total"],"consumption_to_sales":prev_mon_child["consumption_to_sales"]}
                                prev_data=[]
                                if "prev_data" in self.add_data["ca_stock_json"][item_name]:
                                    prev_data=self.add_data["ca_stock_json"][item_name]["prev_data"]
                                prev_data.append(mon_json)
                                # print("--prev data---",prev_data)
                                self.add_data["ca_stock_json"][item_name]["prev_data"]=prev_data
                        # old_data[mon] = lst[0]['children']

            print(details_list)
            total_sales=0
            if pl_qb_api and 'children' in pl_qb_api:
                for c in range(0,len(pl_qb_api["children"])):
                    pl_child=pl_qb_api["children"][c]
                    if pl_child["name"].lower() == "income":
                        for s in range(0,len(pl_child["children"])):
                            income_child=pl_child["children"][s]
                            if income_child["name"].lower() in ["sales"]:
                                total_sales=total_sales+income_child["total"]


            self.add_data["total_sales"]=total_sales
            print("--------Additional Data in Report Task-------")
            print(self.add_data)
            # get sales data and set to add data  - todo
            return details_list

        try:
            self.data = pull_data()
        except Exception as e:
            self.report.last_run_status = "Error"
            self.report.save()
            print(e)
            raise e

    def perform_task(self):
        try:
            print("Performing the task")
            output = ConsumptionAnalysisBuilder()
            output.init_data(self.data) #pass salesdata variable - todo
            output.add_data=self.add_data
            output.process_tree()
            self.pdfresult = output.get_result("PDF")
            self.dashboardresult = output.get_result("Dashboard")
            out_file = open("myfile_final.json", "w")
            json.dump(self.dashboardresult, out_file)
            out_file.close()
        except Exception as e:
            self.report.last_run_status = "Error"
            self.report.save()
            raise (e)

    def setup_report_headers(self):
        try:
            print("Setting up the headers")
            # result=json.loads(json.dumps(self.result))
            self.pdfresult["header"]["month1"] = calendar.month_name[self.report.month]
            self.pdfresult["header"]["month2"] = calendar.month_name[self.prev_date.month]
            self.pdfresult["header"]["customer"] = str(self.report.customer["name"])
            self.pdfresult["header"]["month_year"] = str(calendar.month_name[self.report.month]) + " " + str(
                self.report.year)
            self.pdfresult["header"]["report_type"] = self.report_type
        except Exception as e:
            self.report.last_run_status = "Error"
            self.report.save()
            raise e

    def update_report_status(self):
        try:
            print("Updating the report status")
            accountant = User.objects.get(id=self.customer['accountant'])
            self.report.qc = User.objects.get(id=self.customer['qc'])
            self.report.crm = User.objects.get(id=self.customer['crm'])
            self.report.qb_api = self.dashboardresult
            self.report.results = self.pdfresult
            self.report.status = "Review"
            self.report.save()
        except Exception as e:
            self.report.last_run_status = "Error"
            self.report.save()
            raise e

    def add_event(self):
        try:
            print("Adding event")
            d = datetime.now().astimezone(timezone('Asia/Kolkata'))
            mon = d.strftime("%b")
            message = self.report_type + " Report Version - " + str(self.report.version) + "has been created"
            event = {
                "modifierid": self.user.id,
                "modifiername": self.user.username,
                "date": d.strftime('%Y-%m-%d %H:%M:%S'),
                "month": mon,
                "eventtype": "lifecycle",
                "eventvalue": "Updated",
                "message": message,
                "status": "Review"
            }
            self.report.activity.append(event)
            self.report.save()
        except Exception as e:
            self.report.last_run_status = "Error"
            self.report.save()
            raise e

    def post_process(self):
        try:
            print("Adding comments etc")

            def delete_old_attachments():
                # Deleting old output files
                links = self.report.pdf_attachments.all()
                s3 = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                  config=Config(signature_version='s3v4'), region_name='ap-south-1')
                for i in range(len(links)):
                    attach = links[i]
                    fileurl = settings.AWS_PRIVATE_MEDIA_LOCATION + "/" + attach.document_link
                    s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=fileurl)
                    attach.delete()

            delete_old_attachments()
            d = datetime.now().astimezone(timezone('Asia/Kolkata'))
            self.report.generated_at = d
            self.report.save()
        except Exception as e:
            self.report.last_run_status = "Error"
            self.report.save()
            raise e

    def setup_reportengine_headers(self, format):
        try:
            print("Setting up the report engine headers")
            if format == "pdf":
                self.jsparams = {
                    "template": {"name": "PE-Main", "recipe": "chrome-pdf"},
                    "data": {"result": self.pdfresult},
                    "options": {"reports": {"save": True}, "reportName": "myreport"}
                }
        except Exception as e:
            self.report.last_run_status = "Error"
            self.report.save()
            raise e

    def attach_outputs(self, format):
        print("Attaching the outputs")
        try:
            if format in ["PDF", "pdf"]:
                jsreportdata = settings.JSREPORTENGINE_DATA
                fileurl_pdf = jsreportdata + self.pdf_link
                rename_pdf_url = jsreportdata + self.file_suffix + "_" + self.pdf_link
                os.rename(fileurl_pdf, rename_pdf_url)
                fileurl_pdf = rename_pdf_url
                localfile = open(fileurl_pdf, "rb")
                djangofile = File(localfile)
                filepath = self.get_file_path(self.user.username, localfile.name)
                fileurl = 'https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN, settings.AWS_PRIVATE_MEDIA_LOCATION)
                fileurl += filepath
                pdffile = PrivatePdfDocument(user=self.user, record=self.report, upload=djangofile,
                                             document_link=filepath)
                pdffile.save()
        except Exception as e:
            self.report.last_run_status = "Error"
            self.report.save()
            raise e

    def notify_users(self, channel):
        try:
            print("Notifying the users")
            if "email" in channel:
                subject = 'Report Created'
                body = 'Hi, A new report has been created and has been sent for your approval. Please login to your ' \
                       'firstcourse workflow to check it. '
                sender = "tech@firstcourse.in"
                accountant = User.objects.get(id=self.customer['accountant'])
                receiver = [accountant.email]
                Email_Notification_Generator(sender, receiver, subject, body)
        except Exception as e:
            self.report.last_run_status = "Error"
            self.report.save()
            raise e

    def complete_process(self):
        try:
            self.report.last_run_status = "Success"
            self.report.celery_task_id = ""
            self.report.save()
        except Exception as e:
            self.report.last_run_status = "Error"
            self.report.save()
            raise e
