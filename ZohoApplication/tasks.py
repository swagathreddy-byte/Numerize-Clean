# python specific imports
import requests
import json

# django specific imports
from celery import shared_task
from pytz import timezone
from datetime import datetime, date, timedelta
from django.conf import settings
from rest_framework import status

#application specific imports
from ReportManagement.models import Payables,Report
from ZohoApplication.services import get_zoho_access_token
from ThirdParty_APIManagement.tasks import getPrevVendorBalance
from .config import  bill_mapping,bill_payment_mapping,invoice_mapping,expense_mapping,journal_mapping
from QbApplication.services import insert_qb_transactions

def zohoAPIRequest(zoho_api_url,api_params,res_type,sort_column,zoho_access_token):
    print("--------------------zoho API Request ----------")
    transaction_list=[]
    page=1
    per_page=200
    def api_call(page,zoho_api_url):
        print("---------------------------------api call---------------------")
        api_url=zoho_api_url+"&page={0}&per_page={1}&sort_column={2}&sort_order=A".format(page,per_page,sort_column)
        for param in api_params:
            api_url=api_url+"&{0}={1}".format(param,api_params[param])
        print(api_url)
        print(zoho_access_token)
        auth_header = 'Bearer ' + zoho_access_token
        headers = {'Authorization': auth_header, 'accept': 'application/json'}
        r = requests.get(api_url, headers=headers)
        # print(r.text)
        if r.status_code==200:
            api_response = json.loads(r.text)
            res_list=api_response[res_type]
            print("-----------------response----------------")
            print(len(res_list))
            for l in res_list:
                if res_type !="account_transactions":
                    transaction_list.append(l)
                else:
                    if page==1:
                        transaction_list.append(l)
                    else:
                        res_grp_list=l[res_type]
                        for a in res_grp_list:
                            transaction_list[0][res_type].append(a)



            if api_response["page_context"]["has_more_page"]:
                page=page+1
                api_call(page,zoho_api_url) # call api to get next page transactions
            return transaction_list,r.status_code

    if zoho_access_token !=None:
        print("--before api call---")
        print(zoho_api_url)
        response,responsestatus = api_call(page,zoho_api_url)
        # print("***************************** response ***********************************************")
        # print(response)
        return response,responsestatus
    else:
        return "", status.HTTP_401_UNAUTHORIZED

