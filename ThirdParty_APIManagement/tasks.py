from celery import shared_task
from ReportManagement.models import Report,Receivables,Payables
from CustomerManagement.models import *
from django.conf import settings
import requests
import json
from pytz import timezone
import datetime


# global variables
op_list=[]   # output variable [{'id':'invoiceId/salesId/billId/depositId', 'value':'invoice/sales/bill/deposit'}]
invoice_list=[] #list of invoice ids
bill_list=[] #list of bill ids
sales_rep_list=[] #list of sales_rep ids
deposit_list=[] #list of deposit ids


@shared_task
def pull_invoice_api(reportid,custid,access_token):
    print("Pull Invoice API called")
    report=Report.objects.get(pk=reportid)
    qb_id=report.customer.qb_id
    qb_api=report.qb_api
    # route= '/v3/company/'+str(qb_id)+'/reports/ProfitAndLossDetail?

    auth_header= 'Bearer '+ access_token
    headers = {'Authorization': auth_header, 'accept': 'application/json'}
    # print("About to the PL Detail")
    result=[]
    if("Row" in qb_api["Rows"]):
        len_top=len(qb_api["Rows"]["Row"])
        for l in range(len_top):
            if("Header" in qb_api["Rows"]["Row"][l]):
                if("Row" in qb_api["Rows"]["Row"][l]["Rows"]):
                    second_top=len(qb_api["Rows"]["Row"][l]["Rows"]["Row"])
                    for m in range(second_top):
                        if("Header" in qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]):
                            if("Row" in qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]):
                                len_income=len(qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"])
                                for i in range(len_income):
                                    if("Header" in qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]):
                                        if("Row" in qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]["Rows"]):
                                            len_subincome=len(qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]["Rows"]["Row"])
                                            for j in range(len_subincome):
                                                if("Header" in qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]["Rows"]["Row"][j]):
                                                    if("Row" in qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]["Rows"]["Row"][j]["Rows"]):
                                                        len_subsubincome=len(qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]["Rows"]["Row"][j]["Rows"]["Row"])
                                                        for k in range(len_subsubincome):
                                                            if("Header" not in qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]["Rows"]["Row"][j]["Rows"]["Row"][k]):
                                                                if("ColData" in qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]["Rows"]["Row"][j]["Rows"]["Row"][k]):
                                                                    values={
                                                                        "label": qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]["Rows"]["Row"][j]["Rows"]["Row"][k]["ColData"][1]["value"],
                                                                        "id" : qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]["Rows"]["Row"][j]["Rows"]["Row"][k]["ColData"][1]["id"],
                                                                        "subsubheader":qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]["Rows"]["Row"][j]["Header"]["ColData"][0]["value"],
                                                                        "subheader" : qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]["Header"]["ColData"][0]["value"],
                                                                        "header":qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Header"]["ColData"][0]["value"],
                                                                        "head":qb_api["Rows"]["Row"][l]["Header"]["ColData"][0]["value"]
                                                                    }
                                                                    result.append(values)
                                                            else:
                                                                print("This is never ending isnt it?")
                                                                for k in range(len_subsubincome):
                                                                    print("#######################",qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]["Rows"]["Row"][j]["Rows"]["Row"][k]["Header"]["ColData"][0]["value"],"##############")

                                                else:
                                                    # print(qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Header"]["ColData"][0]["value"])
                                                    if("ColData" in qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]["Rows"]["Row"][j]):
                                                        values={
                                                            "label": qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]["Rows"]["Row"][j]["ColData"][1]["value"],
                                                            "id" : qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]["Rows"]["Row"][j]["ColData"][1]["id"],
                                                            "subheader" : qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Rows"]["Row"][i]["Header"]["ColData"][0]["value"],
                                                            "header":qb_api["Rows"]["Row"][l]["Rows"]["Row"][m]["Header"]["ColData"][0]["value"],
                                                            "head":qb_api["Rows"]["Row"][l]["Header"]["ColData"][0]["value"]
                                                        }
                                                        result.append(values)

    report.invoice_list=result
    report.save()
    with open("result.json", "w") as outfile:
        json.dump(result, outfile, indent=4)
    return {'status': 'Valid', 'message': 'Invoice list generated'}
        #r = requests.get(settings.SANDBOX_QBO_BASEURL + route, headers=headers)


@shared_task
def getPLInfo(access_token,realmId,initdate,finaldate):
    #cust=Customer.objects.get(pk=custid)
    #qb_id=cust.qb_id
    #route= '/v3/company/'+str(qb_id)+'/reports/ProfitAndLossDetail?start_date='+initdate+'&end_date='+finaldate+'&minorversion=51'

    route= '/v3/company/'+str(realmId)+'/reports/ProfitAndLossDetail?start_date='+initdate+'&end_date='+finaldate+'&minorversion=51'
    auth_header= 'Bearer '+ access_token
    print(settings.SANDBOX_QBO_BASEURL + route)
    headers = {'Authorization': auth_header, 'accept': 'application/json'}
    r = requests.get(settings.SANDBOX_QBO_BASEURL + route, headers=headers)
    print(r.content)
    status_code = r.status_code

    # print(status_code)
    if status_code != 200:
        response = ''
        return response, status_code
    # data=''
    # with open('ThirdParty_APIManagement/example.json') as f:
    #     data = json.load(f)

    response = json.loads(r.text)
    getIDs(response,access_token,realmId)
    return op_list, status_code


