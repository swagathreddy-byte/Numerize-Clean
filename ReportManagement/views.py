from django.shortcuts import render,redirect
# Create your views here.
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from datetime import datetime,date
from django.conf import settings
import boto3
from django.http import HttpResponse,JsonResponse
from .models import *
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from .Serializer import  *
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .choices import *
from django.core.paginator import Paginator
import requests
from django.http import FileResponse, Http404
from django.core.files.storage import FileSystemStorage
from .report_generator import *
import magic
from django.core.files import File
from botocore.client import Config
from slugify import Slugify,slugify
from zipfile import ZipFile
import pathlib
import json
import os
import shutil
from .tasks import *
from django.contrib import messages
from celery.result import AsyncResult

from django.db.models.signals import post_save
from django.dispatch import receiver
import pytz
# from arango import ArangoClient
import numpy as np
from itertools import groupby
from pytz import timezone
from EmployeeManagement.models import *
from CustomerManagement.models import *

def get_file_path(name,filename):
    d = date.today()
    mon=d.strftime("%b")
    actualfilename=os.path.basename(filename)
    return 'input/{0}/{1}/{2}'.format(name,mon,actualfilename)


def validate_file(filepath,mimetypes):
    mime = magic.Magic(mime=True)
    print(filepath)
    mimetype=mime.from_file(filepath)
    print("Mime type is ")
    print(mimetype)
    if(mimetype not in mimetypes):
        return False
    else:
        return True

custom_slugify=Slugify()
custom_slugify.safe_chars = '.xlsx'