@shared_task
def getZohoPayablesbyReportID(report_id, zoho_access_token, zoho_org_id,pull_vendor_list):
    print("Inside Get getZohoPayablesbyReportID ", report_id)
    # pull_vendor_list=json.loads(pull_vendor_list)
    print(pull_vendor_list)
    print(len(pull_vendor_list))

    report = Payables.objects.get(id=report_id)

    if (zoho_org_id != '' and zoho_access_token != ''):
        print("access token")
        print(zoho_access_token)
        d=datetime(report.year, report.month, report.day).astimezone(timezone('Asia/Kolkata'))
        finaldate=d.strftime("%Y-%m-%d")
        initdate=datetime(report.year, report.month, 1).astimezone(timezone('Asia/Kolkata')).strftime("%Y-%m-%d")
            # (d-timedelta(days=1))

        print(initdate+" : "+finaldate)

        vendor_api_url=settings.ZOHO_BOOKS_API_URL + "/vendors?organization_id={0}".format(zoho_org_id)
        vendor_api_params={"filter_by":"Status.Active"}
        vendor_res_type="contacts"
        vendor_sort_column="vendor_name"
        vendor_list_data,vendor_responsestatus=zohoAPIRequest(vendor_api_url,vendor_api_params,vendor_res_type,vendor_sort_column,zoho_access_token)

        # vendor_list_url = settings.ZOHO_BOOKS_API_URL + "/vendors?filter_by=Status.Active&organization_id={0}".format(zoho_org_id)
        # print(vendor_list_url)
        # headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
        # print(headers)
        # vendor_list_res = requests.get(vendor_list_url, headers=headers)
        if vendor_responsestatus==200:
            # vendor_list_data=json.loads(vendor_list_res.text)["contacts"]
            print("---------------vendor list-------")
            print(len(vendor_list_data))
            payables_input_api=report.input_api
            print(payables_input_api)
            print("--------payables_input_api------")
            if len(pull_vendor_list)>0:
                if payables_input_api is not None and "values" in  payables_input_api:
                    details=payables_input_api
                else:
                    details = {
                        "values": []
                    }
            else:
                details = {
                    "values": []
                }


            print(len(details["values"]))
            print("curr pay report for ", report.day, report.month, report.year)
            vendor_list_json = {}
            for vendor in vendor_list_data:
                vendorid = vendor["contact_id"]
                add_vendor_flag=False
                if len(pull_vendor_list)>0:
                    if vendorid in pull_vendor_list:
                        add_vendor_flag=True
                else:
                    add_vendor_flag=True

                if add_vendor_flag:
                    vendorname = vendor["vendor_name"]
                    prevdate = datetime(report.year, report.month, 1).astimezone(timezone('Asia/Kolkata'))
                    prevdate = (prevdate - timedelta(days=1)).strftime("%Y-%m-%d")
                    prevbalance, pull_payables_for_vendor = getPrevVendorBalance(vendorid, zoho_org_id, prevdate)
                    if pull_payables_for_vendor == "True":
                        vendor_list_json[vendorid] = {"vendorid": vendorid, "vendorname": vendorname,
                                                      "prevbalance": prevbalance, "pay_up_det_arr": []}
            print(vendor_list_json)
            # vendor bill details api

            vendor_bills_api_url=settings.ZOHO_BOOKS_API_URL + "/reports/billdetails?organization_id={0}".format(zoho_org_id)
            vendor_bills_api_params={"filter_by":"BillDate.CustomDate","from_date":initdate,"to_date":finaldate,"group_by":"vendor_name"}
            if len(pull_vendor_list)>0:
                vendor_bills_api_params["rule"]={"columns":[{"index":1,"field":"vendor_id","value":pull_vendor_list,"comparator":"in","group":"bill"}],"criteria_string":"1"}

            vendor_bills_res_type="bill_details"
            vendor_bills_sort_column="date"
            bill_details_data,vendor_bills_responsestatus=zohoAPIRequest(vendor_bills_api_url,vendor_bills_api_params,vendor_bills_res_type,vendor_bills_sort_column,zoho_access_token)
            # vendor_bills_list_url=settings.ZOHO_BOOKS_API_URL + "/reports/billdetails?organization_id={0}&filter_by=BillDate.CustomDate&from_date={1}&to_date={2}&group_by=vendor_name".format(zoho_org_id,initdate,finaldate)
            # vendor_bills_list_res = requests.get(vendor_bills_list_url, headers=headers)
            if vendor_bills_responsestatus==200:
                print("------------------------------bill details data-----------------")
                print(bill_details_data)

                # bill_details_data=json.loads(vendor_bills_list_res.text)["bill_details"]
                for billdetail in bill_details_data:
                    billvendor = billdetail["group_name"]
                    if billvendor in vendor_list_json:
                        for bill in billdetail["bills"]:
                            billacctdetails = {"id": "", "value": ""}
                            pay_up_det = {"txnid": bill["bill_id"], "invoiceno": bill["bill_number"],
                                          "billtype": "Bill", "billvalue": bill["bcy_total"],
                                          "billacctdetails": billacctdetails, "billdate": bill["date"]}
                            vendor_list_json[billvendor]["pay_up_det_arr"].append(pay_up_det)

            # vendor payment details api
            print("---------------vendor payment details api ----------------------")
            group_by=json.dumps([{"field":"vendor_name","group":"vendor_payment"}])
            vendor_payments_api_url=settings.ZOHO_BOOKS_API_URL + "/reports/vendorpayments?organization_id={0}".format(zoho_org_id)
            vendor_payments_api_params={"filter_by":"PaymentDate.CustomDate","from_date":initdate,"to_date":finaldate,"group_by":group_by}
            if len(pull_vendor_list)>0:
                vendor_payments_api_params["rule"]={"columns":[{"index":1,"field":"vendor_id","value":pull_vendor_list,"comparator":"in","group":"vendor_payment"}],"criteria_string":"1"}
            vendor_payments_res_type="vendor_payments"
            vendor_payments_sort_column="date"
            payments_details_data,vendor_payments_responsestatus=zohoAPIRequest(vendor_payments_api_url,vendor_payments_api_params,vendor_payments_res_type,vendor_payments_sort_column,zoho_access_token)
            # vendor_payments_list_url=settings.ZOHO_BOOKS_API_URL + "/reports/vendorpayments?organization_id={0}&filter_by=PaymentDate.CustomDate&from_date={1}&to_date={2}&group_by={3}".format(zoho_org_id,initdate,finaldate,group_by)
            # vendor_payments_list_res = requests.get(vendor_payments_list_url, headers=headers)
            if vendor_payments_responsestatus==200:
                print("------------------------------payment details data-----------------")
                print(payments_details_data)
                # payments_details_data=json.loads(vendor_payments_list_res.text)["vendor_payments"]
                for paymentdetail in payments_details_data:
                    paymentvendor = paymentdetail["group_name"]
                    if paymentvendor in vendor_list_json:
                        for payment in paymentdetail["vendorpayments"]:
                            print(payment)
                            billacctdetails = {"id": payment["paid_through_account_id"],
                                               "value": payment["paid_through_account_name"]}
                            if payment["payment_mode"] == 'Cash':
                                billacctdetails['value'] = "Cash"
                            pay_up_det = {"txnid": payment["payment_id"], "invoiceno": payment["payment_number"],
                                          "billtype": "Bill Payment", "billvalue": payment["amount"],
                                          "billacctdetails": billacctdetails, "billdate": payment["date"]}
                            vendor_list_json[paymentvendor]["pay_up_det_arr"].append(pay_up_det)

            print("------------------vendor bills updated-----------")
            print(vendor_list_json)
            for vendor in vendor_list_json:
                print(vendor)
                if len(pull_vendor_list)>0:
                    vendor_exists=False
                    for v in range(len(details["values"])):
                        print(details["values"][v])
                        if details["values"][v]["vendorid"]==vendor:
                            vendor_exists=True
                            print("====================vendor exists=====================")
                            details["values"][v]=vendor_list_json[vendor]
                    if not vendor_exists:
                        details["values"].append(vendor_list_json[vendor])
                else:
                    details["values"].append(vendor_list_json[vendor])
            print("---------report input api--------")
            print(details)
            report.input_api = details
            report.save()
            response = {'status': 200, 'message': 'Payables Pulled'}
            return response

        else:

            response = {'status': 404, 'message': 'Unable to pull vendors form zoho'}
            return response

    elif (zoho_org_id == ''):
        response = {'status': 404, 'message': 'Zoho Organisation ID empty'}
        return response
    else:
        response = {'status': 404, 'message': 'Access Token is empty'}
        return response


