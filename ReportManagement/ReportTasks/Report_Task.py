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

from reportbuilders.Builders  import Report_Builder



''' Base Class for Perfoming the Complete Task'''
class Task():
    #Some Tasks contain pull API service
    def __init__(self):
        self.task_id=''
        self.ReportBuilder=Report_Builder()
        self.user_id=None
        self.report_id=None
        self.cust_id=None
        self.jsparams={}
        self.pdf_link=''
        pass
    def input_json_path(self,name,year,month):
        print("input json path")
        return 'media/input/{0}/{1}/{2}/'.format(name,year,month)
    def get_file_path(self,name,filename):
        d = date.today()
        mon=d.strftime("%b")
        actualfilename=os.path.basename(filename)
        return 'input/{0}/{1}/{2}'.format(name,mon,actualfilename)
    '''Prepare the necessary objects like extracting report object, user object etc'''
    def prepare_task(self):
        pass
    '''Call the Qb API to obtain the data '''
    def get_data(self):
        pass
    '''Call the Report Builder Object to generate the data'''
    def perform_task(self):
        pass
    '''Call the Post process the report such as removing old PDF files, adding comments etc'''
    def post_process(self):
        pass
    '''Call the Report Builder Object to update the report status to review'''
    def update_status(self):
        pass
    '''Call the Report Builder Object to setup the json result headers with month, customer name, report type, etc'''
    def setup_report_headers(self):
        pass
    '''Call the Report Builder Object to add event to the report'''
    def add_event(self):
        pass
    '''Call to setup JSreport headers etc'''
    def setup_reportengine_headers(self,format):
        pass
    '''Call the Report Builder Object to generate the PDF output etc'''
    def generate_outputs(self,format):
        if(format=="PDF" or format=="pdf"):
            # print("JS Params are")
            # print(self.jsparams)
            jsreporturl=settings.JSREPORTENGINE_HOST+":"+settings.JSREPORTENGINE_PORT+"/api/report"

            jsrep=requests.post(jsreporturl,json=self.jsparams,auth=('ca-reporting','fatca123@'))
            link=jsrep.headers['Report-BlobName']
            self.pdf_link=link
        pass
    '''Call to Notify users through various mediums'''
    def notify_users(self):
        pass




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
