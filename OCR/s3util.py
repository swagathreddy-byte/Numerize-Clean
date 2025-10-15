import os
import boto3
from datetime import datetime
import urllib
import re
from django.conf import settings
from .models import OcrImageDocument,DownloadCache

from botocore.client import Config
import random
import string

def get_random_alphanumeric_string(length):
    letters_and_digits = string.ascii_letters + string.digits
    result_str = ''.join((random.choice(letters_and_digits) for i in range(length)))
    return result_str



aws_access_key_id = settings.AWS_ACCESS_KEY_ID
aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY
default_region_name = 'us-east-2'
bucket_name = settings.AWS_OCR_BUCKET_NAME
url_base = settings.AWS_OCR_URL
cur_dir = os.path.dirname(os.path.abspath(__file__))

temp_folder_path = "cache/img"
temp_folder_path = cur_dir+"/"+temp_folder_path


def get_boto_session():
    aws_config = {
        'aws_access_key_id': aws_access_key_id,
        'aws_secret_access_key': aws_secret_access_key,
        'region_name': default_region_name
    }
    return boto3.session.Session(**aws_config)


def get_s3_client():
    boto_session = get_boto_session()
    return boto_session.client(service_name="s3")


def get_s3_resource():
    boto_session = get_boto_session()
    return boto_session.resource('s3')


def download_file(obj_name):
    file_name = obj_name.split('/')[-1]
    file_path = os.path.join(temp_folder_path, file_name)
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            get_s3_client().download_fileobj(bucket_name, obj_name, f)
    return file_path


# Get pending images list in given folder
def list_pending(folder_name, cursor=""):
    # print("List Pending")
    if folder_name is None:
        folder_name = ""  # datetime.today().strftime("%d/%m/%Y")
    else:
        folder_name = folder_name + "/"
    client = get_s3_client()
    folderpath = folder_name
    paginator = client.get_paginator('list_objects')
    pending_list = []
    marker = cursor if cursor else folderpath
    # FIXME: change max items and page size
    paginationConfig = {
        'MaxItems': 15,
        'PageSize': 10,
        'StartingToken': marker
    }
    is_truncated = True
    for page in paginator.paginate(Bucket=bucket_name, Prefix=folderpath, PaginationConfig=paginationConfig):
        # print("PAGE", page)
        for content in page.get('Contents', ()):
            if content['Key'][-1] == "/":
                continue
            marker = content['Key']
            is_truncated = page.get('IsTruncated')
            img_entry = {'url': url_base + content['Key'], 'rel_path': urllib.parse.quote_plus(content['Key']),
                         'filename': content['Key'].split('/')[-1]}
            pending_list.append(img_entry)

    result = {
        "next": marker,
        "has_more": is_truncated,
        "pending_list": pending_list
    }
    return result

def list_images(customer,month,year):
    img_links = OcrImageDocument.objects.filter(customer=customer).filter(month=month).filter(year=year)
    s3 = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY, config=Config(signature_version='s3v4'),region_name='us-east-2')
    foldername='downloads/ocr'
    if(len(img_links)>0):
        modelsuccess=False
        while(modelsuccess == False):
            try:
                folder=DownloadCache(foldername=get_random_alphanumeric_string(10))
                folder.save()
                foldername=folder.foldername
                modelsuccess=True
            except:
                folder=DownloadCache(foldername=get_random_alphanumeric_string(10))
                folder.save()
                foldername = folder.foldername
                modelsuccess=False

        foldername=folder.foldername
        os.mkdir(settings.BASE_DIR+"/media/downloads/ocr/"+foldername)
    links = []
    copy_s3 = boto3.resource(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )

    basic_cache_url = 'https://%s.s3.amazonaws.com' % settings.AWS_CACHE_BUCKET_NAME


    for i in range(len(img_links)):
        # print("Printing")
        # print(img_links[i].document_link)
        copy_source = {'Bucket': settings.AWS_OCR_BUCKET_NAME,'Key':img_links[i].document_link}

        # print(foldername)
        #url = s3.generate_presigned_url(ClientMethod='get_object', Params=copy_source,ExpiresIn=3600)
        name = img_links[i].document_link.split("/")[-1]
        copy_s3.meta.client.copy_object(
            ACL='public-read',
            Bucket="fc-cache",
            CopySource=copy_source,
            Key="ocr/"+foldername+"/"+name
        )
        # print(name)
        # print(str(foldername))
        # print(settings.BASE_DIR+"media/downloads/"+foldername+"/"+name)
        s3.download_file(settings.AWS_OCR_BUCKET_NAME, img_links[i].document_link,settings.BASE_DIR+"/media/downloads/ocr/"+foldername+"/"+name)
        path="media/downloads/ocr/"+foldername+"/"+name
        # print(path)
        url=basic_cache_url+"/ocr/"+foldername+"/"+name
        img_entry = {'url': url, 'key': foldername, 'name': name}
        links.append(img_entry)

    return links
# Upload file to S3
def upload_file(local_file_path, s3_path, content_type=None):
    s3_resource = get_s3_resource()
    bucket = s3_resource.Bucket(bucket_name)
    extra_args = {'ACL': 'public-read', "ContentEncoding": "gzip"}
    if content_type is not None:
        extra_args["ContentType"] = content_type
    bucket.upload_fileobj(open(local_file_path, 'rb'), s3_path, ExtraArgs=extra_args)


def move_file(old_path, new_path):
    s3_resource = get_s3_resource()
    # Copy object A as object B
    s3_resource.Object(bucket_name, new_path).copy_from(CopySource=bucket_name+"/"+old_path)
    # Delete the former object A
    s3_resource.Object(bucket_name, old_path).delete()


# On Invoice image processed, save data to S3
def on_processed(csv_file, text_extract_file, s3_img_file_path):
    print(csv_file)
    print(text_extract_file)
    print(s3_img_file_path)
    new_path = s3_img_file_path.replace("pending", "processed")
    move_file(s3_img_file_path, new_path)

    # upload csv
    s3_csv_path = re.sub(r'\.[A-Za-z]+$', ".csv", new_path)
    upload_file(csv_file, s3_csv_path)

    # upload text json
    s3_json_path = re.sub(r'\.[A-Za-z]+$', ".json", new_path)
    upload_file(text_extract_file, s3_json_path)


def is_allowed_file(filename):
    print(filename)
    if len(filename) > 4 and (filename[-4:] == ".jpg" or filename[-4:] == ".png"):
        return True
    else:
        return False