def bill_mapping_func(bill_data):
    # print("---------------bill mapping func----------")
    # print(bill_data)
    qb_converted_json = {}
    for key in bill_mapping:
        if key in bill_data["bill"]:
            qb_converted_json[bill_mapping[key]] = bill_data['bill'][key]
    qb_converted_json['MetaData'] = {'CreateTime': bill_data['bill']['created_time'],
                                     'LastUpdatedTime': bill_data['bill']['last_modified_time']}
    qb_converted_json['DepartmentRef'] = {'value': bill_data['bill']['branch_id'],
                                          'name': bill_data['bill']['branch_name']}
    qb_converted_json['CurrencyRef'] = {'value': bill_data['bill']['currency_id'],
                                        'name': bill_data['bill']['currency_code']}
    qb_converted_json['VendorRef'] = {'value': bill_data["bill"]['vendor_id'],
                                      'name': bill_data["bill"]['vendor_name']}

    if "tax_total" in bill_data["bill"] and "taxes" in bill_data["bill"] :
        TaxLine=[]
        for tax in bill_data["bill"]["taxes"]:
            tax_line={"Amount":tax["tax_amount"],"DetailType":"TaxLineDetail","TaxLineDetail":{"TaxRateRef":{"value":tax["tax_id"]},"PercentBased":True}}
            TaxLine.append(tax_line)
        qb_converted_json['TxnTaxDetail'] = {'TotalTax': bill_data['bill']['tax_total'],"TaxLine":TaxLine}

    items = []
    line_items = bill_data["bill"]['line_items']

    for item in line_items:
        LinkedTxn = []
        TaxCodeRef = {"value": item['tax_id']}
        ItemAccountRef= {"value": item["account_id"],"name": item["account_name"]}
        ItemBasedExpenseLineDetail = {'BillableStatus': item['is_billable'],'ItemRef': {"value": item['item_id'], "name": item['name']},'Qty': item["quantity"], 'UnitPrice': item["rate"],'ItemAccountRef':ItemAccountRef,'TaxCodeRef': TaxCodeRef}
        all_data_dict = {'Id': item["line_item_id"], 'Amount': item["item_total"], 'LineNum': item["line_item_id"],'ItemBasedExpenseLineDetail': ItemBasedExpenseLineDetail,'DetailType':'ItemBasedExpenseLineDetail','LinkedTxn': LinkedTxn}
        items.append(all_data_dict)
    if "tds_amount" in bill_data["bill"] and "tds_tax_id" in bill_data["bill"]:
        tds_line_item={"Amount":bill_data["bill"]["tds_amount"],"DetailType":"TDSLineDetail","TDSLineDetail":{"TDSSectionTypeId":bill_data["bill"]["tds_tax_id"]}}
        items.append(tds_line_item)

    qb_converted_json['Line'] = items
    # print("----------------converted json-------")
    # print(qb_converted_json)
    return qb_converted_json


# bills details method
def bill_details_method(zoho_org_id, bill_id, zoho_access_token):
    headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
    bill_transformed_data = {}
    bill_details_url = settings.ZOHO_BOOKS_API_URL + "/bills/{0}?organization_id={1}".format(bill_id,
                                                                                                    zoho_org_id)
    print("----------------------bill detail api----------------")
    print(bill_id, bill_details_url)
    bill_api_response = requests.get(bill_details_url, headers=headers)
    if bill_api_response.status_code == 200:
        bill_data = bill_api_response.json()
        bill_transformed_data = bill_mapping_func(bill_data)
    return bill_transformed_data, bill_api_response.status_code

def invoice_mapping_func(payload):
    qb_converted_json = {}
    for key in invoice_mapping:
        if key in payload["invoice"]:
            qb_converted_json[invoice_mapping[key]] = payload['invoice'][key]

    qb_converted_json['MetaData'] = {'CreateTime': payload['invoice']['created_time'],
                                     'LastUpdatedTime': payload['invoice']['last_modified_time']}
    qb_converted_json['DepartmentRef'] = {'value': payload["invoice"]['branch_id'],
                                          'name': payload["invoice"]['branch_name']}
    qb_converted_json['CurrencyRef'] = {'value': payload['invoice']['currency_id'],
                                        'name': payload['invoice']['currency_code']}
    # qb_converted_json['TxnTaxDetail'] = {'TotalTax': payload['invoice']['tax_total']}
    print(payload['invoice'])
    if "tax_total" in payload['invoice'] and "taxes" in payload['invoice'] :
        TaxLine=[]
        for tax in payload['invoice']["taxes"]:
            tax_id=""
            if "tax_id" in tax:
                tax_id=tax["tax_id"]
            elif "tax_name" in tax:
                tax_id=tax["tax_name"]
            tax_line={"Amount":tax["tax_amount"],"DetailType":"TaxLineDetail","TaxLineDetail":{"TaxRateRef":{"value":tax_id},"PercentBased":True}}
            TaxLine.append(tax_line)
        qb_converted_json['TxnTaxDetail'] = {'TotalTax': payload['invoice']['tax_total'],"TaxLine":TaxLine}

    qb_converted_json['CustomerRef'] = {'value': payload['invoice']['customer_id'],
                                        'name': payload['invoice']['customer_name']}
    qb_converted_json['ShipAddr'] = {'City': payload['invoice']['shipping_address']['city'],
                                     'Line1': payload['invoice']['shipping_address']['address'],
                                     'PostalCode': payload['invoice']['shipping_address']['zip']},
    qb_converted_json['BillAddr'] = {'Line1': payload['invoice']['billing_address']['street'],
                                     'Line2': payload['invoice']['billing_address']['street2'],
                                     'Line3': payload['invoice']['billing_address']['zip'],
                                     'Line4': payload['invoice']['billing_address']['city']},
    qb_converted_json['SalesTermRef'] = {'value': payload['invoice']['salesorder_id']}

    line_items = payload["invoice"]['line_items']
    items = []
    for item in line_items:
        TaxCodeRef = {"value": item['tax_id']}
        ItemAccountRef= {"value": item["account_id"],"name": item["account_name"]}
        # itemName=item['name']
        # if item["product_type"]=='service':
        #     itemName=item["description"]
        if item['name']:
            itemName=item["name"]
        else:
            itemName=item["description"]
        SalesItemLineDetail = {'DiscountAmt': item['discount'],'ItemRef': {"value": item['item_id'], "name": itemName},'Qty': item["quantity"], 'UnitPrice': item["rate"],'ItemAccountRef':ItemAccountRef,'TaxCodeRef': TaxCodeRef}
        all_data_dict = {'Id': item["line_item_id"], 'Amount': item["item_total"], 'LineNum': item["line_item_id"],'SalesItemLineDetail': SalesItemLineDetail,'DetailType':'SalesItemLineDetail'}
        items.append(all_data_dict)
    if "tds_amount" in payload["invoice"] and "tds_tax_id" in payload["invoice"]:
        tds_line_item={"Amount":payload["invoice"]["tds_amount"],"DetailType":"TDSLineDetail","TDSLineDetail":{"TDSSectionTypeId":payload["invoice"]["tds_tax_id"]}}
        items.append(tds_line_item)
    if "discount_total" in payload["invoice"]:
        discount_line_item={"Amount":payload["invoice"]["discount_total"],"DetailType": "DiscountLineDetail","DiscountLineDetail":{"PercentBased":False,"DiscountAccountRef":{"value":"","name":""}}}
        items.append(discount_line_item)
    qb_converted_json['Line'] = items
    return qb_converted_json