@login_required(login_url='/accounts/login')
def process_report(request):

    if request.method == 'POST':
        if request.user.groups.filter(name='Accountant').exists():
            print("Hey upload file called")
            print(request.POST.get("report_type"))
            print(request.POST.get("report_id"))
            if("report_type" not in request.POST):
                print("Hey its not there.")
                response = JsonResponse({'status': 'Invalid', 'message': 'Invalid Form. Missing parameters'})
                response.status_code = 400
                return response
            elif(request.POST.get("report_type")==""):
                response = JsonResponse({'status': 'Invalid', 'message': 'Invalid Form. Report type not present'})
                response.status_code = 400
                return response
            elif(request.POST.get("report_id")=="" and request.POST.get("report_type")!="CL_ST"):
                response = JsonResponse({'status': 'Invalid', 'message': 'Invalid Form. Report id not present'})
                response.status_code = 400
                return response
            else:
                #Handle Profit Loss Statement
                if(request.POST.get("report_type")=="P_L"):
                    if(("pl_qb_in_file" not in request.FILES) and ("pl_cat_in_file" not in request.FILES)):
                        response = JsonResponse({'status': 'Valid', 'message': 'Incomplete inputs'})
                        response.status_code = 400
                        return response
                    else:
                        qbfile = request.FILES['pl_qb_in_file']
                        catfile= request.FILES['pl_cat_in_file']
                        fs = FileSystemStorage(location='media/uploads')

                        qb_filename = fs.save(custom_slugify(qbfile.name), qbfile)
                        cat_filename=fs.save(custom_slugify(catfile.name), catfile)


                        qb_url=fs.url(qb_filename)
                        cat_url=fs.url(cat_filename)


                        #Absolute path
                        qb_url=settings.BASE_DIR+"/media/uploads/"+qb_url
                        cat_url=settings.BASE_DIR+"/media/uploads/"+cat_url

                        print(qb_url)
                        mimetypes=('application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                        if(validate_file(qb_url,mimetypes) and validate_file(cat_url,mimetypes)):
                            print("valid files")
                            report_id=request.POST.get("report_id")
                            r=Report.objects.get(id=report_id)

                            cust=Customer.objects.get(id=r.customer.id)
                            file_suffix=custom_slugify(str(cust.name))

                            #Async Task- Report Generator
                            output=generate_profit_loss.delay(qb_url,cat_url,file_suffix,request.user.id,cust.id,request.POST.get("report_id"))

                            response = JsonResponse({'status': 'Valid', 'message': 'File processed','fileurl':'/get_file/','taskid':output.task_id})
                            response.status_code = 200
                            return response

                        else:
                            response = JsonResponse({'status': 'Error', 'message': 'Invalid File types'})
                            response.status_code = 400
                            return response

                #Handle Closing Stock Summary
                elif(request.POST.get("report_type")=="CL_ST"):
                    print("CL_ST file requested")
                    if("cl_st_in_file" not in request.FILES):
                        print("Is cs st there?")
                        response = JsonResponse({'status': 'Invalid', 'message': 'Incomplete form.'})
                        response.status_code = 400
                        return response
                    elif("cl_qb_in_file" not in request.FILES):
                        print("Is not there?")
                        response = JsonResponse({'status': 'Invalid', 'message': 'Incomplete form.'})
                        response.status_code = 400
                        return response
                    else:
                        print("Files are there")
                        stfile = request.FILES['cl_st_in_file']
                        qbfile= request.FILES['cl_qb_in_file']
                        fs = FileSystemStorage(location='media/uploads')
                        qb_filename = fs.save(custom_slugify(qbfile.name), qbfile)
                        st_filename=fs.save(custom_slugify(stfile.name), stfile)

                        qb_url=fs.url(qb_filename)
                        st_url=fs.url(st_filename)
                        qb_url=settings.BASE_DIR+"/media/uploads/"+qb_url
                        st_url=settings.BASE_DIR+"/media/uploads/"+st_url
                        print(qb_url)
                        print(st_url)
                        mimetypes=('application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                        if(validate_file(qb_url,mimetypes) and validate_file(st_url,mimetypes)):
                            #both files are excel files
                            print("Both are excel files")
                            cust=Customer.objects.get(id=int(request.POST.get("customer_name")))
                            print("Customer name is ");
                            print(cust)
                            file_suffix=custom_slugify(str(cust.name))
                            output=Closing_Stock(st_url,qb_url,file_suffix)

                            if(output.status=="Success"):
                                print(request.POST.get("customer_name"))
                                r=Report(report_type=request.POST.get("report_type"),owner=request.user,customer=cust,status="Generated")
                                r.save()
                                report_url=settings.BASE_DIR+"/"+output.fname
                                localfile=open(report_url,"rb")
                                djangofile=File(localfile)

                                filepath=get_file_path(request.user.username,localfile.name)
                                print(filepath)
                                # filepath='media/private/'+filepath
                                fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
                                fileurl+=filepath
                                outputfile=PrivateExcelDocument(user=request.user,record=r,upload=djangofile,document_link=filepath)
                                outputfile.save()

                                report_url=settings.BASE_DIR+"/"+output.fname1
                                localfile=open(report_url,"rb")
                                djangofile=File(localfile)
                                filepath=get_file_path(request.user.username,localfile.name)
                                # filepath='media/private/'+filepath
                                fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
                                fileurl+=filepath
                                outputfile=PrivateExcelDocument(user=request.user,record=r,upload=djangofile,document_link=filepath)
                                outputfile.save()


                                fileurl='/get_file/'+str(r.id)+'/'
                                # if os.path.exists(cat_url):
                                #     os.remove(cat_url)
                                response = JsonResponse({'status': 'Valid', 'message': 'File processed','fileurl':fileurl})
                                response.status_code = 200
                                return response
                            else:
                                print("Failed")
                                response = JsonResponse({'status': 'Error', 'message': 'Error in generating report'})
                                response.status_code = 400
                                return response

                        else:
                            print("Invalid files")
                            response = JsonResponse({'status': 'Error', 'message': 'Invalid file formats'})
                            response.status_code = 400
                            return response
                    #Generate report
                    #If report is successful
                    #then create report record
                    #create document model
                    #save object

                #GST Summary
                elif(request.POST.get("report_type")=="GST"):

                    # if("gst_input_tax_credit" not in request.FILES):
                    #     response = JsonResponse({'status': 'Invalid', 'message': 'Incomplete form.'})
                    #     response.status_code = 400
                    #     return response
                    if(("gst_input_b2b" not in request.FILES) and ("gst_input_b2c" not in request.FILES)):
                        response = JsonResponse({'status': 'Invalid', 'message': 'Incomplete form.'})
                        response.status_code = 400
                        return response
                    else:
                        report_id=request.POST.get("report_id")
                        r=Report.objects.get(id=report_id)
                        cust=Customer.objects.get(id=r.customer.id)

                        if("gst_input_b2b" in request.FILES) and ("gst_input_b2c" in request.FILES):
                            if('gst_input_tax_credit' in request.FILES):
                                print("Both b2b and b2c are there")
                                tax_credit = request.FILES['gst_input_tax_credit']
                                b2c_input= request.FILES['gst_input_b2c']
                                b2b_input= request.FILES['gst_input_b2b']

                                fs = FileSystemStorage(location='media/uploads')
                                tax_credit_filename = fs.save(custom_slugify(tax_credit.name), tax_credit)
                                b2c_input_filename = fs.save(custom_slugify(b2c_input.name), b2c_input)
                                b2b_input_filename = fs.save(custom_slugify(b2b_input.name), b2b_input)
                                tax_credit_url=fs.url(tax_credit_filename)
                                b2c_input_url=fs.url(b2c_input_filename)
                                b2b_input_url=fs.url(b2b_input_filename)
                                tax_credit_url=settings.BASE_DIR+"/media/uploads/"+tax_credit_url
                                b2c_input_url=settings.BASE_DIR+"/media/uploads/"+b2c_input_url
                                b2b_input_url=settings.BASE_DIR+"/media/uploads/"+b2b_input_url
                                mimetypes=('application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                                if(validate_file(tax_credit_url,mimetypes) and validate_file(b2c_input_url,mimetypes) and validate_file(b2b_input_url,mimetypes)):

                                    file_suffix=custom_slugify(str(cust.name))
                                    output=generate_gst.delay(b2c_input_url,b2b_input_url,tax_credit_url,file_suffix,request.user.id,cust.id,report_id)
                                    response = JsonResponse({'status': 'Valid', 'message': 'Report processing','taskid':output.task_id})
                                    response.status_code = 200
                                    return response

                                else:
                                    response = JsonResponse({'status': 'Error', 'message': 'Invalid file formats'})
                                    response.status_code = 400
                                    return response
                            else:

                                b2c_input= request.FILES['gst_input_b2c']
                                b2b_input= request.FILES['gst_input_b2b']
                                fs = FileSystemStorage(location='media/uploads')
                                b2c_input_filename = fs.save(custom_slugify(b2c_input.name), b2c_input)
                                b2b_input_filename = fs.save(custom_slugify(b2b_input.name), b2b_input)
                                b2c_input_url=fs.url(b2c_input_filename)
                                b2b_input_url=fs.url(b2b_input_filename)
                                b2c_input_url=settings.BASE_DIR+"/media/uploads/"+b2c_input_url
                                b2b_input_url=settings.BASE_DIR+"/media/uploads/"+b2b_input_url
                                mimetypes=('application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                                if(validate_file(b2c_input_url,mimetypes) and validate_file(b2b_input_url,mimetypes)):
                                    #both files are excel files
                                    tax_credit_url=''
                                    file_suffix=custom_slugify(str(cust.name))
                                    output=generate_gst.delay(b2c_input_url,b2b_input_url,tax_credit_url,file_suffix,request.user.id,cust.id,report_id)
                                    response = JsonResponse({'status': 'Valid', 'message': 'Report processing','taskid':output.task_id})
                                    response.status_code = 200
                                    return response
                                else:
                                    response = JsonResponse({'status': 'Error', 'message': 'Invalid file formats'})
                                    response.status_code = 400
                                    return response

                        elif("gst_input_b2b" in request.FILES) and ("gst_input_b2c" not in request.FILES):
                            if('gst_input_tax_credit' in request.FILES):
                                print("Only b2b are there")
                                tax_credit = request.FILES['gst_input_tax_credit']
                                b2b_input= request.FILES['gst_input_b2b']
                                fs = FileSystemStorage(location='media/uploads')
                                tax_credit_filename = fs.save(custom_slugify(tax_credit.name), tax_credit)

                                b2b_input_filename = fs.save(custom_slugify(b2b_input.name), b2b_input)
                                tax_credit_url=fs.url(tax_credit_filename)

                                b2b_input_url=fs.url(b2b_input_filename)
                                tax_credit_url=settings.BASE_DIR+"/media/uploads/"+tax_credit_url

                                b2b_input_url=settings.BASE_DIR+"/media/uploads/"+b2b_input_url
                                mimetypes=('application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                                if(validate_file(tax_credit_url,mimetypes) and validate_file(b2b_input_url,mimetypes)):
                                    #both files are excel files
                                    b2c_input_url=''
                                    file_suffix=custom_slugify(str(cust.name))
                                    output=generate_gst.delay(b2c_input_url,b2b_input_url,tax_credit_url,file_suffix,request.user.id,cust.id,report_id)
                                    response = JsonResponse({'status': 'Valid', 'message': 'Report processing','taskid':output.task_id})
                                    response.status_code = 200
                                    return response
                                else:
                                    response = JsonResponse({'status': 'Error', 'message': 'Invalid file formats'})
                                    response.status_code = 400
                                    return response
                            else:
                                print("Only b2b are there")
                                b2b_input= request.FILES['gst_input_b2b']
                                fs = FileSystemStorage(location='media/uploads')
                                b2b_input_filename = fs.save(custom_slugify(b2b_input.name), b2b_input)
                                b2b_input_url=fs.url(b2b_input_filename)
                                b2b_input_url=settings.BASE_DIR+"/media/uploads/"+b2b_input_url
                                mimetypes=('application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                                if( validate_file(b2b_input_url,mimetypes)):
                                    #both files are excel files
                                    b2c_input_url=''
                                    tax_credit_url=''
                                    file_suffix=custom_slugify(str(cust.name))
                                    output=generate_gst.delay(b2c_input_url,b2b_input_url,tax_credit_url,file_suffix,request.user.id,cust.id,report_id)
                                    response = JsonResponse({'status': 'Valid', 'message': 'Report processing','taskid':output.task_id})
                                    response.status_code = 200
                                    return response
                                else:
                                    response = JsonResponse({'status': 'Error', 'message': 'Invalid file formats'})
                                    response.status_code = 400
                                    return response

                        elif("gst_input_b2b" not in request.FILES) and ("gst_input_b2c" in request.FILES):
                            if('gst_input_tax_credit' in request.FILES):
                                tax_credit = request.FILES['gst_input_tax_credit']
                                b2c_input= request.FILES['gst_input_b2c']
                                fs = FileSystemStorage(location='media/uploads')
                                tax_credit_filename = fs.save(custom_slugify(tax_credit.name), tax_credit)
                                b2c_input_filename = fs.save(custom_slugify(b2c_input.name), b2c_input)
                                tax_credit_url=fs.url(tax_credit_filename)
                                b2c_input_url=fs.url(b2c_input_filename)
                                tax_credit_url=settings.BASE_DIR+"/media/uploads/"+tax_credit_url
                                b2c_input_url=settings.BASE_DIR+"/media/uploads/"+b2c_input_url
                                mimetypes=('application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                                if(validate_file(tax_credit_url,mimetypes) and validate_file(b2c_input_url,mimetypes)):
                                    #both files are excel files
                                    b2b_input_url=''
                                    file_suffix=custom_slugify(str(cust.name))
                                    output=generate_gst.delay(b2c_input_url,b2b_input_url,tax_credit_url,file_suffix,request.user.id,cust.id,report_id)
                                    response = JsonResponse({'status': 'Valid', 'message': 'Report processing','taskid':output.task_id})
                                    response.status_code = 200
                                    return response

                            else:
                                tax_credit=''
                                b2c_input= request.FILES['gst_input_b2c']
                                fs = FileSystemStorage(location='media/uploads')
                                b2c_input_filename = fs.save(custom_slugify(b2c_input.name), b2c_input)
                                b2c_input_url=fs.url(b2c_input_filename)
                                b2c_input_url=settings.BASE_DIR+"/media/uploads/"+b2c_input_url
                                mimetypes=('application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                                if(validate_file(b2c_input_url,mimetypes)):
                                    #both files are excel files
                                    b2b_input_url=''
                                    tax_credit_url=''
                                    file_suffix=custom_slugify(str(cust.name))
                                    output=generate_gst.delay(b2c_input_url,b2b_input_url,tax_credit_url,file_suffix,request.user.id,cust.id,report_id)
                                    response = JsonResponse({'status': 'Valid', 'message': 'Report processing','taskid':output.task_id})
                                    response.status_code = 200
                                    return response
                                else:
                                    response = JsonResponse({'status': 'Error', 'message': 'Invalid file formats'})
                                    response.status_code = 400
                                    return response

                #Sales Channel Reconciliation
                elif(request.POST.get("report_type")=="S_C_R"):
                    if("bank_transaction_input_file" not in request.FILES):
                        response = JsonResponse({'status': 'Valid', 'message': 'Incomplete inputs'})
                        response.status_code = 400
                        return response
                    else:
                        #Extracting the files
                        swiggy_input_file = ''
                        zomato_input_file= ''
                        dunzo_input_file= ''
                        nearbuy_input_file = ''
                        dineout_input_file= ''
                        bank_transaction_input_file=''

                        swiggy_input_url=''
                        zomato_input_url=''
                        dunzo_input_url=''
                        nearbuy_input_url=''
                        dineout_input_url=''
                        bank_transaction_input_url=''

                        swiggy_input_zip_url=''
                        zomato_input_zip_url=''
                        nearbuy_input_zip_url=''
                        dunzo_input_zip_url=''
                        dineout_input_zip_url=''

                        swiggy_input_pos=''
                        zomato_input_pos=''
                        dunzo_input_pos=''
                        nearbuy_input_pos=''
                        dineout_input_pos=''
                        d=datetime.now().astimezone(timezone('Asia/Kolkata'))
                        location='media/uploads/scr/'+request.user.username+"/"+d.strftime('%Y-%m-%d-%H-%M')+"/"
                        fs = FileSystemStorage(location=location)
                        if('swiggy_input_file' in request.FILES and 'swiggy_input_pos' not in request.POST):
                            response = JsonResponse({'status': 'Valid', 'message': 'swiggy input pos missing'})
                            response.status_code = 400
                            return response
                        else:
                            swiggy_input_file=request.FILES['swiggy_input_file']
                            swiggy_input_pos=request.POST["swiggy_input_pos"]
                            filename=fs.save(custom_slugify(swiggy_input_file.name), swiggy_input_file)
                            swiggy_input_url=fs.url(filename)
                            swiggy_input_url=settings.BASE_DIR+"/"+location+swiggy_input_url
                            zippath=settings.BASE_DIR+"/"+location+"input_swiggy"
                            with ZipFile(swiggy_input_url, 'r') as z:
                                z.extractall(path=zippath)
                            swiggy_input_zip_url=swiggy_input_url
                            swiggy_input_url=zippath
                        if('zomato_input_file' in request.FILES and 'zomato_input_pos' not in request.POST):
                            response = JsonResponse({'status': 'Valid', 'message': 'Zomato Input POS missing'})
                            response.status_code = 400
                            return response
                        else:
                            zomato_input_file=request.FILES['zomato_input_file']
                            zomato_input_pos=request.POST["zomato_input_pos"]
                            filename=fs.save(custom_slugify(zomato_input_file.name), zomato_input_file)
                            zomato_input_url=fs.url(filename)
                            zomato_input_url=settings.BASE_DIR+"/"+location+zomato_input_url
                            zippath=settings.BASE_DIR+"/"+location+"input_zomato"
                            with ZipFile(zomato_input_url, 'r') as z:
                                z.extractall(path=zippath)
                            zomato_input_zip_url=zomato_input_url
                            zomato_input_url=zippath
                        if('dunzo_input_file' in request.FILES and 'dunzo_input_pos' not in request.POST):
                            response = JsonResponse({'status': 'Valid', 'message': 'Dunzo Input POS missing'})
                            response.status_code = 400
                            return response
                        else:
                            dunzo_input_file=request.FILES['dunzo_input_file']
                            dunzo_input_pos=request.POST["dunzo_input_pos"]
                            filename=fs.save(custom_slugify(dunzo_input_file.name), dunzo_input_file)
                            dunzo_input_url=fs.url(filename)
                            dunzo_input_url=settings.BASE_DIR+"/"+location+dunzo_input_url
                            zippath=settings.BASE_DIR+"/"+location+"input_dunzo"
                            with ZipFile(dunzo_input_url, 'r') as z:
                                z.extractall(path=zippath)
                            dunzo_input_zip_url=dunzo_input_url
                            dunzo_input_url=zippath
                        if('nearbuy_input_file' in request.FILES and 'nearbuy_input_pos' not in request.POST):
                            response = JsonResponse({'status': 'Valid', 'message': 'Nearbuy Input POS missing'})
                            response.status_code = 400
                            return response
                        else:
                            nearbuy_input_file=request.FILES['nearbuy_input_file']
                            nearbuy_input_pos=request.POST["nearbuy_input_pos"]
                            filename=fs.save(custom_slugify(nearbuy_input_file.name), nearbuy_input_file)
                            nearbuy_input_url=fs.url(filename)
                            nearbuy_input_url=settings.BASE_DIR+"/"+location+nearbuy_input_url
                            zippath=settings.BASE_DIR+"/"+location+"input_nearbuy"
                            with ZipFile(nearbuy_input_url, 'r') as z:
                                z.extractall(path=zippath)
                            nearbuy_input_zip_url=nearbuy_input_url
                            nearbuy_input_url=zippath
                        if('dineout_input_file' in request.FILES and 'dineout_input_pos' not in request.POST):
                            response = JsonResponse({'status': 'Valid', 'message': 'Dineout Input POS missing'})
                            response.status_code = 400
                            return response
                        else:
                            dineout_input_file=request.FILES['dineout_input_file']
                            dineout_input_pos=request.POST["dineout_input_pos"]
                            filename=fs.save(custom_slugify(dineout_input_file.name), dineout_input_file)
                            dineout_input_url=fs.url(filename)
                            dineout_input_url=settings.BASE_DIR+"/"+location+dineout_input_url
                            zippath=settings.BASE_DIR+"/"+location+"input_dineout"
                            with ZipFile(dineout_input_url, 'r') as z:
                                z.extractall(path=zippath)
                            dineout_input_zip_url=dineout_input_url
                            dineout_input_url=zippath
                        if('bank_transaction_input_file' not in request.FILES ):
                            response = JsonResponse({'status': 'Valid', 'message': 'Bank Transaction missing'})
                            response.status_code = 400
                            return response
                        else:
                            bank_transaction_input_file=request.FILES['bank_transaction_input_file']
                            filename=fs.save(custom_slugify(bank_transaction_input_file.name), bank_transaction_input_file)
                            bank_transaction_input_url=fs.url(filename)
                            bank_transaction_input_url=settings.BASE_DIR+"/"+location+bank_transaction_input_url
                            #Saving the files


                            if os.path.exists(dineout_input_zip_url):
                                os.remove(dineout_input_zip_url)
                            if os.path.exists(zomato_input_zip_url):
                                os.remove(zomato_input_zip_url)
                            if os.path.exists(swiggy_input_zip_url):
                                os.remove(swiggy_input_zip_url)
                            if os.path.exists(dunzo_input_zip_url):
                                os.remove(dunzo_input_zip_url)
                            if os.path.exists(nearbuy_input_zip_url):
                                os.remove(nearbuy_input_zip_url)

                        #Getting absolute urls

                        exceltypes=('application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                        ziptypes=('application/zip','application/x-rar')

                        print(swiggy_input_url)
                        if(validate_file(bank_transaction_input_url,exceltypes)):
                            report_id=request.POST.get("report_id")

                            r=Report.objects.get(id=report_id)

                            cust=Customer.objects.get(id=r.customer.id)
                            tday=date.today().strftime('%Y-%m-%d')
                            file_suffix=custom_slugify(str(cust.name))

                            # generate_scr_report(bankTranx_file, swiggy_file, zomato_file, dunzo_file, nearbuy_file, dineout_file, swiggy_pos, zomato_pos, dunzo_pos, nearbuy_pos, dineout_pos,file_suffix,user_id,cust_id,report_id)

                            output=generate_scr_report.delay(bank_transaction_input_url,
                                                             swiggy_input_url,
                                                             zomato_input_url,
                                                             dunzo_input_url,
                                                             nearbuy_input_url,
                                                             dineout_input_url,
                                                             swiggy_input_pos,
                                                             zomato_input_pos,
                                                             dunzo_input_pos,
                                                             nearbuy_input_pos,
                                                             dineout_input_pos,
                                                             file_suffix,
                                                             request.user.id,
                                                             cust.id,
                                                             report_id)
                            # print(result.task_id)
                            response = JsonResponse({'status': 'Valid', 'message': 'Report processing','taskid':output.task_id})
                            response.status_code = 200
                            return response

                        else:
                            response = JsonResponse({'status': 'Error', 'message': 'Invalid File types'})
                            response.status_code = 400
                            return response

                #Swiggy Invoice Level Reconciliation
                elif(request.POST.get("report_type")=="SW_IN"):
                    response = JsonResponse({'status': 'Valid', 'message': 'Swiggy Invoice Level Reconciliation not implemented'})
                    response.status_code = 200
                    return response

                #Swiggy Dump Level Reconciliation
                elif(request.POST.get("report_type")=="SW_DUMP"):
                    if(("input_data_in_file" not in request.FILES) and ("weekly_mail_in_file" not in request.FILES) and ("master_data_in_file" not in request.FILES)):
                        response = JsonResponse({'status': 'Valid', 'message': 'Incomplete inputs'})
                        response.status_code = 400
                        return response
                    else:
                        #Extracting the files
                        in_data_file = request.FILES['input_data_in_file']
                        week_in_file= request.FILES['weekly_mail_in_file']
                        master_in_file = request.FILES['master_data_in_file']
                        #Saving the files
                        fs = FileSystemStorage(location='media/uploads/sdump/')
                        in_data_filename = fs.save(custom_slugify(in_data_file.name), in_data_file)
                        week_in_filename = fs.save(custom_slugify(week_in_file.name), week_in_file)
                        master_in_filename = fs.save(custom_slugify(master_in_file.name), master_in_file)
                        #Getting the urls
                        in_data_url=fs.url(in_data_filename)
                        week_in_data_url=fs.url(week_in_filename)
                        master_in_data_url=fs.url(master_in_filename)

                        #Getting absolute urls
                        in_data_url=settings.BASE_DIR+"/media/uploads/sdump/"+in_data_url
                        week_in_data_url=settings.BASE_DIR+"/media/uploads/sdump/"+week_in_data_url
                        master_in_data_url=settings.BASE_DIR+"/media/uploads/sdump/"+master_in_data_url

                        exceltypes=('application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                        ziptypes=('application/zip','application/x-rar')

                        if(validate_file(in_data_url,ziptypes) and validate_file(week_in_data_url,ziptypes) and validate_file(master_in_data_url,exceltypes)):
                            report_id=request.POST.get("report_id")

                            r=Report.objects.get(id=report_id)

                            cust=Customer.objects.get(id=r.customer.id)
                            tday=date.today().strftime('%Y-%m-%d')
                            unzip_url=settings.BASE_DIR+"/media/uploads/sdump/"+str(request.user)+"/"+custom_slugify(cust.name)+"/"+tday+"/"
                            file_suffix=custom_slugify(str(cust.name))
                            input_file_url=""
                            with ZipFile(in_data_url, 'r') as z:
                                z.extractall(unzip_url)
                                print(z.infolist()[0].filename)
                                input_file_url=unzip_url+str(z.infolist()[0].filename)

                            week_input_file_url=''
                            with ZipFile(week_in_data_url, 'r') as z:
                                z.extractall(unzip_url)
                                week_input_file_url=unzip_url+str(z.infolist()[0].filename)

                            output=generate_swiggy_dump_report.delay(input_file_url,week_input_file_url,master_in_data_url,unzip_url,request.user.id,cust.id,report_id,in_data_url,week_in_data_url)
                            # print(result.task_id)
                            response = JsonResponse({'status': 'Valid', 'message': 'Report processing','taskid':output.task_id})
                            response.status_code = 200
                            return response

                        else:
                            response = JsonResponse({'status': 'Error', 'message': 'Invalid File types'})
                            response.status_code = 400
                            return response
                #TDS
                elif(request.POST.get("report_type")=="TDS"):
                    response = JsonResponse({'status': 'Valid', 'message': 'TDS Summary not implemented'})
                    response.status_code = 200
                    return response

                elif(request.POST.get("report_type")=="CON_ANA"):
                    print("inside con_ana")
                    cs_m0_file = request.FILES['cs_cur_input_file']
                    print(cs_m0_file)
                    cs_m1_file=''
                    cs_m2_file = ''
                    cs_m3_file = ''
                    os_m1_file = ''
                    os_m2_file = ''
                    os_m3_file = ''

                    if ('cs_m1_input_file' in request.FILES):
                        cs_m1_file= request.FILES['cs_m1_input_file']
                    if ('cs_m2_input_file' in request.FILES):
                        cs_m2_file= request.FILES['cs_m2_input_file']
                    if ('cs_m3_input_file' in request.FILES):
                        cs_m3_file= request.FILES['cs_m3_input_file']

                    os_m0_file = request.FILES['os_cur_input_file']
                    if ('os_m1_input_file' in request.FILES):
                        os_m1_file= request.FILES['os_m1_input_file']
                    if ('os_m2_input_file' in request.FILES):
                        os_m2_file= request.FILES['os_m2_input_file']
                    if ('os_m3_input_file' in request.FILES):
                        os_m3_file= request.FILES['os_m3_input_file']


                    ca_pur_file=request.FILES['ca_pur_file']
                    print("before media uploads")

                    fs = FileSystemStorage(location='media/uploads')
                    mimetypes = ('application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

                    print(cs_m1_file)
                    cs_m0_filename = fs.save(custom_slugify(cs_m0_file.name), cs_m0_file)
                    cs_m0_url = fs.url(cs_m0_filename)
                    cs_m0_url = settings.BASE_DIR + "/media/uploads/" + cs_m0_url
                    cs_m0_val = validate_file(cs_m0_url, mimetypes)

                    cs_m1_url = ''
                    cs_m2_url = ''
                    cs_m3_url = ''
                    cs_m1_val = ''
                    cs_m2_val = ''
                    cs_m3_val = ''

                    if(cs_m1_file!=''):
                        cs_m1_filename = fs.save(custom_slugify(cs_m1_file.name), cs_m1_file)
                        cs_m1_url = fs.url(cs_m1_filename)
                        cs_m1_url = settings.BASE_DIR + "/media/uploads/" + cs_m1_url
                        cs_m1_val = validate_file(cs_m1_url, mimetypes)

                    if(cs_m2_file!=''):
                        cs_m2_filename = fs.save(custom_slugify(cs_m2_file.name), cs_m2_file)
                        cs_m2_url = fs.url(cs_m2_filename)
                        cs_m2_url = settings.BASE_DIR + "/media/uploads/" + cs_m2_url
                        cs_m2_val = validate_file(cs_m2_url, mimetypes)

                    if(cs_m3_file!=''):
                        cs_m3_filename = fs.save(custom_slugify(cs_m3_file.name), cs_m3_file)
                        cs_m3_url = fs.url(cs_m3_filename)
                        cs_m3_url = settings.BASE_DIR + "/media/uploads/" + cs_m3_url
                        cs_m3_val = validate_file(cs_m3_url, mimetypes)

                    os_m0_filename = fs.save(custom_slugify(os_m0_file.name), os_m0_file)
                    os_m0_url = fs.url(os_m0_filename)
                    os_m0_url = settings.BASE_DIR + "/media/uploads/" + os_m0_url
                    os_m0_val = validate_file(os_m0_url, mimetypes)
                    os_m1_url=''
                    os_m2_url=''
                    os_m3_url = ''
                    os_m1_val = ''
                    os_m2_val = ''
                    os_m3_val = ''
                    if(os_m1_file!=''):
                        os_m1_filename = fs.save(custom_slugify(os_m1_file.name), os_m1_file)
                        os_m1_url = fs.url(os_m1_filename)
                        os_m1_url = settings.BASE_DIR + "/media/uploads/" + os_m1_url
                        os_m1_val = validate_file(os_m1_url, mimetypes)

                    if(os_m2_file!=''):
                        os_m2_filename = fs.save(custom_slugify(os_m2_file.name), os_m2_file)
                        os_m2_url = fs.url(os_m2_filename)
                        os_m2_url = settings.BASE_DIR + "/media/uploads/" + os_m2_url
                        os_m2_val = validate_file(os_m2_url, mimetypes)

                    if(os_m3_file!=''):
                        os_m3_filename = fs.save(custom_slugify(os_m3_file.name), os_m3_file)
                        os_m3_url = fs.url(os_m3_filename)
                        os_m3_url = settings.BASE_DIR + "/media/uploads/" + os_m3_url
                        os_m3_val = validate_file(os_m3_url, mimetypes)

                    ca_pur_filename = fs.save(custom_slugify(ca_pur_file.name), ca_pur_file)
                    ca_pur_url=fs.url(ca_pur_filename)
                    ca_pur_url=settings.BASE_DIR+"/media/uploads/"+ca_pur_url
                    ca_pur_val=validate_file(ca_pur_url,mimetypes)
                    print("after validate file")
                    if(cs_m0_val and (cs_m1_val or cs_m2_val or cs_m3_val) and os_m0_val and (os_m1_val or os_m2_val or os_m3_val) and ca_pur_val ):
                        report_id=request.POST.get("report_id")
                        r=Report.objects.get(id=report_id)

                        cust=Customer.objects.get(id=r.customer.id)
                        file_suffix=custom_slugify(str(cust.name))

                        cs_files={'m1':cs_m1_url,
                                  'm2':cs_m2_url,
                                  'm3':cs_m3_url,
                                  'cur':cs_m0_url}

                        os_files={'m1':os_m1_url,
                                  'm2':os_m2_url,
                                  'm3':os_m3_url,
                                  'cur':os_m0_url}

                        #Async Task- Report Generator
                        print("cs files")
                        print(cs_files)
                        print(os_files)
                        print(ca_pur_url)
                        dates=request.POST.get('dates').split(',')
                        months=[]
                        years=[]
                        for ind in range(len(dates)):

                            dat=dates[ind].split()
                            months.append(dat[0])
                            years.append(dat[1])

                        output=generate_con_analysis.delay(cs_files,os_files,ca_pur_url,months,years,file_suffix,request.user.id,cust.id,request.POST.get("report_id"))

                        response = JsonResponse({'status': 'Valid', 'message': 'File processed','fileurl':'/get_file/','taskid':output.task_id})
                        response.status_code = 200
                        return response

                    else:
                        response = JsonResponse({'status': 'Error', 'message': 'Invalid File types'})
                        response.status_code = 400
                        return response

                elif(request.POST.get("report_type")=="PUR_EFF"):
                    if("pe_input_file" not in request.FILES ):
                        response = JsonResponse({'status': 'Valid', 'message': 'Incomplete inputs'})
                        response.status_code = 400
                        return response
                    else:
                        pe_inputfile = request.FILES['pe_input_file']
                        fs = FileSystemStorage(location='media/uploads')

                        pe_filename = fs.save(custom_slugify(pe_inputfile.name), pe_inputfile)
                        pe_url=fs.url(pe_filename)


                        #Absolute path
                        pe_url=settings.BASE_DIR+"/media/uploads/"+pe_url

                        mimetypes=('application/vnd.ms-excel','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                        if(validate_file(pe_url,mimetypes)):
                            report_id=request.POST.get("report_id")
                            r=Report.objects.get(id=report_id)

                            cust=Customer.objects.get(id=r.customer.id)
                            file_suffix=custom_slugify(str(cust.name))

                            #Async Task- Report Generator
                            output=generate_pe.delay(pe_url,file_suffix,request.user.id,cust.id,request.POST.get("report_id"))

                            response = JsonResponse({'status': 'Valid', 'message': 'File processing','fileurl':'/get_file/','taskid':output.task_id})
                            response.status_code = 200
                            return response

                        else:
                            response = JsonResponse({'status': 'Error', 'message': 'Invalid File types'})
                            response.status_code = 400
                            return response


        else:
            response = JsonResponse({'status': 'Invalid', 'message': 'Not allowed for this user. Contact your administrator'})
            response.status_code = 400
            return response


@login_required(login_url='/accounts/login')
def update_report(request):
    print("update report")
    if request.method == 'POST':
        if request.user.groups.filter(name='Accountant').exists():
            if("reportid" not in request.POST or "reportstatus" not in request.POST):
                response = JsonResponse({'status': 'Invalid', 'message': 'Invalid Form. Missing parameters'})
                response.status_code = 400
                return response
            else:
                reportid=request.POST.get("reportid")
                value=int(request.POST.get("reportstatus"))
                if(value==0):
                    r=Report.objects.get(id=reportid)
                    r.status="Review"
                    d = datetime.now().astimezone(timezone('Asia/Kolkata'))
                    mon=d.strftime("%b")
                    event={
                        "modifierid" : request.user.id,
                        "modifiername" : request.user.username,
                        "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                        "month" : mon,
                        "eventtype" : "Lifecycle",
                        "eventvalue" : "Reverted",
                        "message" : "Report has been reverted back to the accountant",
                        "status" : r.status
                    }
                    r.activity.append(event)
                    r.save()
                    man_email=r.owner.email
                    send_mail('Report Modified', 'Hi, A modification has been made to the report. Please login to your firstcourse workflow to check it.', 'chaitanya.nandigama@firstcourse.in', [man_email], fail_silently=False)
                    response = JsonResponse({'status': 'Valid', 'message': 'Report has been reverted back to the accountant and email has been sent'})
                    response.status_code = 200
                    return response
                elif(value==1):
                    r=Report.objects.get(id=reportid)
                    r.status="QC"
                    d = datetime.now().astimezone(timezone('Asia/Kolkata'))
                    mon=d.strftime("%b")
                    event={
                        "modifierid" : request.user.id,
                        "modifiername" : request.user.username,
                        "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                        "month" : mon,
                        "eventtype" : "Lifecycle",
                        "eventvalue" : "Updated",
                        "message" : "Report has been generated and sent for QC and notified",
                        "status" : r.status
                    }
                    r.activity.append(event)
                    r.save()
                    man_email=r.qc.email
                    send_mail('Report Created', 'Hi, A new modification to the Report has been initiated. Please login to your firstcourse workflow to check it.', 'chaitanya.nandigama@firstcourse.in', [man_email], fail_silently=False)
                    response = JsonResponse({'status': 'Valid', 'message': event["message"]})
                    response.status_code = 200
                    return response

        elif request.user.groups.filter(name='TeamLead').exists():
            if("reportid" not in request.POST or "reportstatus" not in request.POST):
                response = JsonResponse({'status': 'Invalid', 'message': 'Invalid Form. Missing parameters'})
                response.status_code = 400
                return response
            else:
                reportid=request.POST.get("reportid")
                value=int(request.POST.get("reportstatus"))
                if(value==0):
                    r=Report.objects.get(id=reportid)
                    r.status="Review"
                    d = datetime.now().astimezone(timezone('Asia/Kolkata'))
                    mon=d.strftime("%b")
                    event={
                        "modifierid" : request.user.id,
                        "modifiername" : request.user.username,
                        "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                        "month" : mon,
                        "eventtype" : "Lifecycle",
                        "eventvalue" : "Reverted",
                        "message" : "Report has been reverted back to the Accountant",
                        "status" : r.status
                    }
                    r.activity.append(event)
                    r.save()
                    man_email=r.owner.email
                    send_mail('Report Modified', 'Hi, A modification has been made to the report. Please login to your firstcourse workflow to check it.', 'chaitanya.nandigama@firstcourse.in', [man_email], fail_silently=False)
                    response = JsonResponse({'status': 'Valid', 'message': event["message"]})
                    response.status_code = 200
                    return response
                elif(value==1):
                    r=Report.objects.get(id=reportid)
                    r.status="QC"
                    d = datetime.now().astimezone(timezone('Asia/Kolkata'))
                    mon=d.strftime("%b")
                    event={
                        "modifierid" : request.user.id,
                        "modifiername" : request.user.username,
                        "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                        "month" : mon,
                        "eventtype" : "Lifecycle",
                        "eventvalue" : "Updated",
                        "message" : "Report has been generated and sent for Quality control",
                        "status" : r.status
                    }
                    r.activity.append(event)
                    r.save()
                    man_email=r.qc.email
                    send_mail('Report Created', 'Hi, A new request to quality control the Report has been initiated. Please login to your firstcourse workflow to check it.', 'chaitanya.nandigama@firstcourse.in', [man_email], fail_silently=False)
                    response = JsonResponse({'status': 'Valid', 'message': event["message"]})
                    response.status_code = 200
                    return response
        elif request.user.groups.filter(name='QC').exists():
            if("reportid" not in request.POST or "reportstatus" not in request.POST):
                response = JsonResponse({'status': 'Invalid', 'message': 'Invalid Form. Missing parameters'})
                response.status_code = 400
                return response
            else:
                reportid=request.POST.get("reportid")
                value=int(request.POST.get("reportstatus"))
                print("value is ",value)
                if(value==0):
                    r=Report.objects.get(id=reportid)
                    r.status="Review"
                    d = datetime.now().astimezone(timezone('Asia/Kolkata'))
                    mon=d.strftime("%b")
                    event={
                        "modifierid" : request.user.id,
                        "modifiername" : request.user.username,
                        "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                        "month" : mon,
                        "eventtype" : "Lifecycle",
                        "eventvalue" : "Reverted",
                        "message" : "Report has been reverted back to the Accountant",
                        "status" : r.status
                    }
                    r.activity.append(event)
                    r.save()
                    man_email=r.owner.email
                    print("Email is ",man_email)
                    send_mail('Report Modified', 'Hi, A modification has been made to your QC report. Please login to your firstcourse workflow to check it.', 'chaitanya.nandigama@firstcourse.in', [man_email], fail_silently=False)
                    response = JsonResponse({'status': 'Valid', 'message': event["message"]})
                    response.status_code = 200
                    return response
                elif(value==1):
                    r=Report.objects.get(id=reportid)
                    r.status="CRM"
                    d = datetime.now().astimezone(timezone('Asia/Kolkata'))
                    mon=d.strftime("%b")
                    event={
                        "modifierid" : request.user.id,
                        "modifiername" : request.user.username,
                        "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                        "month" : mon,
                        "eventtype" : "Lifecycle",
                        "eventvalue" : "Updated",
                        "message" : "Report has been forwarded to the CRM for approval",
                        "status" : r.status
                    }
                    r.activity.append(event)
                    r.save()
                    man_email=r.crm.email
                    print(r.crm.email)
                    send_mail('Report Created', 'Hi, A new request has been created to publish the Report. Please login to your firstcourse workflow to check it.', 'chaitanya.nandigama@firstcourse.in', [man_email], fail_silently=False)
                    response = JsonResponse({'status': 'Valid', 'message': event["message"]})
                    response.status_code = 200
                    return response
        elif request.user.groups.filter(name='CRM').exists():
            print("crm")
            if("reportid" not in request.POST or "reportstatus" not in request.POST):
                response = JsonResponse({'status': 'Invalid', 'message': 'Invalid Form. Missing parameters'})
                response.status_code = 400
                return response
            else:
                reportid=request.POST.get("reportid")
                value=int(request.POST.get("reportstatus"))
                print(value)
                if(value==0):
                    r=Report.objects.get(id=reportid)
                    r.status="Review"
                    d = datetime.now().astimezone(timezone('Asia/Kolkata'))
                    mon=d.strftime("%b")
                    event={
                        "modifierid" : request.user.id,
                        "modifiername" : request.user.username,
                        "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                        "month" : mon,
                        "eventtype" : "Lifecycle",
                        "eventvalue" : "Reverted",
                        "message" : "Report has been sent back to Accountant",
                        "status" : r.status
                    }
                    r.activity.append(event)
                    r.save()
                    man_email=r.owner.email
                    print("before mail")
                    send_mail('CRM reported issues in the report', 'Hi, There seems to be a problem with your quality control check. Pleae login to the email to check it.', 'chaitanya.nandigama@firstcourse.in', [man_email], fail_silently=False)
                    response = JsonResponse({'status': 'Valid', 'message': event["message"]})
                    response.status_code = 200
                    print(response)
                    return response
                elif(value==1):
                    r=Report.objects.get(id=reportid)
                   # r.status="Published"
                    d = datetime.now().astimezone(timezone('Asia/Kolkata'))
                    mon=d.strftime("%b")
                    event={
                        "modifierid" : request.user.id,
                        "modifiername" : request.user.username,
                        "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                        "month" : mon,
                        "eventtype" : "Lifecycle",
                        "eventvalue" : "Published",
                        "message" : "Report has been published",
                        "status" : r.status
                    }
                    r.activity.append(event)
                    r.save()
                    man_email=r.owner.email
                    print("before mail")
                    send_mail('Report Published', 'Hi, the report is published ', 'chaitanya.nandigama@firstcourse.in', [man_email], fail_silently=False)
                    response = JsonResponse({'status': 'Valid', 'message': event["message"]})
                    response.status_code = 200
                    print(response)

                    # API call to post report data to arango db
                    print("report data post to arango db start")
                    client = requests.session()
                    headers = {'Accept': 'application/json','accept': 'application/json'}
                    apiUrl = settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.CSRFTOKEN_API_URL
                    print(apiUrl)
                    apiReq = client.get(apiUrl, headers=headers)
                    api_status_code = apiReq.status_code
                    if api_status_code != 200:
                        response = ''
                        return response, api_status_code
                    else:
                        apiRes = json.loads(apiReq.text)
                        csrfToken=apiRes['csrfToken']
                        print(csrfToken)
                        headers['x-csrf-token']=csrfToken
                        print(headers)
                        reportEntity=''
                        print(r.brand)
                        print(r.outlet)
                        print(r.legalentity)
                        print(r.customer)
                        if(r.brand):
                            reportEntity=r.brand
                        elif(r.outlet):
                            reportEntity = r.outlet
                        elif(r.legalentity):
                            reportEntity = r.legalentity
                        else:
                            reportEntity = r.customer
                        d = datetime.now().astimezone(timezone('Asia/Kolkata'))
                        apiBody={
                            'entity':reportEntity,
                            'day':'1',
                            'year':r.year,
                            'month':r.month,
                            'report_type':r.report_type,
                            'version':1,
                            'created_at':d.strftime("%m/%d/%Y, %H:%M:%S"),
                            'modified_at':d.strftime("%m/%d/%Y, %H:%M:%S"),
                            'result':json.dumps(r.results)
                        }
                        print(apiBody)
                        apiUrl=settings.EXPRESS_API_HOST+":"+settings.EXPRESS_API_PORT+settings.SAVEREPORT_API_URL
                        print(apiUrl)
                        apiReq = client.post(apiUrl,data=apiBody, headers=headers)
                        api_status_code = apiReq.status_code
                        print("api response")
                        if api_status_code != 200:
                            response = ''
                            return response, api_status_code
                        else:
                            apiRes = json.loads(apiReq.text)
                            print(apiRes)

                            response = JsonResponse({'status': 'Valid', 'message': event["message"]})
                            response.status_code = 200
                    return response
        else:
            response = JsonResponse({'status': 'Invalid', 'message': 'Not allowed for this user. Contact your administrator'})
            response.status_code = 400
            return response
    else:
        response = JsonResponse({'status': 'Invalid', 'message': 'Not Allowed'})
        response.status_code = 400
        return response
        print("reponse : ")
        print(response)
    return redirect('dashboard')


@api_view(['GET'])
@login_required
def report_list(request,format=None):
    """
    List all code snippets, or create a new snippet.
    """
    if request.method == 'GET':
        print("Record list called")
        report_type=[]
        customer=[]
        status='all'
        month=''
        year=''
        if('rtype[]' in request.GET):
            report_type=request.GET.getlist('rtype[]')
        elif('rtype' in request.GET):
            report_type=[request.GET.get('rtype')]
        if('customer[]' in request.GET):
            customer=request.GET.getlist('customer[]')
        elif('customer' in request.GET):
            customer=[request.GET.get('customer')]
        if('status[]' in request.GET):
            status=request.GET.getlist('status[]')
        if('month' in request.GET):
            date=request.GET.get('month')
            splitdate=date.split()
            month=int(splitdate[0])
            year=int(splitdate[1])

        number_per_page=5
        if('no_per_page' in request.GET):
            number_per_page=request.GET.get('no_per_page')
        page=1
        if('page' in request.GET):
            page=request.GET.get('page')
            page=int(page)
            page+=1
        number=0
        values={}
        records=[]
        emp=Employee.objects.get(user=request.user)
        if request.user.groups.filter(name='TeamLead').exists():
            #Team lead
            print("Hey its team lead")
            if(month!=''):
                if(status!='all'):
                    if(report_type==[]):
                        if(customer==[]):
                            records=Report.objects.filter(tl=request.user).filter(status__in=status).filter(month=month).filter(year=year).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(tl=request.user).filter(customer__in=customer).filter(status__in=status).filter(month=month).filter(year=year).order_by("-generated_at")
                    else:
                        if(customer==[]):
                            records=Report.objects.filter(tl=request.user).filter(report_type__in=report_type).filter(status__in=status).filter(month=month).filter(year=year).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(tl=request.user).filter(report_type__in=report_type).filter(status__in=status).filter(customer__in=customer).filter(month=month).filter(year=year).order_by("-generated_at")
                else:
                    if(report_type==[]):
                        if(customer==[]):
                            records=Report.objects.filter(tl=request.user).filter(month=month).filter(year=year).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(tl=request.user).filter(customer__in=customer).filter(month=month).filter(year=year).order_by("-generated_at")
                    else:
                        if(customer==[]):
                            records=Report.objects.filter(tl=request.user).filter(report_type__in=report_type).filter(month=month).filter(year=year).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(tl=request.user).filter(report_type__in=report_type).filter(customer__in=customer).filter(month=month).filter(year=year).order_by("-generated_at")
            else:
                if(status!='all'):
                    if(report_type==[]):
                        if(customer==[]):
                            records=Report.objects.filter(tl=request.user).filter(status__in=status).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(tl=request.user).filter(customer__in=customer).filter(status__in=status).order_by("-generated_at")
                    else:
                        if(customer==[]):
                            records=Report.objects.filter(tl=request.user).filter(report_type__in=report_type).filter(status__in=status).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(tl=request.user).filter(report_type__in=report_type).filter(status__in=status).filter(customer__in=customer).order_by("-generated_at")
                else:
                    if(report_type==[]):
                        if(customer==[]):
                            records=Report.objects.filter(tl=request.user).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(tl=request.user).filter(customer__in=customer).order_by("-generated_at")
                    else:
                        if(customer==[]):
                            records=Report.objects.filter(tl=request.user).filter(report_type__in=report_type).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(tl=request.user).filter(report_type__in=report_type).filter(customer__in=customer).order_by("-generated_at")

        if request.user.groups.filter(name='QC').exists():
            #Team lead
            print("Hey its QC")
            if(month!=''):
                if(status!='all'):
                    if(report_type==[]):
                        if(customer==[]):
                            records=Report.objects.filter(qc=request.user).filter(status__in=status).filter(month=month).filter(year=year).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(qc=request.user).filter(customer__in=customer).filter(status__in=status).filter(month=month).filter(year=year).order_by("-generated_at")
                    else:
                        if(customer==[]):
                            records=Report.objects.filter(qc=request.user).filter(report_type__in=report_type).filter(status__in=status).filter(month=month).filter(year=year).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(qc=request.user).filter(report_type__in=report_type).filter(status__in=status).filter(customer__in=customer).filter(month=month).filter(year=year).order_by("-generated_at")
                else:
                    if(report_type==[]):
                        if(customer==[]):
                            records=Report.objects.filter(qc=request.user).filter(month=month).filter(year=year).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(qc=request.user).filter(customer__in=customer).filter(month=month).filter(year=year).order_by("-generated_at")
                    else:
                        if(customer==[]):
                            records=Report.objects.filter(qc=request.user).filter(report_type__in=report_type).filter(month=month).filter(year=year).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(qc=request.user).filter(report_type__in=report_type).filter(customer__in=customer).filter(month=month).filter(year=year).order_by("-generated_at")
            else:
                if(status!='all'):
                    if(report_type==[]):
                        if(customer==[]):
                            records=Report.objects.filter(qc=request.user).filter(status__in=status).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(qc=request.user).filter(customer__in=customer).filter(status__in=status).order_by("-generated_at")
                    else:
                        if(customer==[]):
                            records=Report.objects.filter(qc=request.user).filter(report_type__in=report_type).filter(status__in=status).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(qc=request.user).filter(report_type__in=report_type).filter(status__in=status).filter(customer__in=customer).order_by("-generated_at")
                else:
                    if(report_type==[]):
                        if(customer==[]):
                            records=Report.objects.filter(qc=request.user).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(qc=request.user).filter(customer__in=customer).order_by("-generated_at")
                    else:
                        if(customer==[]):
                            records=Report.objects.filter(qc=request.user).filter(report_type__in=report_type).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(qc=request.user).filter(report_type__in=report_type).filter(customer__in=customer).order_by("-generated_at")

        if request.user.groups.filter(name='CRM').exists():
            #Team lead
            if(month!=''):
                if(status!='all'):
                    if(report_type==[]):
                        if(customer==[]):
                            records=Report.objects.filter(crm=request.user).filter(status__in=status).filter(month=month).filter(year=year).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(crm=request.user).filter(customer__in=customer).filter(status__in=status).filter(month=month).filter(year=year).order_by("-generated_at")
                    else:
                        if(customer==[]):
                            records=Report.objects.filter(crm=request.user).filter(report_type__in=report_type).filter(status__in=status).filter(month=month).filter(year=year).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(crm=request.user).filter(report_type__in=report_type).filter(status__in=status).filter(customer__in=customer).filter(month=month).filter(year=year).order_by("-generated_at")
                else:
                    if(report_type==[]):
                        if(customer==[]):
                            records=Report.objects.filter(crm=request.user).filter(month=month).filter(year=year).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(crm=request.user).filter(customer__in=customer).filter(month=month).filter(year=year).order_by("-generated_at")
                    else:
                        if(customer==[]):
                            records=Report.objects.filter(crm=request.user).filter(report_type__in=report_type).filter(month=month).filter(year=year).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(crm=request.user).filter(report_type__in=report_type).filter(customer__in=customer).filter(month=month).filter(year=year).order_by("-generated_at")
            else:
                if(status!='all'):
                    if(report_type==[]):
                        if(customer==[]):
                            records=Report.objects.filter(crm=request.user).filter(status__in=status).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(crm=request.user).filter(customer__in=customer).filter(status__in=status).order_by("-generated_at")
                    else:
                        if(customer==[]):
                            records=Report.objects.filter(crm=request.user).filter(report_type__in=report_type).filter(status__in=status).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(crm=request.user).filter(report_type__in=report_type).filter(status__in=status).filter(customer__in=customer).order_by("-generated_at")
                else:
                    if(report_type==[]):
                        if(customer==[]):
                            records=Report.objects.filter(crm=request.user).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(crm=request.user).filter(customer__in=customer).order_by("-generated_at")
                    else:
                        if(customer==[]):
                            records=Report.objects.filter(crm=request.user).filter(report_type__in=report_type).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(crm=request.user).filter(report_type__in=report_type).filter(customer__in=customer).order_by("-generated_at")

        if request.user.groups.filter(name='Accountant').exists():
            number=Report.objects.filter(owner=request.user).count()
            if(month!=''):
                if(status!='all'):
                    print("Hey its not all status")
                    if(report_type==[]):
                        if(customer==[]):
                            records=Report.objects.filter(owner=request.user).filter(status__in=status).filter(month=month).filter(year=year).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(owner=request.user).filter(customer__in=customer).filter(status__in=status).filter(month=month).filter(year=year).order_by("-generated_at")
                    else:
                        print("Hey its something else")
                        if(customer==[]):
                            records=Report.objects.filter(owner=request.user).filter(report_type__in=report_type).filter(status__in=status).filter(month=month).filter(year=year).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(owner=request.user).filter(report_type__in=report_type).filter(status__in=status).filter(customer__in=customer).filter(month=month).filter(year=year).order_by("-generated_at")
                else:
                    if(report_type==[]):
                        if(customer==[]):
                            records=Report.objects.filter(owner=request.user).filter(month=month).filter(year=year).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(owner=request.user).filter(customer__in=customer).filter(month=month).filter(year=year).order_by("-generated_at")
                    else:
                        if(customer==[]):
                            records=Report.objects.filter(owner=request.user).filter(report_type__in=report_type).filter(month=month).filter(year=year).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(owner=request.user).filter(report_type__in=report_type).filter(customer__in=customer).filter(month=month).filter(year=year).order_by("-generated_at")
            else:
                if(status!='all'):

                    if(report_type==[]):
                        if(customer==[]):
                            records=Report.objects.filter(owner=request.user).filter(status__in=status).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(owner=request.user).filter(customer__in=customer).filter(status__in=status).order_by("-generated_at")
                    else:
                        if(customer==[]):
                            records=Report.objects.filter(owner=request.user).filter(report_type__in=report_type).filter(status__in=status).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(owner=request.user).filter(report_type__in=report_type).filter(status__in=status).filter(customer__in=customer).order_by("-generated_at")
                else:
                    if(report_type==[]):
                        if(customer==[]):
                            records=Report.objects.filter(owner=request.user).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(owner=request.user).filter(customer__in=customer).order_by("-generated_at")
                    else:
                        if(customer==[]):
                            records=Report.objects.filter(owner=request.user).filter(report_type__in=report_type).order_by("-generated_at")
                        else:
                            records=Report.objects.filter(owner=request.user).filter(report_type__in=report_type).filter(customer__in=customer).order_by("-generated_at")



        number=len(records)
        print(number)
        if(number>0):
            print("Hey number>0")
            pages=Paginator(records,number_per_page)
            records=pages.page(page).object_list
            serializer = ReportSerializer(records, many=True)

            values={"records":list(serializer.data)}


        newdict = {'count':number}
        values["count"]=number
        # print(values)
        return Response(values)

    elif request.method == 'POST':
        message="Not Allowed"
        return JsonResponse(message, status=400)


@api_view(['GET'])
@login_required
def task_list(request,status,format=None):
    """
    List all code snippets, or create a new snippet.
    """
    if request.method == 'GET':
        # print("Record list called")
        number=0
        values={}
        records=[]
        try:
            emp=Employee.objects.get(user=request.user)
        except:
            emp=None
        if request.user.groups.filter(name='Accountant').exists():
            if(status!="all"):
                records=Report.objects.filter(owner=request.user).filter(status=status).order_by("-generated_at")
            else:
                records=Report.objects.filter(owner=request.user).order_by("-generated_at")
        elif request.user.groups.filter(name='TeamLead').exists():
            if(status!="all"):
                records=Report.objects.filter(tl=request.user).filter(status=status).order_by("-generated_at")
            else:
                records=Report.objects.filter(tl=request.user).order_by("-generated_at")


        elif request.user.groups.filter(name='QC').exists():
            if(status!="all"):
                records=Report.objects.filter(qc=request.user).filter(status=status).order_by("-generated_at")
            else:
                records=Report.objects.filter(qc=request.user).order_by("-generated_at")


        elif request.user.groups.filter(name='CRM').exists():
            if(status!="all"):
                records=Report.objects.filter(crm=request.user).filter(status=status).order_by("-generated_at")
            else:
                records=Report.objects.filter(crm=request.user).order_by("-generated_at")

        number=len(records)
        print(number)
        if(number>0):
            serializer = ReportSerializer(records, many=True)

            values={"tasks":list(serializer.data)}


        newdict = {'count':number}
        values["count"]=number
        # print(values)
        return Response(values)

    elif request.method == 'POST':
        message="Not Allowed"
        return JsonResponse(message, status=400)


@api_view(['POST'])
@login_required
def post_entity(request):
    if(request.method=='POST'):
        if(request.POST.get("entity")=='comments'):
            if(request.POST.get("action")=="insert"):
                reportid=int(request.POST.get("reportid"))
                rr=Report.objects.get(pk=reportid)
                if(rr.report_type=="P_L"):

                    description=request.POST.get("comment_description")
                    category=request.POST.get("comment_category")
                    print("Category is ",category)
                    type=request.POST.get("comment_type")
                    remarks=request.POST.get("comment_remarks")
                    d = datetime.now().astimezone(timezone('Asia/Kolkata'))
                    comments={"comment_author":request.user.username,"comment_description":description,"comment_type":type,"comment_remarks":remarks,"comment_category":category,"comment_datetime":d.strftime("%m/%d/%Y, %H:%M:%S")}
                    print(comments)
                    rr=Report.objects.get(pk=reportid)
                    if(rr.comments==None):
                        rr.comments={"values":[comments]}
                    else:
                        rr.comments['values'].append(comments)
                else:
                    remarks=request.POST.get("comment_remarks")
                    d = datetime.now().astimezone(timezone('Asia/Kolkata'))
                    comments={"comment_author":request.user.username,"comment_remarks":remarks,"comment_datetime":d.strftime("%m/%d/%Y, %H:%M:%S")}
                    rr=Report.objects.get(pk=reportid)
                    if(rr.comments==None):
                        rr.comments={"values":[comments]}
                    else:
                        rr.comments['values'].append(comments)
                mon=d.strftime("%b")
                event={
                    "modifierid" : request.user.id,
                    "modifiername" : request.user.username,
                    "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                    "month" : mon,
                    "eventtype" : "Comment",
                    "eventvalue" : comments,
                    "message" : "A comment has been added",
                    "status" : rr.status
                }
                rr.activity.append(event)
                rr.save()
                rrc_serializer=ReportSerializer(rr)
                options={
                    "status":200,
                    "message":"Successfully added comments",
                    "object":rrc_serializer.data
                }
                return JsonResponse(options)
            elif(request.POST.get("action")=="modify"):
                reportid=int(request.POST.get("reportid"))
                commentid=int(request.POST.get("commentid"))
                description=request.POST.get("comment_description")
                category=request.POST.get("comment_category")
                type=request.POST.get("comment_type")
                remarks=request.POST.get("comment_remarks")
                d = datetime.now().astimezone(timezone('Asia/Kolkata'))
                comments={"comment_author":request.user.username,"comment_description":description,"comment_type":type,"comment_remarks":remarks,"comment_category":category,"comment_datetime":d.strftime("%m/%d/%Y, %H:%M:%S")}
                rr=Report.objects.get(pk=reportid)
                if(rr.comments==None):
                    rr.comments={"values":[comments]}
                else:
                    rr.comments['values'][commentid]=comments

                mon=d.strftime("%b")
                event={
                    "modifierid" : request.user.id,
                    "modifiername" : request.user.username,
                    "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                    "month" : mon,
                    "eventtype" : "Comment",
                    "eventvalue" : comments,
                    "message" : "A comment has been added",
                    "status" : rr.status
                }
                rr.activity.append(event)
                rr.save()
                rrc_serializer=ReportSerializer(rr)
                options={
                    "status":200,
                    "message":"Successfully modify comments",
                    "object":rrc_serializer.data
                }
                return JsonResponse(options)

        if(request.POST.get("entity")=='anomalies'):

            reportid=int(request.POST.get("reportid"))
            description=request.POST.get("anomaly_description")
            comment=request.POST.get("anomaly_comment")
            criticality=request.POST.get("anomaly_criticality")
            rr=Report.objects.get(pk=reportid)



            d = datetime.now().astimezone(timezone('Asia/Kolkata'))
            # print(d.strftime("%m/%d/%Y, %H:%M:%S"))
            anomaly={"anomaly_author":request.user.username,"anomaly_description":description,"anomaly_comment":comment,"anomaly_criticality":criticality,"anomaly_datetime":d.strftime("%m/%d/%Y, %H:%M:%S")}
            if(rr.anomalies == None):
                rr.anomalies={"values":[anomaly]}
            else:
                rr.anomalies['values'].append(anomaly)

            mon=d.strftime("%b")
            event={
                "modifierid" : request.user.id,
                "modifiername" : request.user.username,
                "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                "month" : mon,
                "eventtype" : "Anomaly",
                "eventvalue" : anomaly,
                "message" : "An anomaly has been added",
                "status" : rr.status
            }
            rr.activity.append(event)
            rr.save()
            rrf_serializer=ReportSerializer(rr)
            options={
                "status":200,
                "message":"Successfully added flag",
                "object":rrf_serializer.data
            }
            return JsonResponse(options)

        if(request.POST.get("entity")=='checklists'):
            print("Hey it called checklists post")
            reportid=int(request.POST.get("reportid"))
            checklist=request.POST.get("checklists")
            rr=Report.objects.get(pk=reportid)
            checklist=json.loads(checklist)
            # print(json.loads(checklist))
            if(rr.checklists == None):
                rr.checklists=checklist
            else:
                rr.checklists=checklist
            d = datetime.now().astimezone(timezone('Asia/Kolkata'))
            mon=d.strftime("%b")
            event={
                "modifierid" : request.user.id,
                "modifiername" : request.user.username,
                "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                "month" : mon,
                "eventtype" : "Checklist",
                "eventvalue" : "Checklist modified",
                "message" : "Checklist has been added",
                "status" : rr.status
            }
            rr.activity.append(event)
            rr.save()
            rrf_serializer=ReportSerializer(rr)
            options={
                "status":200,
                "message":"Successfully added checklist",
                "object":rrf_serializer.data
            }
            return JsonResponse(options)
    else:
        options={
            "status":400
        }
        return JsonResponse(options)


@login_required
def delete_entity(request):
    if(request.method=='POST'):
        if(request.POST.get("entity")=='comments'):
            reportid=request.POST.get("reportid")
            commentid=request.POST.get("commentid")
            print(reportid)
            r=Report.objects.get(pk=reportid)
            if not request.user.groups.filter(name='Customer').exists():
                comments=r.comments
                comments=json.dumps(comments)
                comments=json.loads(comments)
                del comments["values"][int(commentid)]
                # print(comments)
                r.comments=comments
                r.save()
                options={
                    "status":200,
                    "message":"Successfully deleted comment",
                }
                return JsonResponse(options)
            else:
                options={
                    "status":400,
                    "message":"Not Allowed",
                }
                return JsonResponse(options)


@api_view(['GET'])
@login_required
def choices_list(request,format=None):
    if(request.method=='GET'):
        report_types=[]
        count=1
        for i in REPORT_TYPE:
            report_types.append([i[0],i[1]])
            count+=1
        status_types=[]
        count=1
        for j in STATUS_TYPE:
            status_types.append({"id":j[0],"text":j[1]})
        options={
            "report_type":report_types,
            "status_type":status_types,
            "status":200
        }
        return JsonResponse(options)


@api_view(['GET'])
@login_required
def get_anomalies(request,id):
    if(request.method=='GET'):
        records=Report.objects.get(pk=id)
        anomalies=records.anomalies
        options={
            "anomalies":anomalies,
            "status":200
        }
        return JsonResponse(options)


@api_view(['GET'])
@login_required
def get_comments(request,id):
    if(request.method=='GET'):
        records=Report.objects.get(pk=id)
        comments=records.comments
        options={
            "comments":comments,
            "status":200
        }
        return JsonResponse(options)


@api_view(['GET'])
@login_required
def get_checklists(request,id):
    if(request.method=='GET'):
        records=Report.objects.get(pk=id)
        checklists=records.checklists
        options={
            "checklists":checklists,
            "status":200
        }
        return JsonResponse(options)


@api_view(['GET'])
@login_required
def get_activities(request,id):
    if(request.method=='GET'):
        records=Report.objects.get(pk=id)
        activities=records.activity
        options={
            "activity":activities,
            "status":200
        }
        return JsonResponse(options)


@api_view(['GET'])
@login_required
def get_report(request,id):
    if(request.method=='GET'):
        records=Report.objects.get(pk=id)
        serializer = ReportSerializer(records)
        options={
            "report":serializer.data,
            "status":200
        }
        return JsonResponse(options)

@api_view(['GET'])
@login_required
def get_payables(request,day,month,year):
    if(request.method=='GET'):
        cust=Customer.objects.get(user_account=request.user)
        payable=Payables.objects.filter(customer=cust,day=day,month=month,year=year)
        options={
            "report":payable.data,
            "status":200
        }
        return JsonResponse(options)

@api_view(['GET'])
@login_required
def get_payables_latest(request):
    if(request.method=='GET'):
        cust=Customer.objects.get(user_account=request.user)
        payable=Payables.objects.filter(customer=cust).order_by('-generated_at')[0]
        pay_ser=PayableSerializer(payable)
        print(payable)
        options={
            "result":pay_ser.data,
            "status":200
        }
        return JsonResponse(options)

@api_view(['GET'])
@login_required
def get_receivables(request,day,month,year):
    if(request.method=='GET'):
        cust=Customer.objects.get(user_account=request.user)
        receivable=Receivables.objects.filter(customer=cust,day=day,month=month,year=year)
        rec_ser=ReceivableSerializer(receivable)
        options={
            "report":rec_ser.data,
            "status":200
        }
        return JsonResponse(options)


@api_view(['GET'])
@login_required
def get_receivables_latest(request):
    if(request.method=='GET'):
        cust=Customer.objects.get(user_account=request.user)
        receivable=Receivables.objects.filter(customer=cust).order_by('-generated_at')[0]
        rec_ser=ReceivableSerializer(receivable)
        options={
            "result":rec_ser.data,
            "status":200
        }
        return JsonResponse(options)

@api_view(['GET'])
@login_required
def get_results(request,scope):
    if(request.method=='GET'):
        print("scope : "+scope)
        if(scope == "latest"):
            month=request.GET.get("query_month")
            year = request.GET.get("query_year")
            report_type=request.GET.get("report_type")
            cust=Customer.objects.get(user_account=request.user)
            records=Report.objects.filter(customer=cust).filter(status="Published").order_by("-generated_at").filter(report_type=report_type).first()
            print(records)
            if records:
                # records=records[0]
                results=ResultSerializer(records)

                options={
                    "result":results.data,
                    "status":200
                }
                return JsonResponse(options)
            else:
                options={
                    "result":'empty',
                    "status":200
                }
                return JsonResponse(options)
        elif(scope == "all"):
            cust=Customer.objects.get(user_account=request.user)
            records=Report.objects.filter(customer=cust).filter(status="Published").order_by("-generated_at")
            results=ResultSerializer(records,many=True)
            options={
                "result":results.data,
                "status":200
            }
            return JsonResponse(options)
        elif(scope == "specific"):
            month=request.GET.get("query_month")
            year = request.GET.get("query_year")
            report_type=request.GET.get("report_type")

            cust=Customer.objects.get(user_account=request.user)
            records=Report.objects.filter(customer=cust).filter(month=month).filter(status="Published").filter(year=year).filter(report_type=report_type).first()
            if records:
                results=ResultSerializer(records)

                options={
                    "result":results.data,
                    "status":200
                }
                print("records if result: ", results.data)
                return JsonResponse(options)
            else:
                options={
                    "result":'empty',
                    "status":200
                }
                print("records else result: ")
                return JsonResponse(options)


@api_view(['GET'])
@login_required
def get_insights(request):
    if('type' not in request.GET):
        options = {
            "result": 'empty',
            "status": 200
        }
        return JsonResponse(options)
    else:
        type=request.GET.get("type")
        if(type=="type"):
            if('cat' not in request.GET):
                insightcat=InsightsType.objects.all()
                incat=InsightTypeSerializer(insightcat,many=True)
                print(incat.data)
                return Response(incat.data)
            else:
                cat_name=request.GET.get('cat')
                insightcat=InsightsType.objects.filter(incategory__name=cat_name)
                incat=InsightTypeSerializer(insightcat,many=True)
                print(incat.data)
                return Response(incat.data)
        if(type=="category"):
            insightcat=InsightCategory.objects.all()
            incat=InsightCategorySerializer(insightcat,many=True)
            print(incat.data)
            return Response(incat.data)
        if(type=="notes"):
            if ('cat' in request.GET and 'intype' not in request.GET):
                cat_name = request.GET.get('cat')
                insightnotes = InsightsNotes.objects.filter(category__name=cat_name)
                innotes = InsightNotesSerializer(insightnotes, many=True)
                return Response(innotes.data)
            if ('cat' not in request.GET and 'intype' in request.GET):
                type_name = request.GET.get('intype')
                insightnotes = InsightsNotes.objects.filter(type__name=type_name)
                innotes = InsightNotesSerializer(insightnotes, many=True)
                return Response(innotes.data)
            if ('cat' in request.GET and 'intype' in request.GET):
                type_name = request.GET.get('intype')
                cat_name = request.GET.get('cat')
                insightnotes = InsightsNotes.objects.filter(type__name=type_name).filter(category__name=cat_name)
                innotes = InsightNotesSerializer(insightnotes, many=True)
                return Response(innotes.data)
            if ('cat' not in request.GET and 'intype' not in request.GET):
                insightnotes = InsightsNotes.objects.all
                innotes = InsightNotesSerializer(insightnotes, many=True)
                return Response(innotes.data)


@api_view(['GET'])
@login_required
def get_file(request,id,fileid,filetype):
    if(request.method=="GET"):
        if(filetype=="excel"):
            r=Report.objects.get(id=id)
            if(r.status!="Initiated"):
                links=r.excel_attachments.all()
                if(len(links)==1):
                    s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
                    url = s3.generate_presigned_url(
                        ClientMethod='get_object',
                        Params={
                            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                            'Key': settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+links[0].document_link
                        },
                        ExpiresIn=20
                    )
                    return redirect(url)
                elif(len(links)>1):

                    s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
                    url = s3.generate_presigned_url(
                        ClientMethod='get_object',
                        Params={
                            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                            'Key': settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+links[int(fileid)].document_link
                        },
                        ExpiresIn=20
                    )
                    return redirect(url)
            else:
                url=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+"assets/img/First%20Course%20Final%20Logo%20black.png"
                return redirect("https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf")

        if(filetype=="pdf"):
            r=Report.objects.get(id=id)
            if(r.status!="Initiated"):

                links=r.pdf_attachments.all()
                if(len(links)==1):
                    s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
                    url = s3.generate_presigned_url(
                        ClientMethod='get_object',
                        Params={
                            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                            'Key': settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+links[0].document_link
                        },
                        ExpiresIn=20
                    )
                    return redirect(url)
                elif(len(links)>1):

                    s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
                    url = s3.generate_presigned_url(
                        ClientMethod='get_object',
                        Params={
                            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                            'Key': settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+links[int(fileid)].document_link
                        },
                        ExpiresIn=20
                    )
                    return redirect(url)
            else:
                url=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+"assets/img/First%20Course%20Final%20Logo%20black.png"
                return redirect("https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf")
            # d = datetime.now().astimezone(timezone('Asia/Kolkata'))
            # mon=d.strftime("%b")
            # zipurl="media/downloads/"+str(request.user)+"/"+str(mon)+"/"+custom_slugify(r.customer.name)+"/"
            # pathlib.Path(zipurl).mkdir(parents=True, exist_ok=True)
            # zipurl+="/reports.zip"
            # with ZipFile(zipurl,"w") as zip:
            #     for link in links:
            #         s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
            #         url = s3.generate_presigned_url(
            #             ClientMethod='get_object',
            #             Params={
            #                 'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            #                 'Key': settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+link.document_link
            #             },
            #             ExpiresIn=20
            #         )
            #
            #         return HttpResponse(open(zipurl, 'rb'), content_type='application/zip')


@login_required(login_url='/accounts/login')
def regenerate_report(request):
    if request.method == 'POST':

        if("report_id" not in request.POST):
            response = JsonResponse({'status': 'Invalid', 'message': 'Invalid Form. Empty parameters'})
            response.status_code = 400
            return response
        else:
            reportid=request.POST.get("report_id")
            r=Report.objects.get(id=reportid)
            if(r.owner.id == request.user.id) or (r.qc.id == request.user.id) or (r.crm.id == request.user.id):
                reporttype=r.report_type
                cust=r.customer
                user=request.user
                if(reporttype == "P_L"):
                    result=r.results
                    links=r.pdf_attachments.all()
                    s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
                    for i in range(len(links)):
                        attach=links[i]
                        fileurl=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+attach.document_link
                        s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=fileurl)
                        attach.delete()
                    comments=r.comments
                    comments=json.dumps(comments)
                    comments=json.loads(comments)
                    comments["values"].sort(key=lambda content: content['comment_category'])
                    gp=groupby(comments["values"],lambda content: content['comment_category'])
                    grouped_comments=[]
                    keys=[]
                    v=[]
                    for key,g in gp:
                        types=[]
                        content=[]
                        if(key not in keys):
                            keys.append(key)
                        print(g)
                        for con in g:

                            if(con["comment_type"] not in types):
                                types.append(con["comment_type"])
                            content.append(con)

                        v={"category":key,"types":types,"values":content}

                        grouped_comments.append(v)


                    print(grouped_comments)
                    file_suffix=custom_slugify(str(cust.name))
                    jsonparams={
                        "template": { "name" : "PL-Main","recipe": "chrome-pdf" },
                        "data" : {"result":result,"comments":grouped_comments,"keys":keys},
                        "options": { "reports": { "save": "true" },"reportName": "myreport"}
                    }
                    jsrep=requests.post("http://localhost:5543/api/report",json=jsonparams,auth=('ca-reporting','fastca123@'))
                    link=jsrep.headers['Report-BlobName']
                    fileurl_pdf='jsreportapp/data/storage/'+link
                    rename_pdf_url='jsreportapp/data/storage/'+file_suffix+"_"+link
                    os.rename(fileurl_pdf,rename_pdf_url)
                    fileurl_pdf=rename_pdf_url
                    localfile=open(fileurl_pdf,"rb")
                    djangofile=File(localfile)
                    filepath=get_file_path(user.username,localfile.name)
                    fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
                    fileurl+=filepath
                    pdffile=PrivatePdfDocument(user=user,record=r,upload=djangofile,document_link=filepath)
                    pdffile.save()
                    fileurl='/get_file/'+str(r.id)+'/'
                    response = JsonResponse({'status': 'Valid', 'message': 'File processed','fileurl':'/get_file/'})
                    response.status_code = 200
                    return response
                if(reporttype == "GST"):
                    result=r.results
                    links=r.pdf_attachments.all()
                    s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
                    for i in range(len(links)):
                        attach=links[i]
                        fileurl=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+attach.document_link
                        s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=fileurl)
                        attach.delete()
                    comments=r.comments
                    file_suffix=custom_slugify(str(cust.name))
                    jsonparams={
                        "template": { "name" : "GST-Main","recipe": "chrome-pdf" },
                        "data" : {"result":result,"comments":comments},
                        "options": { "reports": { "save": "true" },"reportName": "myreport"}
                    }
                    jsrep=requests.post("http://localhost:5543/api/report",json=jsonparams,auth=('ca-reporting','fastca123@'))
                    link=jsrep.headers['Report-BlobName']
                    fileurl_pdf='jsreportapp/data/storage/'+link
                    rename_pdf_url='jsreportapp/data/storage/'+file_suffix+"_"+link
                    os.rename(fileurl_pdf,rename_pdf_url)
                    fileurl_pdf=rename_pdf_url
                    localfile=open(fileurl_pdf,"rb")
                    djangofile=File(localfile)
                    filepath=get_file_path(user.username,localfile.name)
                    fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
                    fileurl+=filepath
                    pdffile=PrivatePdfDocument(user=user,record=r,upload=djangofile,document_link=filepath)
                    pdffile.save()
                    fileurl='/get_file/'+str(r.id)+'/'
                    response = JsonResponse({'status': 'Valid', 'message': 'File processed','fileurl':'/get_file/'})
                    response.status_code = 200
                    return response
                if(reporttype == "PUR_EFF"):
                    result=r.results
                    links=r.pdf_attachments.all()
                    s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
                    for i in range(len(links)):
                        attach=links[i]
                        fileurl=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+attach.document_link
                        s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=fileurl)
                        attach.delete()
                    comments=r.comments
                    print(comments["values"])
                    file_suffix=custom_slugify(str(cust.name))
                    jsonparams={
                        "template": { "name" : "PE-Main","recipe": "chrome-pdf" },
                        "data" : {"result":result,"comments":comments},
                        "options": { "reports": { "save": "true" },"reportName": "myreport"}
                    }
                    jsrep=requests.post("http://localhost:5543/api/report",json=jsonparams,auth=('ca-reporting','fastca123@'))
                    link=jsrep.headers['Report-BlobName']
                    fileurl_pdf='jsreportapp/data/storage/'+link
                    rename_pdf_url='jsreportapp/data/storage/'+file_suffix+"_"+link
                    os.rename(fileurl_pdf,rename_pdf_url)
                    fileurl_pdf=rename_pdf_url
                    localfile=open(fileurl_pdf,"rb")
                    djangofile=File(localfile)
                    filepath=get_file_path(user.username,localfile.name)
                    fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
                    fileurl+=filepath
                    pdffile=PrivatePdfDocument(user=user,record=r,upload=djangofile,document_link=filepath)
                    pdffile.save()
                    fileurl='/get_file/'+str(r.id)+'/'
                    response = JsonResponse({'status': 'Valid', 'message': 'File processed','fileurl':'/get_file/'})
                    response.status_code = 200
                    return response
                if(reporttype == "CON_ANA"):
                    result=r.results
                    links=r.pdf_attachments.all()
                    s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
                    for i in range(len(links)):
                        attach=links[i]
                        fileurl=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+attach.document_link
                        s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=fileurl)
                        attach.delete()
                    comments=r.comments
                    print(comments.values)
                    file_suffix=custom_slugify(str(cust.name))
                    jsonparams={
                        "template": { "name" : "CA-Main","recipe": "chrome-pdf" },
                        "data" : {"results":result,"comments":comments},
                        "options": { "reports": { "save": "true" },"reportName": "myreport"}
                    }
                    jsrep=requests.post("http://localhost:5543/api/report",json=jsonparams,auth=('ca-reporting','fastca123@'))
                    link=jsrep.headers['Report-BlobName']
                    fileurl_pdf='jsreportapp/data/storage/'+link
                    rename_pdf_url='jsreportapp/data/storage/'+file_suffix+"_"+link
                    os.rename(fileurl_pdf,rename_pdf_url)
                    fileurl_pdf=rename_pdf_url
                    localfile=open(fileurl_pdf,"rb")
                    djangofile=File(localfile)
                    filepath=get_file_path(user.username,localfile.name)
                    fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
                    fileurl+=filepath
                    pdffile=PrivatePdfDocument(user=user,record=r,upload=djangofile,document_link=filepath)
                    pdffile.save()
                    fileurl='/get_file/'+str(r.id)+'/'
                    response = JsonResponse({'status': 'Valid', 'message': 'File processed','fileurl':'/get_file/'})
                    response.status_code = 200
                    return response
                if(reporttype == "S_C_R"):
                    result=r.results
                    links=r.pdf_attachments.all()
                    s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
                    for i in range(len(links)):
                        attach=links[i]
                        fileurl=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+attach.document_link
                        s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=fileurl)
                        attach.delete()
                    comments=r.comments
                    file_suffix=custom_slugify(str(cust.name))
                    jsonparams={
                        "template": { "name" : "SCR-Main","recipe": "chrome-pdf" },
                        "data" : {"result":result,"comments":comments},
                        "options": { "reports": { "save": "true" },"reportName": "myreport"}
                    }
                    jsrep=requests.post("http://localhost:5543/api/report",json=jsonparams,auth=('ca-reporting','fastca123@'))
                    link=jsrep.headers['Report-BlobName']
                    fileurl_pdf='jsreportapp/data/storage/'+link
                    rename_pdf_url='jsreportapp/data/storage/'+file_suffix+"_"+link
                    os.rename(fileurl_pdf,rename_pdf_url)
                    fileurl_pdf=rename_pdf_url
                    localfile=open(fileurl_pdf,"rb")
                    djangofile=File(localfile)
                    filepath=get_file_path(user.username,localfile.name)
                    fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
                    fileurl+=filepath
                    pdffile=PrivatePdfDocument(user=user,record=r,upload=djangofile,document_link=filepath)
                    pdffile.save()
                    fileurl='/get_file/'+str(r.id)+'/'
                    response = JsonResponse({'status': 'Valid', 'message': 'File processed','fileurl':'/get_file/'})
                    response.status_code = 200
                    return response
            else:
                response = JsonResponse({'status': 'Invalid', 'message': 'Not Allowed'})
                response.status_code = 400
                return response

@login_required(login_url='/accounts/login')
def get_task_status(request,id):
    res = AsyncResult(id)
    return JsonResponse({'status': res.status, 'traceback': res.traceback})


@receiver(post_save, sender=Report)
def align_reportrecords(sender, **kwargs):
    #     client =   Client(hosts='http://localhost:8529')
    #
    # # # Connect to "_system" database as root user.
    #
    #     db = client.db('_system', username='root', password='porqy123')
    #
    #     if not db.has_database('firstcourse'):
    #         db.create_database('firstcourse')
    #     fc_db=client.db('firstcourse',username='root', password='porqy123')
    #     if fc_db.has_collection('outputs'):
    #         outputs = fc_db.collection('outputs')
    #     else:
    #         outputs = fc_db.create_collection('outputs')
    #     if fc_db.has_graph('workspace'):
    #         workspace = fc_db.graph('workspace')
    #     else:
    #         workspace = fc_db.create_graph('workspace')
    #
    #     if fc_db.has_vertex_collection('teamleads'):
    #         teamleads = fc_db.vertex_collection('teamleads')
    #
    #     if fc_db.has_vertex_collection('teamleads'):
    #         teamleads = fc_db.vertex_collection('teamleads')
    return True