def getPayablesInfo(access_token,realmId,initdate,finaldate):
    #cust=Customer.objects.get(pk=custid)
    #qb_id=cust.qb_id
    #route= '/v3/company/'+str(qb_id)+'/reports/ProfitAndLossDetail?start_date='+initdate+'&end_date='+finaldate+'&minorversion=51'
    print("Calling payables info")
    print(access_token)
    route= '/v3/company/'+str(realmId)+'/reports/VendorBalance?start_date='+initdate+'&end_date='+finaldate+'&minorversion=51'
    print(route)
    auth_header= 'Bearer '+ access_token
    headers = {'Authorization': auth_header, 'accept': 'application/json'}
    r = requests.get(settings.SANDBOX_QBO_BASEURL + route, headers=headers)
    status_code = r.status_code
    print(r.text)

    # print(status_code)
    if status_code != 200:
        response = ''
        return response, status_code
    response = json.loads(r.text)

    return response, status_code


def getReceivablesInfo(access_token,realmId,initdate,finaldate):
    #cust=Customer.objects.get(pk=custid)
    #qb_id=cust.qb_id
    #route= '/v3/company/'+str(qb_id)+'/reports/ProfitAndLossDetail?start_date='+initdate+'&end_date='+finaldate+'&minorversion=51'

    route= '/v3/company/'+str(realmId)+'/reports/CustomerBalance?start_date='+initdate+'&end_date='+finaldate+'&minorversion=51'
    auth_header= 'Bearer '+ access_token
    # print(settings.SANDBOX_QBO_BASEURL + route)
    headers = {'Authorization': auth_header, 'accept': 'application/json'}
    r = requests.get(settings.SANDBOX_QBO_BASEURL + route, headers=headers)
    status_code = r.status_code
    if status_code != 200:
        response = ''
        return response, status_code
    response = json.loads(r.text)
    return response, status_code


def getIDs(response,accesstoken,realmid):
    '''
    this function takes response[JSON] as input from PLdetail API and updates the global variable op_list
    '''
    # print(response)
    jdata = response#json.loads(response)
    def json_list(d, op_list=op_list):
        # print("json_list")
        temp_d = {}
        temp_d['value'] = d['value']
        temp_d['id'] = d['id']
        temp_d['api'] = getAPIResult(d['id'], d['value'],access_token=accesstoken,realmId=realmid)
        print(temp_d)
        op_list.append(temp_d)

    def dict_m(d, invoice_list=invoice_list, bill_list=bill_list, sales_rep_list=sales_rep_list):
        # print("r")
        try:
            if (d['value'] == 'Invoice'):
                # print(d['id'])
                if d['id'] not in invoice_list:
                    # print(d['id'])
                    invoice_list.append(d['id'])
                    json_list(d)
                return
            if (d['value' == 'Bill']):
                # print(d['id'])
                if d['id'] not in bill_list:
                    bill_list.append(d['id'])
                    json_list(d)
                return
            if (d['value'] == 'Sales receipt'):
                # print(d['id'])
                if d['id'] not in sales_rep_list:
                    sales_rep_list.append(d['id'])
                    json_list(d)
                return
            if (d['value'] == 'Deposit'):
                # print(d['id'])
                if d['id'] not in deposit_list:
                    deposit_list.append(d['id'])
                    json_list(d)
                return
        except:
            pass
        if (type(d) is list):
            for val in range(len(d)):
                dict_m(d[val])
        if (type(d) is dict):
            for k in d.keys():
                dict_m(d[k])

    dict_m(jdata)
    # print(invoice_list)
    # print(len(op_list))
    # print(op_list)


def getAPIResult(id,inp,access_token,realmId):
    '''
    this function takes invoice/sales/deposit/bill ids and values and returns their respective API result
    '''
    path = ""
    if(inp == 'Invoice'):
        path = "/v3/company/{}/invoice/{}?minorversion=51"
    elif(inp== 'Bill'):
        path = "/v3/company/{}/bill/{}?minorversion=51"
    elif (inp == 'Deposit'):
        path = "/v3/company/{}/deposit/{}?minorversion=51"
    elif (inp == 'SalesReceipt'):
        path = "/v3/company/{}/salesreceipt/{}?minorversion=51"
    route = path.format(realmId,id)
    auth_header= 'Bearer '+ access_token
    print(settings.SANDBOX_QBO_BASEURL + route)
    headers = {'Authorization': auth_header, 'accept': 'application/json'}
    r = requests.get(settings.SANDBOX_QBO_BASEURL + route, headers=headers)
    # print(r.content)
    status_code = r.status_code

    # print(status_code)
    if status_code != 200:
        response = ''
        return response, status_code
    response = json.loads(r.text)
    return response