def invoice_details_method(zoho_org_id, invoice_id, zoho_access_token):
    headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
    invoice_transformed_data={}
    invoice_details_url = settings.ZOHO_BOOKS_API_URL + "/invoices/{0}?organization_id={1}".format(invoice_id,zoho_org_id)
    print("----------------------invoice detail api----------------")
    print(invoice_id,invoice_details_url)
    invoice_api_response = requests.get(invoice_details_url, headers=headers)
    if invoice_api_response.status_code==200:
        invoice_data = invoice_api_response.json()
        invoice_transformed_data=invoice_mapping_func(invoice_data)
    return invoice_transformed_data,invoice_api_response.status_code


def expense_mapping_func(payload):
    print("----expense mapping----")
    # print(payload["expense"])
    qb_converted_json = {}
    for key in expense_mapping:
        if key in payload["expense"]:
            qb_converted_json[expense_mapping[key]] = payload['expense'][key]

    qb_converted_json['MetaData'] = {'CreateTime': payload['expense']['created_time'],
                                     'LastUpdatedTime': payload['expense']['last_modified_time']}
    qb_converted_json['CurrencyRef'] = {'value': payload['expense']['currency_id'],
                                        'name': payload['expense']['currency_code']}
    qb_converted_json['AccountRef'] = {'value': payload['expense']['account_id'],
                                       'name': payload['expense']['account_name']}
    qb_converted_json['VendorRef'] = {'value': payload['expense']['vendor_id'],
                                       'name': payload['expense']['vendor_name']}
    items = []
    line_items = payload["expense"]['line_items']
    # print("-------------------------line items length---------------")
    # print(line_items)
    for item in line_items:
        # print(item)
        # print(payload["expense"]["account_name"].lower())
        TaxCodeRef = {"value": item['tax_id']}
        if payload["expense"]["account_name"].lower()=='itemized':
            ItemBasedExpenseLineDetail={'ItemRef': {"value": item['account_id'], "name": item['account_name']},'Qty': 1, 'UnitPrice': item["item_total"],'TaxCodeRef': TaxCodeRef}
            all_data_dict = {'Id': item["line_item_id"], 'Amount': item["item_total"], 'LineNum': item["line_item_id"],'ItemBasedExpenseLineDetail': ItemBasedExpenseLineDetail,'DetailType':'ItemBasedExpenseLineDetail'}
        else:
            AccountBasedExpenseLineDetail = {'AccountRef': {"value": item['account_id'], "name": item['account_name']},"BillableStatus":payload["expense"]["status"],'TaxCodeRef': TaxCodeRef}
            all_data_dict = {'Id': item["line_item_id"], 'Amount': item["item_total"], 'LineNum': item["line_item_id"],'AccountBasedExpenseLineDetail': AccountBasedExpenseLineDetail,'DetailType':'AccountBasedExpenseLineDetail'}

        items.append(all_data_dict)
    qb_converted_json['Line'] = items
    return qb_converted_json


def expense_details_method(zoho_org_id, expense_id, zoho_access_token):
    headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
    expense_transformed_data={}
    expense_details_url = settings.ZOHO_BOOKS_API_URL + "/expenses/{0}?organization_id={1}".format(expense_id,zoho_org_id)
    print("----------------------expense detail api----------------")
    print(expense_id,expense_details_url)
    expense_api_response = requests.get(expense_details_url, headers=headers)
    if expense_api_response.status_code==200:
        expense_data = expense_api_response.json()
        expense_transformed_data=expense_mapping_func(expense_data)
    return expense_transformed_data,expense_api_response.status_code


def journal_mapping_func(payload):
    qb_converted_json = {}
    for key in journal_mapping:
        if key in payload["journal"]:
            qb_converted_json[journal_mapping[key]] = payload['journal'][key]

    qb_converted_json['MetaData'] = {'CreateTime': payload['journal']['created_time'],
                                     'LastUpdatedTime': payload['journal']['last_modified_time']}
    qb_converted_json['CurrencyRef'] = {'value': payload['journal']['currency_id'],
                                        'name': payload['journal']['currency_code']}
    items = []
    line_items = payload["journal"]['line_items']
    for item in line_items:
        if item["debit_or_credit"]=='debit':
            PostingType="Debit"
        elif item["debit_or_credit"]=='credit':
            PostingType="Credit"
        JournalEntryLineDetail = {"PostingType":PostingType,"AccountRef": {"value": item["account_id"], "name": item["account_name"]}}
        all_data_dict = {'Id': item["line_id"], 'Amount': item["amount"], 'Description': item["description"],'DetailType': 'JournalEntryLineDetail','JournalEntryLineDetail': JournalEntryLineDetail}
        items.append(all_data_dict)

    qb_converted_json['Line'] = items

    return qb_converted_json



def journal_details_method(zoho_org_id, journal_id, zoho_access_token):
    headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
    journal_transformed_data={}
    journal_details_url = settings.ZOHO_BOOKS_API_URL + "/journals/{0}?organization_id={1}".format(journal_id,zoho_org_id)
    print("----------------------journal detail api----------------")
    print(journal_id,journal_details_url)
    journal_api_response = requests.get(journal_details_url, headers=headers)
    if journal_api_response.status_code==200:
        journal_data = journal_api_response.json()
        journal_transformed_data=journal_mapping_func(journal_data)
    return journal_transformed_data,journal_api_response.status_code



