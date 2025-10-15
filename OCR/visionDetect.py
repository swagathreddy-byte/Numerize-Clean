import io
import os
import re
from os import path
import json
import ntpath
import datetime

# Imports the Google Cloud client library
from google.cloud import vision
from google.cloud.vision import types
from google.protobuf.json_format import MessageToDict
from .s3util import temp_folder_path


import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'OCR/Firstcourse-OCR-de04e651c5a5.json'



# Google document OCR - TEST Method
def detect_document(path):
    """Detects document features in an image."""
    client = vision.ImageAnnotatorClient()

    with io.open(path, 'rb') as image_file:
        content = image_file.read()

    image = vision.types.Image(content=content)

    response = client.document_text_detection(image=image)

    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            print('\nBlock confidence: {}\n'.format(block.confidence))

            for paragraph in block.paragraphs:
                print('Paragraph confidence: {}'.format(
                    paragraph.confidence))

                for word in paragraph.words:
                    word_text = ''.join([
                        symbol.text for symbol in word.symbols
                    ])
                    print('Word text: {} (confidence: {})'.format(
                        word_text, word.confidence))

                    for symbol in word.symbols:
                        print('\tSymbol: {} (confidence: {})'.format(
                            symbol.text, symbol.confidence))

    if response.error.message:
        raise Exception(
            '{}\nFor more info on error messages, check: '
            'https://cloud.google.com/apis/design/errors'.format(
                response.error.message))


# Fetch OCR data from local image file or remote URL and return JSON response
def getTextExtract(imgpath, urlpath):
    # Instantiates a client
    client = vision.ImageAnnotatorClient()
    print(urlpath)
    if urlpath:
        image = vision.types.Image()
        image.source.image_uri = urlpath
    else:
        # The name of the image file to annotate
        file_name = os.path.abspath(imgpath) #'fwdpurchasebills/Picture Bill_1.jpg'

        # Loads the image into memory
        with io.open(file_name, 'rb') as image_file:
            content = image_file.read()

        image = types.Image(content=content)

    # Performs label detection on the image file
    response = client.text_detection(image=image)
    json_response = MessageToDict(response)

    # texts = json_response['textAnnotations']

    # print('Texts:')
    # for text in texts:
    #     print('\n"{}"'.format(text.description))
    #
    #     vertices = (['({},{})'.format(vertex.x, vertex.y)
    #                  for vertex in text.bounding_poly.vertices])
    #
    #     print('bounds: {}'.format(','.join(vertices)))

    if response.error.message:
        raise Exception(
            '{}\nFor more info on error messages, check: '
            'https://cloud.google.com/apis/design/errors'.format(
                response.error.message))
    return json_response


# TODO: Fix cache to handle s3 folders
# Fetch Google OCR data and identify primary fields data
# To reduce unnecessary API calls, data is being cached in local folders
def getValueMap(imgpath):
    data = {}
    urlpath = None
    file_name = ntpath.basename(imgpath)
    if imgpath[:4] == "http":
        urlpath = imgpath
        imgpath = os.path.join(temp_folder_path, file_name)
    json_path = re.sub(r'\.[A-Za-z]+$', ".json", imgpath)
    # print(imgpath)
    # print(json_path)
    if path.exists(json_path):
        fp = open(json_path)
        texts_string = fp.read()
        resp = json.loads(texts_string)
        texts = resp['textAnnotations']
        fp.close()
    else:
        resp = getTextExtract(imgpath, urlpath)
        texts = resp['textAnnotations']
        fw = open(json_path, "w")
        texts_string = json.dumps(resp)
        fw.write(texts_string)
        fw.close()
    gst_values = re.findall("GST.*?\d[\d\w]+", texts[0]['description'])
    print(gst_values)
    for val in gst_values:
        gst_value = re.split(': ', val)[-1]
        if len(gst_value) != 15:
            continue
        print("GST: ", gst_value)
        data["gst_no"] = gst_value  # first valid gst value
        break

    invoice_values = re.findall("(?i)Invoice.*?[\d\w/]+|(?i)Bill.*?[\d\w/]+", texts[0]['description'])
    print(invoice_values)
    if len(invoice_values) == 1:
        invoice_value = re.split(': ', invoice_values[0])[-1]
        print("Invoice No: ", invoice_value)
        data["invoice_no"] = invoice_value

    current_year = datetime.datetime.now().year
    prev_year = str(current_year - 1)
    current_year = str(current_year)
    date_values = re.findall("[\d]+[ /-]+[a-zA-Z0-9]+[ /-]+"+current_year+"|[\d]+[ /-]+[a-zA-Z0-9]+[ /-]+"+prev_year, texts[0]['description'])
    date_values = date_values + re.findall("[\d]+[ /-]+[a-zA-Z0-9]+[ /-]+" + current_year[-2:] + "|[\d]+[ /-]+[a-zA-Z0-9]+[ /-]+" + prev_year[-2:], texts[0]['description'])
    print(date_values)
    import dateutil.parser
    for dt in date_values:
        dt_obj = None
        try:
            dt_obj = dateutil.parser.parse(dt, dayfirst=True)
        except:
            pass
        if dt_obj:
            data["invoice_date"] = dt_obj.strftime("%Y-%m-%d")
            break

    data["texts"] = texts #json.dumps({"texts": texts}) #re.sub("&", "and", texts_string)
    return data
