from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.http import HttpResponse,JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from . import s3util
import json
from . import visionDetect
import urllib
from django.core.files.storage import FileSystemStorage
from slugify import Slugify,slugify
from django.conf import settings
import datetime
import os
from django.core.files import File
from .models import OcrImageDocument,OcrCSVDocument,OcrJSONDocument

custom_slugify=Slugify()
custom_slugify.safe_chars = ('.png','.jpg','.jpeg')

def get_ocr_file_path(name,year,month,filename):
    actualfilename=os.path.basename(filename)

    return 'input/{0}/{1}/{2}/{3}'.format(name,year,month,actualfilename)




@login_required(login_url='/accounts/login')
def get_imglist(request):
    if(request.method=="GET"):
        # print("Get Img List")
        customerid = request.GET.get("customer")
        monthyear = request.GET.get("month-year")
        month = int(monthyear.split()[0])
        year = int(monthyear.split()[1])

        data = {"hasMore": False, "next": None, "customerid": customerid}

        if customerid is not None:
            result = s3util.list_images(customerid,month,year)
            # data["next"] = result["next"]
            # data["hasMore"] = result["has_more"]
            data["imgList"] = result
            data["customerid"] = customerid
        return JsonResponse(data)



@login_required(login_url='/accounts/login')
def get_imagedata(request):
    if(request.method=='GET'):
        # print("Hey get image data")
        key = request.GET.get('key')
        name=request.GET.get('name')
        # print(img_rel_path)
        # img_url = s3util.public_url_base + urllib.parse.unquote(img_rel_path)
        img_path = settings.BASE_DIR +"/"+ "media/downloads/ocr/"+str(key)+"/"+str(name)
        data = visionDetect.getValueMap(img_path)
        # data = {"invoice_no": "123123123"}
        # data["imgpath"] = img_path
        return JsonResponse(data)

@login_required(login_url='/accounts/login')
def upload_image(request):
    if(request.method=='POST'):

        if not request.user.groups.filter(name='Customer').exists():
            if "customer" not in request.POST:
                response = JsonResponse({'status': 'Invalid', 'message': 'Customer ID missing '})
                response.status_code = 400
            if "images" not in request.FILES:
                response = JsonResponse({'status': 'Invalid', 'message': 'Images missing '})
                response.status_code = 400
            if "month-year" not in request.POST:
                response = JsonResponse({'status': 'Invalid', 'message': 'Month Year is missing '})
                response.status_code = 400
            else:
                customerid = request.POST.get("customer")
                monthyear=request.POST.get("month-year")
                user=request.user
                month=int(monthyear.split()[0])
                year=int(monthyear.split()[1])
                print(month)
                cust = Customer.objects.get(id=int(customerid))
                fs = FileSystemStorage(location='media/uploads/ocr')
                for i in range(len(request.FILES)):
                    name='images['+str(i)+']'
                    if(name in request.FILES):
                        file=request.FILES[name]
                        img_filename = fs.save(custom_slugify(file.name), file)
                        img_url = fs.url(img_filename)
                        pe_url = settings.BASE_DIR + "/media/uploads/ocr/" + img_url
                        localfile = open(pe_url, "rb")
                        djangofile = File(localfile)
                        filepath = get_ocr_file_path(cust.user_account.username,year,month,pe_url)
                        print(filepath)
                        fileurl = settings.AWS_OCR_URL
                        fileurl += filepath
                        # print(fileurl)
                        imgfile = OcrImageDocument(user=user, customer=cust, month=month,year=year,image_file=djangofile, document_link=filepath)
                        imgfile.save()

                        if os.path.exists(pe_url):
                            os.remove(pe_url)

                response = JsonResponse({'status': 'Valid', 'message': 'Images successfully uploaded'})
                response.status_code = 200
            return response
    if (request.method == 'GET'):
        return render(request, 'ocr/imgupload.html')


@login_required
def post_result(request):
    if request.method=="POST":
        result=request.POST.get("data")
        result=json.loads(result)
        print(result)
        key=result["key"]
        name=result["name"]
        customerid = result["customer"]
        monthyear = result["date"]
        print(monthyear)
        user = request.user
        month = int(monthyear.split()[0])
        year = int(monthyear.split()[1])
        print(month)
        cust = Customer.objects.get(id=int(customerid))
        jsonurl="media/downloads/ocr/"+str(key)+"/invoiceresult.json"
        with open(jsonurl, 'w') as json_file:
            json.dump(result, json_file)
        # fs = FileSystemStorage(location='media/uploads/ocr')

        # img_filename = fs.save(custom_slugify(file.name), file)
        # img_url = fs.url(img_filename)
        pe_url = settings.BASE_DIR + "/"+ jsonurl
        localfile = open(pe_url, "rb")
        djangofile = File(localfile)
        filepath = get_ocr_file_path(cust.user_account.username, year, month, pe_url)
        print(filepath)
        fileurl = settings.AWS_OCR_URL
        fileurl += filepath
        # print(fileurl)
        jsonfile = OcrJSONDocument(user=user, customer=cust, month=month, year=year, json_file=djangofile,
                                   document_link=filepath)
        jsonfile.save()

        if os.path.exists(pe_url):
            os.remove(pe_url)

        response = JsonResponse({'status': 'Valid', 'message': 'Results have been submitted'})
        response.status_code = 200
        return response