def billpayments_mapping_func(bill_payment_data):
    print("-------------------billpayments_mapping_func----------------------")
    # print(bill_payment_data)
    qb_converted_json = {}
    for key in bill_payment_mapping:
        if key in bill_payment_data['vendorpayment']:
            qb_converted_json[bill_payment_mapping[key]] = bill_payment_data['vendorpayment'][key]

    qb_converted_json['MetaData'] = {'CreateTime': bill_payment_data['vendorpayment']['created_time'],
                                     'LastUpdatedTime': bill_payment_data['vendorpayment']['last_modified_time']}
    bankAccountRef = {}
    if "paid_through_account_type" in bill_payment_data['vendorpayment'] and bill_payment_data['vendorpayment'][
        "paid_through_account_type"] == 'bank':
        bankAccountRef["name"] = bill_payment_data['vendorpayment']["paid_through_account_name"]
        bankAccountRef["value"] = bill_payment_data['vendorpayment']["paid_through_account_id"]

    qb_converted_json['CheckPayment'] = {'BankAccountRef': bankAccountRef,
                                         'PrintStatus': ''}
    qb_converted_json['CurrencyRef'] = {'value': bill_payment_data['vendorpayment']['currency_id'],
                                        'name': bill_payment_data['vendorpayment']['currency_code']}
    qb_converted_json['VendorRef'] = {'value': bill_payment_data['vendorpayment']['vendor_id'],
                                      'name': bill_payment_data['vendorpayment']['vendor_name']}

    line = []
    line_items = bill_payment_data['vendorpayment']['bills']

    for item in line_items:
        LinkedTxn = [{"TxnId": item['bill_id'], "TxnType": "Bill", "TxnDocNumber": item['bill_number']}]
        all_data_dict = {}
        all_data_dict['Amount'] = item["total"]
        all_data_dict["LinkedTxn"] = LinkedTxn
        line.append(all_data_dict)
    qb_converted_json['Line'] = line
    print("-------------------converted json---------------")
    print(qb_converted_json)
    return qb_converted_json


# billPayments_details_method
def billpayment_details_method(zoho_org_id, payment_id, zoho_access_token):
    headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
    payment_transformed_data={}
    bill_payment_details_url = settings.ZOHO_BOOKS_API_URL + "/vendorpayments/{0}?organization_id={1}".format(payment_id,zoho_org_id)
    print("----------------------bill payment detail api----------------")
    print(payment_id,bill_payment_details_url)
    bill_payment_details_response = requests.get(bill_payment_details_url, headers=headers)
    print(bill_payment_details_response)
    if bill_payment_details_response.status_code==200:
        bill_payment_data = bill_payment_details_response.json()
        payment_transformed_data = billpayments_mapping_func(bill_payment_data)
    return payment_transformed_data,bill_payment_details_response.status_code


def getZohoTransactionsInfo(zoho_org_id,params,trans_type,zoho_access_token):
    print("--------------------getZohoTransactionsInfo ----------",params)
    transformed_list=[]
    transaction_list=[]
    type=""
    sort_column=""
    page=1
    per_page=200
    def api_call(type, page, per_page, sort_column):
        api_list_url = settings.ZOHO_BOOKS_API_URL + "/" + type + "?page={0}&per_page={1}&sort_column={2}" \
                                                                         "&sort_order=A&organization_id={3}".format(
            page, per_page, sort_column, zoho_org_id)
        if "start_date" in params and "end_date" in params:
            api_list_url = api_list_url + "&date_start=" + params["start_date"] + "&date_end=" + params["end_date"]
        print("---------------------------------api call---------------------")
        print(api_list_url)
        print(zoho_access_token)
        auth_header = 'Bearer ' + zoho_access_token
        headers = {'Authorization': auth_header, 'accept': 'application/json'}
        r = requests.get(api_list_url, headers=headers)
        if r.status_code==200:
            api_response = json.loads(r.text)
            txns=api_response[type]
            for txn in txns:
                transaction_list.append(txn)
            if api_response["page_context"]["has_more_page"]:
                page=page+1
                api_call(type,page, per_page,sort_column) # call api to get next page transactions
        return transaction_list,r.status_code

    if zoho_access_token !=None:
        if trans_type=='Bill':
            bills,billstatus = api_call('bills',page, per_page,"date")
            print("***************************** bills ***********************************************")
            print(len(bills))
            if billstatus==200:
                for bill in bills:
                    bill_transformed_data,billdetailstatus = bill_details_method(zoho_org_id, bill['bill_id'], zoho_access_token)
                    if billdetailstatus==200:
                        transformed_list.append(bill_transformed_data)
            else:
                return "", billstatus, "Unable to pull bill data"

        if trans_type == 'BillPayment':
            payments, paymentstatus = api_call('vendorpayments', page, per_page, "date")
            print("***************************** payments ***********************************************")
            print(len(payments))
            if paymentstatus == 200:
                for payment in payments:
                    payment_transformed_data, paymentdetailstatus = billpayment_details_method(zoho_org_id,
                                                                                               payment['payment_id'],
                                                                                               zoho_access_token)
                    if paymentdetailstatus == 200:
                        transformed_list.append(payment_transformed_data)
            else:
                return "", paymentstatus, "Unable to pull bill payment data"

        if trans_type=='Invoice':
            invoices,invoicestatus = api_call('invoices',page, per_page,"date")
            print("***************************** invoices ***********************************************")
            print(len(invoices))
            if invoicestatus==200:
                for invoice in invoices:
                    invoice_transformed_data,invoicedetailstatus = invoice_details_method(zoho_org_id, invoice['invoice_id'], zoho_access_token)
                    if invoicedetailstatus==200:
                        transformed_list.append(invoice_transformed_data)
            else:
                return "", invoicestatus, "Unable to pull invoice data"

        if trans_type=='JournalEntry':
            journals,journalstatus = api_call('journals',page, per_page,"journal_date")
            print("***************************** journals ***********************************************")
            print(len(journals))
            if journalstatus==200:
                for journal in journals:
                    journal_transformed_data,journaldetailstatus = journal_details_method(zoho_org_id, journal['journal_id'], zoho_access_token)
                    if journaldetailstatus==200:
                        transformed_list.append(journal_transformed_data)
            else:
                return "", journalstatus, "Unable to pull journal data"

        if trans_type=='Purchase':
            expenses,expensestatus = api_call('expenses',page, per_page,"date")
            print("***************************** expenses ***********************************************")
            print(len(expenses))
            if expensestatus==200:
                for expense in expenses:
                    expense_transformed_data,expensedetailstatus = expense_details_method(zoho_org_id, expense['expense_id'], zoho_access_token)
                    if expensedetailstatus==200:
                        transformed_list.append(expense_transformed_data)
            else:
                return "", expensestatus, "Unable to pull expense data"

        return transformed_list,status.HTTP_200_OK,"success"

    else:
        return "", status.HTTP_401_UNAUTHORIZED, "No Access Token"

    return transformed_list

def getZohoOrganizationInfo(zoho_org_id,zoho_access_token):
    headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
    org_data = {}
    org_url = settings.ZOHO_BOOKS_API_URL + "/organizations/{0}".format(zoho_org_id)
    print(org_url)
    org_api_response = requests.get(org_url, headers=headers)
    if org_api_response.status_code == 200:
        org_data = org_api_response.json()
    return org_data,org_api_response.status_code


def pull_zoho_PL_Detail(report_id,cust_id,from_date,to_date):
    report=Report.objects.get(id=report_id)
    outlet=report.outlet
    outlet_id=outlet["id"]
    dept_id=outlet["dept_id"]
    print(outlet_id)
    headers = {'Accept': 'application/json', 'accept': 'application/json'}
    apiUrl = settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + "/api/entities/le_ot_link/getFromData?"+"id="+outlet_id
    leg=requests.get(apiUrl,headers=headers,timeout = 30)
    print(leg.text)
    if leg.status_code==200:
        result_data = json.loads(leg.text).get("result",[])
        print("pull data zoho - result " + str(len(result_data)))
        if not result_data or len(result_data) == 0:
            error_msg = "No legal entity data found for outlet_id :" + str(outlet_id) + ". Please check your outlet configuration."
            print("Error: " + str(error_msg))
            return {"status" : 400, "message" : error_msg, "error_type":"no_data"}
        le_data=result_data[0]
        print("SUCCESS: found legal entity")
        zoho_org_id=le_data["qb_id"]
        zoho_refresh_token=le_data["qb_refreshtoken"]
        headers = {'Accept': 'application/json', 'accept': 'application/json'}
        apiUrl = settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.CUSTOMER_GET_API_URL
        apiUrl=apiUrl+"?id="+cust_id
        apiUrl=apiUrl+"&active=True"
        apiReq = requests.get(apiUrl, headers=headers)
        api_status_code = apiReq.status_code
        if api_status_code == 200:
            cust_json = json.loads(apiReq.text)['result']
            cust_json=cust_json[0]
            if(zoho_org_id!='' and zoho_refresh_token!=''):
                print("----------------------get_zoho_access_token---------------------")
                print(zoho_org_id,zoho_refresh_token)
                # zoho_client_id=cust_json["clientid"]
                # zoho_client_secret=cust_json["clientsecret"]
                zoho_client_id=settings.ZOHO_CLIENT_ID
                zoho_client_secret=settings.ZOHO_CLIENT_SECRET
                print(zoho_client_id,zoho_client_secret)
                zoho_access_token = get_zoho_access_token(zoho_refresh_token, zoho_client_id, zoho_client_secret)
                print("--------------------zoho access token----------------",zoho_access_token)
                rule=json.dumps({"columns":[{"index":1,"field":"branch_name","value":[dept_id],"comparator":"in","group":"branch"}],"criteria_string":"1"})
                pl_api_url=settings.ZOHO_BOOKS_API_URL + "/reports/profitandloss?organization_id={0}&filter_by=TransactionDate.CustomDate&from_date={1}&to_date={2}&rule={3}&sort_column=account_name&sort_order=A&is_response_new_flow=true".format(zoho_org_id,from_date,to_date,rule)
                print(pl_api_url)
                auth_header = 'Bearer ' + zoho_access_token
                headers = {'Authorization': auth_header, 'accept': 'application/json'}
                pl_api_response = requests.get(pl_api_url, headers=headers)
                print(pl_api_response.text)
                if pl_api_response.status_code==200:
                    pl_data = json.loads(pl_api_response.text)["profit_and_loss"]
                    child_nodes=[]
                    def getChildNodeTxns(data):
                        for acc in data["accounts"]:
                            print(acc["has_child"])
                            if acc["has_child"]==True:
                                getChildNodeTxns(acc)
                            else:
                                if "account_id" in acc:
                                    child_nodes.append(acc["account_id"])
                                    ledger_api_url=settings.ZOHO_BOOKS_API_URL + "/reports/generalledgerdetails?organization_id={0}".format(zoho_org_id)
                                    ledger_group_by=json.dumps([{"field":"account_name","group":"report"}])
                                    ledger_rule=json.dumps({"columns":[{"index":1,"field":"account_id","value":[acc["account_id"]],"comparator":"in","group":"report"},{"index":2,"field":"branch_name","value":[dept_id],"comparator":"in","group":"branch"}],"criteria_string":"( 1 AND 2 )"})
                                    ledger_api_params={"filter_by":"TransactionDate.CustomDate","from_date":from_date,"to_date":to_date,"group_by":ledger_group_by,"rule":ledger_rule,"show_sub_account":False}
                                    ledger_res_type="account_transactions"
                                    ledger_sort_column="date"
                                    ledger_details_data,ledger_responsestatus=zohoAPIRequest(ledger_api_url,ledger_api_params,ledger_res_type,ledger_sort_column,zoho_access_token)
                                    # print("--------------------ledger_details_data----------------------")
                                    # print(ledger_details_data)
                                    # print("--------------------ledger_details_data----------------------")
                                    acc["accounts"]=ledger_details_data[0]["account_transactions"]
                    getChildNodeTxns(pl_data)
                    print("---------------child_nodes----------------")
                    print(len(child_nodes))
                    # print("=============================================================================================")
                    # print(pl_data)
                    # print("=============================================================================================")
                    # input_api={'profit_and_loss':pl_data}
                    input_api=pl_data
                    # report=Report.objects.get(id=report_id)
                    # report.input_api=input_api
                    # report.save()
                    response = {'status': 200, 'message': 'PL API Detail Pulled'}
                    return response,input_api
                else:

                    response = {'status': pl_api_response.status_code, 'message': 'Unable to pull PL API Detail'}
                    return response,{}

            else:
                response = {'status': 400, 'message': 'Zoho organisation id or refresh token is empty'}
                return response,{}
        else:
            response = {'status': api_status_code, 'message': 'Unable to get Customer Detail'}
            return response,{}
    else:
        response = {'status': leg.status_code, 'message': 'Unable to get Legalentity Detail'}
        return response,{}

@shared_task
def update_report_status(report_id):
    report=Report.objects.get(id=report_id)
    report.status="Review"
    report.save()

@shared_task
def pull_zoho_PL_particulars_api(report_id):
    report=Report.objects.get(id=report_id)
    outlet=report.outlet
    outlet_id=outlet["id"]
    dept_id=outlet["dept_id"]
    print(outlet_id)
    customer=report.customer
    cust_id=customer["id"]
    headers = {'Accept': 'application/json', 'accept': 'application/json'}
    apiUrl = settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + "/api/entities/le_ot_link/getFromData?"+"id="+outlet_id
    leg=requests.get(apiUrl,headers=headers)
    print(leg.text)
    if leg.status_code==200:
        result_data = json.loads(leg.text).get("result",[])
        print(" pull zoho data: result data: " + str(len(result_data)))
        if not result_data or len(result_data) ==0 :
           error_msg = "No legal entity data found. Try again"
           print("Error: " + str(error_msg))
           return {"status":400,"message": error_msg, "error_type":"no_data"}
        le_data= result_data[0]
        print(" SUCCESS: pull zoho - found legal entity")
        zoho_org_id=le_data["qb_id"]
        zoho_refresh_token=le_data["qb_refreshtoken"]
        headers = {'Accept': 'application/json', 'accept': 'application/json'}
        apiUrl = settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.CUSTOMER_GET_API_URL
        apiUrl=apiUrl+"?id="+cust_id
        apiUrl=apiUrl+"&active=True"
        apiReq = requests.get(apiUrl, headers=headers)
        api_status_code = apiReq.status_code
        if api_status_code == 200:
            cust_json = json.loads(apiReq.text)['result']
            cust_json=cust_json[0]
            if(zoho_org_id!='' and zoho_refresh_token!=''):
                print("----------------------get_zoho_access_token---------------------")
                print(zoho_org_id,zoho_refresh_token)
                # zoho_client_id=cust_json["clientid"]
                # zoho_client_secret=cust_json["clientsecret"]
                zoho_client_id=settings.ZOHO_CLIENT_ID
                zoho_client_secret=settings.ZOHO_CLIENT_SECRET
                print(zoho_client_id,zoho_client_secret)
                zoho_access_token = get_zoho_access_token(zoho_refresh_token, zoho_client_id, zoho_client_secret)
                invoice_list=[]
                bill_list=[]
                journal_list=[]
                expense_list=[]
                values={
                    "values":[]
                }
                d = datetime.now().astimezone(timezone('Asia/Kolkata'))
                day="1"
                pdflink=""
                excellink=""
                print("pdf attachments")
                pdf = report.pdf_attachments.all()

                if len(pdf) >0 :
                    pdflink=pdf[len(pdf)-1].document_link
                print(pdflink)
                print("excel attachments")
                excel = report.excel_attachments.all()
                print(len(excel))
                if len(excel) >0 :
                    excellink=excel[len(excel)-1].document_link
                print(excellink)
                month=report.month
                year=report.year
                version=report.version
                generated_at=report.generated_at
                qb_api=report.qb_api
                report_type=report.report_type
                notes={}
                if(report.comments!=None):
                    notes=report.comments

                # IDExtactor(response,sales_list,bill_list,invoice_list,deposit_list)

                details=report.details
                if("values" in details):
                    if("invoice_list" in details["values"]):
                        invoice_list=list(set(details["values"]["invoice_list"]))
                    if("bill_list" in details["values"]):
                        bill_list=list(set(details["values"]["bill_list"]))
                    if("expense_list" in details["values"]):
                        expense_list=list(set(details["values"]["expense_list"]))
                    if("journal_list" in details["values"]):
                        journal_list=list(set(details["values"]["journal_list"]))
                    json_file_path="/mnt/fcsharedata/PL_Details/"
                    print(report.customer["name"])
                    print(report.outlet["name"])
                    entity=str(report.customer["name"])+"_"+str(report.outlet["name"])
                    # print(entity)
                    print(str(report.year))
                    print(str(report.month))
                    json_file_path=json_file_path+str(report.year)+"_"+str(report.month)+"_"+entity+"_"+"details.json"
                    print(json_file_path)
                    details={
                        "details":json_file_path
                    }
                    report.details=details
                    report.save()
                    print(invoice_list)
                    invoice_apis=[]
                    sales_apis=[]
                    deposit_apis=[]
                    bill_apis=[]
                    expense_apis=[]
                    journal_apis=[]
                    for t in range(len(bill_list)):
                        nid=bill_list[t]
                        bill_transformed_data,stas=bill_details_method(zoho_org_id, nid, zoho_access_token)
                        val={"Bill":bill_transformed_data}
                        if(stas == 200):
                            bill_apis.append({
                                "id":nid,
                                "value":val
                            })

                    for t in range(len(invoice_list)):
                        nid=invoice_list[t]
                        invoice_transformed_data,stas=invoice_details_method(zoho_org_id, nid, zoho_access_token)
                        val={"Invoice":invoice_transformed_data}
                        if(stas == 200):
                            invoice_apis.append({
                                "id":nid,
                                "value":val
                            })

                    for t in range(len(expense_list)):
                        nid=expense_list[t]
                        expense_transformed_data,stas=expense_details_method(zoho_org_id,nid,zoho_access_token)
                        val={"Purchase":expense_transformed_data}
                        if(stas == 200):
                            expense_apis.append({
                                "id":nid,
                                "value":val
                            })
                    # print(journal_list)

                    for t in range(len(journal_list)):
                        nid=journal_list[t]
                        journal_transformed_data,stas=journal_details_method(zoho_org_id,nid,zoho_access_token)
                        val={"JournalEntry":journal_transformed_data}
                        if(stas == 200):
                            journal_apis.append({
                                "id":nid,
                                "value":val
                            })

                    data={
                        "invoice_list":invoice_apis,
                        "bill_list":bill_apis,
                        "expense_list":expense_apis,
                        "deposit_list":deposit_apis,
                        "sales_list":sales_apis,
                        "journal_list":journal_apis
                    }
                    try:

                        data=json.loads(json.dumps(data))
                        with open(json_file_path, 'w') as f:
                            json.dump(data, f)

                        # report=Report.objects.get(id=report_id)
                        details={
                            "details":json_file_path
                        }
                        print("Report Details attached")

                        # report.save()
                        # print("Hey its done")
                    except Exception as e:
                        print(e)
                        raise(e)

                reportEntity=None
                try:
                    if (report.brand!=None):
                        reportEntity = report.brand["id"]
                    elif (report.outlet!=None):
                        reportEntity = report.outlet["id"]
                    elif (report.legalentity!=None):
                        reportEntity = report.legalentity["id"]
                    elif(report.customer!=None):
                        reportEntity = report.customer["id"]
                except Exception as e:
                    print(e)
                    raise(e)

                print("======================================details===========================")
                print(details)
                apiRes=insert_qb_transactions(entity=reportEntity,details=json.dumps(details))
                if apiRes.status_code != 200:
                    return "Failure", 200
                else:
                    update_report_status.apply_async(args=(report_id,),queue="qbapi")

            response = {'status': 400, 'message': 'Zoho organisation id or refresh token is empty'}
            return response,{}
        else:
            response = {'status': api_status_code, 'message': 'Unable to get Customer Detail'}
            return response,{}
    else:
        response = {'status': leg.status_code, 'message': 'Unable to get Legalentity Detail'}
        return response,{}

@shared_task
def pull_Zoho_CashFlow_Info(report_id, from_date, to_date):
    print("Inside pull cashflow Report", report_id)
    report = Report.objects.get(id=report_id)
    legalentity = report.legalentity
    le_id = legalentity["id"]
    headers = {'Accept': 'application/json', 'accept': 'application/json'}
    apiUrl = settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + "/api/entities/legalentity/get?"+"_id="+le_id
    leg = requests.get(apiUrl, headers=headers)
    print(leg.text)
    if leg.status_code==200:
        result_data = json.loads(leg.text).get("result",[])
        print("DEBUG : pull zoho cashflow : result data : " + str(len(result_data)))
        if not result_data or len(result_data) ==0 :
           error_msg = "No legal data found. Try again"
           print("ERROR:" + str(error_msg))
           return {"status":400, "message":error_msg, "error_type": "no_data"}
        le_data= result_data[0]
        print("SUCCESS: pull cashflow - Found legal entity data")
        zoho_org_id=le_data["qb_id"]
        zoho_refresh_token=le_data["qb_refreshtoken"]
        if(zoho_org_id!='' and zoho_refresh_token!=''):
            zoho_client_id=settings.ZOHO_CLIENT_ID
            zoho_client_secret=settings.ZOHO_CLIENT_SECRET
            print(zoho_client_id,zoho_client_secret)
            zoho_access_token = get_zoho_access_token(zoho_refresh_token, zoho_client_id, zoho_client_secret)
            print("--------------------zoho access token----------------",zoho_access_token)
            cpr_api_url=settings.ZOHO_BOOKS_API_URL + "/reports/cashflow?organization_id={0}&filter_by=TransactionDate.CustomDate&from_date={1}&to_date={2}&sort_column=name&sort_order=A&is_response_new_flow=true&is_new_flow=true".format(zoho_org_id,from_date,to_date)
            print(cpr_api_url)
            auth_header = 'Bearer ' + zoho_access_token
            headers = {'Authorization': auth_header, 'accept': 'application/json'}
            cpr_api_response = requests.get(cpr_api_url, headers=headers)
            print(cpr_api_response.text)
            if cpr_api_response.status_code==200:
                input_api = {}
                resp=json.loads(cpr_api_response.text)
                cash_detail = resp["cash_flow"]
                for d in range(len(cash_detail["accounts"])):
                    sub_dtl = cash_detail["accounts"][d]
                    if sub_dtl["node_name"] == "operating_activity":
                        if sub_dtl["has_child"]:
                            adjchildren = []
                            for acc in sub_dtl["accounts"]:
                                if acc["name"]=="Net Income":
                                    input_api["profitloss"] = {"name": "Profit/ Loss","value": acc["values"][0]["total"]}
                                else:
                                    if acc["has_child"]:
                                        for super_sub in acc["accounts"]:
                                                adjchildren.append({"id": super_sub["account_id"],"name": super_sub["name"],"value": super_sub["values"][0]["total"]})
                                    else:
                                        adjchildren.append({"id": acc["account_id"],"name": acc["name"],"value": acc["values"][0]["total"]})
                            input_api["adjustments"] = {"name": "Adjustments (Non cash)","value": sub_dtl["values"][0]["total_sub_account"],"children": adjchildren}

                    if sub_dtl["node_name"] == "investing_activity":
                        if sub_dtl["has_child"]:
                            invtchildren = []
                            for acc in sub_dtl["accounts"]:
                                if acc["has_child"]:
                                    for super_sub in acc["accounts"]:
                                        invtchildren.append({"id": super_sub["account_id"],"name": super_sub["name"],"value": super_sub["values"][0]["total"]})
                                else:
                                    invtchildren.append({"id": acc["account_id"],"name": acc["name"],"value": acc["values"][0]["total"]})
                            input_api["investments"] = {"name": "Investments","value": sub_dtl["values"][0]["total_sub_account"],"children": invtchildren}
                    if sub_dtl["node_name"] == "financial_activity":
                        if sub_dtl["has_child"]:
                            finchildren = []
                            for acc in sub_dtl["accounts"]:
                                if acc["has_child"]:
                                    for super_sub in acc["accounts"]:
                                        finchildren.append({"id": super_sub["account_id"],"name": super_sub["name"],"value": super_sub["values"][0]["total"]})
                                else:
                                    finchildren.append({"id": acc["account_id"],"name": acc["name"],"value": acc["values"][0]["total"]})
                            input_api["capitaldrawings"] = {"name": "Capital & drawings","value": sub_dtl["values"][0]["total_sub_account"],"children": finchildren}

                response = {'status': 200, 'message': 'Cash Flow Report Pulled'}
                return response, input_api
            else:
                response = {'status': cpr_api_response.status_code, 'message': 'Unable to pull Cash Flow API Detail'}
                return response,{}
        else:
            response = {'status': 400, 'message': 'Zoho organisation id or refresh token is empty'}
            return response,{}

    else:
        response = {'status': leg.status_code, 'message': 'Unable to get Legalentity Detail'}
        return response,{}
