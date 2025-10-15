# python specific imports

import requests

# django specific imports
from django.conf import settings

from rest_framework import status

# application specific imports
from Workspace.settings.base import ZOHO_ACCOUNTS_API_URL, ZOHO_BOOKS_API_URL, ZOHO_REDIRECT_URL, ZOHO_GRANT_TYPE, \
    EXPRESS_API_HOST, EXPRESS_API_PORT, CSRFTOKEN_API_URL
from .config import account_mapping, bill_mapping, bill_payment_mapping, invoice_mapping, items_map, \
    expense_mapping, tax_code_mapping, tax_rate_mapping, vendor_mapping, journal_mapping
from QbApplication.services import redis_instance
import json

client = requests.session()


def getTokenFromAuthCode(code, clientid, clientsecret):
    url = ZOHO_ACCOUNTS_API_URL + "/oauth/v2/token?code={0}&client_id={1}&client_secret={2}&redirect_uri={3}" \
                                  "&grant_type={4}".format(
        code, clientid, clientsecret, ZOHO_REDIRECT_URL, ZOHO_GRANT_TYPE)
    response = requests.post(url)
    bearer_raw = json.loads(response.text)
    return bearer_raw


# def update_refreshtoken(org_id, refresh_token, le_id):
#     print("Update refresh token")
#     headers = {'Accept': 'application/json', 'accept': 'application/json'}
#     getcsrf = client.get(EXPRESS_API_HOST + ":" + EXPRESS_API_PORT + CSRFTOKEN_API_URL)
#     apiRes = json.loads(getcsrf.text)
#     customerHeaders = {'Accept': 'application/json', 'accept': 'application/json',
#                        'x-csrf-token': apiRes["csrfToken"]}
#     legalentity_url = "/api/entities/legalentity/save"
#     print(le_id)
#     data = {
#         "id": le_id,
#         "qb_refreshtoken": refresh_token
#     }
#     les1 = client.post(EXPRESS_API_HOST + ":" + EXPRESS_API_PORT + legalentity_url,
#                        data=data, headers=customerHeaders)
#     print(les1.text)
#     return les1

def update_refreshtoken(client_id, refresh_token):
    print("Update refresh token")
    headers = {'Accept': 'application/json', 'accept': 'application/json'}
    getcsrf = client.get(EXPRESS_API_HOST + ":" + EXPRESS_API_PORT + CSRFTOKEN_API_URL)
    apiRes = json.loads(getcsrf.text)
    customerHeaders = {'Accept': 'application/json', 'accept': 'application/json',
                       'x-csrf-token': apiRes["csrfToken"]}
    zoho_auth_details_save_url = "/api/entities/zoho_auth_details/save"
    print(zoho_auth_details_save_url)
    data = {
        "clientid": client_id,
        "refresh_token": refresh_token
    }
    les1 = client.post(EXPRESS_API_HOST + ":" + EXPRESS_API_PORT + zoho_auth_details_save_url,
                       data=data, headers=customerHeaders)
    print(les1.text)
    return les1

#
# def updatesessions(access_token, refresh_token, org_id, le_id):
#     print("in updatesessions")
#     redis_instance.set(org_id, access_token)
#     update_refreshtoken(org_id, refresh_token, le_id)

def updatesessions(access_token, refresh_token, client_id):
    print("in updatesessions")
    # redis_instance.set(client_id, access_token)
    update_refreshtoken(client_id, refresh_token)


# getting access_token from refresh_token if previous access_token expired
def get_zoho_access_token(refresh_token, ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET):
    acc_token = ""
    url = ZOHO_ACCOUNTS_API_URL + "/oauth/v2/token?refresh_token={0}&client_id={1}&client_secret={2}" \
                                  "&redirect_uri={3}&grant_type={4}".format(
        refresh_token, ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REDIRECT_URL, 'refresh_token')
    print(url)
    response = requests.post(url).json()
    print("----------------get zoho access token --------------")
    print(response)
    acc_token = response['access_token']
    return acc_token


def Zoho_api_request(zoho_org_id, params, type, sort_column, filter_by, zoho_access_token):
    transaction_list = []
    page = 1
    per_page = 200
    print(zoho_access_token)

    def api_call(type, page, per_page, sort_column):
        api_list_url = ZOHO_BOOKS_API_URL + "/" + type + "?page={0}&per_page={1}&sort_column={2}" \
                                                                "&sort_order=A&organization_id={3}".format(page,
                                                                                                           per_page,
                                                                                                           sort_column,
                                                                                                           zoho_org_id)
        if type == "taxes":
            api_list_url = ZOHO_BOOKS_API_URL + "/settings/" + type + "?page={0}&per_page={1}&sort_column={2}" \
                                                                             "&sort_order=A&organization_id={3}".format(
                page, per_page, sort_column, zoho_org_id)

        if filter_by:
            api_list_url = api_list_url + "&filter_by=" + filter_by

        auth_header = 'Bearer ' + zoho_access_token
        headers = {'Authorization': auth_header, 'accept': 'application/json'}
        r = requests.get(api_list_url, headers=headers)
        if r.status_code == 200:
            api_response = json.loads(r.text)
            if type == 'vendors':
                txns = api_response['contacts']
            else:
                txns = api_response[type]
            for txn in txns:
                transaction_list.append(txn)
            if api_response["page_context"]["has_more_page"]:
                page = page + 1
                api_call(type, page, per_page, sort_column)
        return transaction_list, r.status_code

    if zoho_access_token:
        response, response_status_code = api_call(type, page, per_page, sort_column)
        print(response)
        return response, response_status_code
    else:
        return "", status.HTTP_401_UNAUTHORIZED


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
    qb_converted_json['TxnTaxDetail'] = {'TotalTax': payload['invoice']['tax_total']}
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
        items.append(
            {'SalesItemLineDetail': {'DiscountAmt': item["discount_amount"], 'ItemRef': {
                'value': item['salesorder_item_id'], 'name': item['name']}, 'ItemAccountRef': {
                'value': item['account_id'], 'name': item['account_name']}},
             'LineNum': item["line_item_id"], 'Amount': item["cost_amount"], 'DetailType': item["product_type"],
             'UnitPrice': item["rate"], 'Qty': item["quantity"]
             })
    qb_converted_json['Line'] = items
    return qb_converted_json


# invoice details api
def invoice_details_method(zoho_org_id, invoice_id, zoho_access_token, zoho_refresh_token,
                           zoho_client_id, zoho_client_secret):
    invoice_details_url = ZOHO_BOOKS_API_URL + "/invoices/{0}?" + zoho_org_id + "".format(invoice_id)
    if not zoho_access_token:
        zoho_access_token = get_zoho_access_token(zoho_refresh_token, zoho_client_id, zoho_client_secret)
    headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
    invoice_api_response = requests.get(invoice_details_url, headers=headers)
    invoice_data = invoice_api_response.json()
    response = invoice_mapping_func(invoice_data)
    return response


def process_invoice_list_data(data, zoho_org_id, zoho_refresh_token, zoho_client_id, zoho_client_secret):
    response = []
    invoice_list_url = data.json()
    invoices = invoice_list_url["invoices"]

    for obj_index in range(len(invoices)):
        invoice_data = invoice_details_method(zoho_org_id, invoices[obj_index]['invoice_id'],
                                              zoho_refresh_token, zoho_client_id, zoho_client_secret)
        response.append(invoice_data)

    return {"QueryResponse": {"Invoice": response}}


def bill_mapping_func(payload):
    qb_converted_json = {}
    for key in bill_mapping:
        if key in payload["bill"]:
            qb_converted_json[bill_mapping[key]] = payload['bill'][key]

    line_items = payload["bill"]['line_items']
    qb_converted_json['MetaData'] = {'CreateTime': payload['bill']['created_time'],
                                     'LastUpdatedTime': payload['bill']['last_modified_time']}
    qb_converted_json['DepartmentRef'] = {'value': payload['bill']['branch_id'],
                                          'name': payload['bill']['branch_name']}
    qb_converted_json['CurrencyRef'] = {'value': payload['bill']['currency_id'],
                                        'name': payload['bill']['currency_code']}
    qb_converted_json['VendorRef'] = {'value': payload["bill"]['vendor_id'],
                                      'name': payload["bill"]['vendor_name']}
    items = []
    for item in line_items:
        ItemBasedExpenseLineDetail = {'BillableStatus': item['is_billable'],
                                      'ItemRef': {"value": item['item_id'], "name": item['name']}}
        LinkedTxn = {"TxnId": item['tax_name'], "TxnType": item['tax_type']}
        TaxCodeRef = {"value": item['tax_exemption_code']}

        all_data_dict = {'Id': item["line_item_id"], 'Qty': item["quantity"], 'UnitPrice': item["rate"],
                         'TaxCodeRef': TaxCodeRef, 'Amount': item["item_total"], 'LineNum': item["line_item_id"],
                         'ItemBasedExpenseLineDetail': ItemBasedExpenseLineDetail, 'LinkedTxn': LinkedTxn}

        items.append(all_data_dict)

    qb_converted_json['Line'] = items

    return qb_converted_json

# bills details method
def bill_details_method(zoho_org_id, bill_id, zoho_access_token,zoho_refresh_token,zoho_client_id,zoho_client_secret):
    bill_details_url = ZOHO_BOOKS_API_URL + "/bills/{0}?" + zoho_org_id + "".format(bill_id)
    if not zoho_access_token:
        zoho_access_token = get_zoho_access_token(zoho_refresh_token, zoho_client_id, zoho_client_secret)
    headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
    bill_api_response = requests.get(bill_details_url, headers=headers)
    bill_data = bill_api_response.json()
    response = bill_mapping_func(bill_data)
    return response


def process_bills_list_data(data, zoho_org_id, zoho_access_token, zoho_refresh_token, zoho_client_id,
                            zoho_client_secret):
    try:
        bill_api_response = data.json()
    except:
        bill_api_response = data

    bills = bill_api_response["bills"]
    response = []
    for obj_index in range(len(bills)):
        bill_data = bill_details_method(zoho_org_id, bills[obj_index]['Id'], zoho_access_token, zoho_refresh_token,
                                        zoho_client_id, zoho_client_secret)

        response.append(bill_data)
    return {"QueryResponse": {"Bill": response}}


def billpayments_mapping_func(payload):
    vendorpayment_data = payload['vendorpayment']
    qb_converted_json = {}
    for key in bill_payment_mapping:
        if key in vendorpayment_data:
            qb_converted_json[bill_payment_mapping[key]] = vendorpayment_data[key]

    qb_converted_json['MetaData'] = {'CreateTime': vendorpayment_data['created_time'],
                                     'LastUpdatedTime': vendorpayment_data['last_modified_time']}
    qb_converted_json['CheckPayment'] = {'BankAccountRef': vendorpayment_data['check_details']['check_id'],
                                         'PrintStatus': vendorpayment_data['check_details']['check_status']}
    qb_converted_json['CurrencyRef'] = {'value': vendorpayment_data['currency_id'],
                                        'name': vendorpayment_data['currency_code']}
    qb_converted_json['VendorRef'] = {'value': vendorpayment_data['vendor_id'],
                                      'name': vendorpayment_data['vendor_name']}

    line = []
    line_items = vendorpayment_data['bills']

    for item in line_items:
        LinkedTxn = [{"TxnId": item['bill_id'], "TxnType": "Bill"}]

        all_data_dict = {'Amount': item["total"], "LinkedTxn": LinkedTxn}
        line.append(all_data_dict)
    qb_converted_json['Line'] = line

    return qb_converted_json


# billPayments_details_method
def billPayment_details_method(zoho_org_id, bill_id, zoho_access_token, zoho_refresh_token,
                               zoho_client_id, zoho_client_secret):
    bill_payment_details_url = ZOHO_BOOKS_API_URL + "/v3/bills/{0}/payments?" + zoho_org_id + "".format(bill_id)
    if not zoho_access_token:
        zoho_access_token = get_zoho_access_token(zoho_refresh_token, zoho_client_id, zoho_client_secret)
    headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
    bill_payment_details_url = requests.get(bill_payment_details_url, headers=headers)
    bill_payment_data = bill_payment_details_url.json()
    response = billpayments_mapping_func(bill_payment_data)
    return response


def process_billspayments_list_data(data, zoho_org_id, zoho_access_token, zoho_refresh_token, zoho_client_id,
                                    zoho_client_secret):
    try:
        bill_api_response = data.json()

    except:
        bill_api_response = data

    response = []
    vendorpayment_data = bill_api_response['vendorpayment']
    for obj_index in range(len(vendorpayment_data)):
        bill_payment_data = billPayment_details_method(zoho_org_id, vendorpayment_data[obj_index]['Id'],
                                                       zoho_access_token, zoho_refresh_token, zoho_client_id,
                                                       zoho_client_secret)
        response.append(bill_payment_data)
    return {"QueryResponse": {"BillPayment": response}}


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
        JournalEntryLineDetail = {"AccountRef": {
            "PostingType": {"value": item["account_id"], "name": item["account_name"]}}}

        all_data_dict = {'Id': item["line_id"], 'Amount': item["amount"], 'Description': item["description"],
                         'JournalEntryLineDetail': JournalEntryLineDetail}

        items.append(all_data_dict)
    qb_converted_json['Line'] = items

    return qb_converted_json


# journal details method
def journal_details_method(zoho_org_id, journal_id, zoho_access_token, zoho_refresh_token, zoho_client_id,
                           zoho_client_secret):
    journal_details_url = ZOHO_BOOKS_API_URL + "/journals/{0}?" + zoho_org_id + "".format(journal_id)
    if not zoho_access_token:
        zoho_access_token = get_zoho_access_token(zoho_refresh_token, zoho_client_id, zoho_client_secret)
    headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
    journal_details_url = requests.get(journal_details_url, headers=headers)
    journals_data = journal_details_url.json()
    response = journal_mapping_func(journals_data)
    return response


def process_journals_list_data(data, zoho_org_id, zoho_access_token, zoho_refresh_token, zoho_client_id,
                               zoho_client_secret):
    response = []
    journal_api_response = data.json()
    journals = journal_api_response["journals"]

    for obj_index in range(len(journals)):
        journals_data = journal_details_method(zoho_org_id, journals[obj_index]['journal_id'], zoho_access_token,
                                               zoho_refresh_token, zoho_client_id, zoho_client_secret)
        response.append(journals_data)

    return {"QueryResponse": {"JournalEntry": response}}


# expense details method
def expense_details_method(zoho_org_id, expense_id, zoho_access_token, zoho_refresh_token, zoho_client_id,
                           zoho_client_secret):
    expense_details_url = ZOHO_BOOKS_API_URL + "/expenses/{0}?" + zoho_org_id + "".format(expense_id)
    if not zoho_access_token:
        zoho_access_token = get_zoho_access_token(zoho_refresh_token, zoho_client_id, zoho_client_secret)
    headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
    expense_details_url = requests.get(expense_details_url, headers=headers)
    expense_data = expense_details_url.json()
    response = expense_mapping_func(expense_data)
    return response


def expense_mapping_func(payload):
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

    items = []
    line_items = payload["expense"]['line_items']

    for item in line_items:
        AccountBasedExpenseLineDetail = {"AccountRef": {"value": item["account_id"], "name": item["account_name"]}}

        all_data_dict = {'Id': item["item_id"], 'Amount': item["item_total"], 'UnitPrice': item["rate"],
                         'TaxCodeRef': item["tax_id"],
                         'AccountBasedExpenseLineDetail': AccountBasedExpenseLineDetail}

        items.append(all_data_dict)

    return qb_converted_json

def process_expense_list_data(data, zoho_org_id, zoho_access_token, zoho_refresh_token, zoho_client_id,
                              zoho_client_secret):
    response = []
    expenses_data = data.json()
    expenses = expenses_data["expenses"]

    for obj_index in range(len(expenses)):
        expense_data = expense_details_method(zoho_org_id, expenses[obj_index]['expense_id'], zoho_access_token,
                                              zoho_refresh_token, zoho_client_id, zoho_client_secret)
        response.append(expense_data)

    return {"QueryResponse": {"Purchase": response}}


def taxcode_mapping_func(payload):
    qb_converted_json = {}
    for key in tax_code_mapping:
        if 'tax_group' in payload and key in payload['tax_group']:
            qb_converted_json[tax_code_mapping[key]] = payload['tax_group'][key]

    return qb_converted_json

# taxcode details method
def tax_details_method(zoho_org_id, tax_id, zoho_access_token, zoho_refresh_token, zoho_client_id, zoho_client_secret):
    taxcode_details_url = ZOHO_BOOKS_API_URL + "/settings/taxgroups/{0}?organization_id=" + zoho_org_id + "".format(
        tax_id)
    if not zoho_access_token:
        zoho_access_token = get_zoho_access_token(zoho_refresh_token, zoho_client_id, zoho_client_secret)
    headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
    taxcode_details_url = requests.get(taxcode_details_url, headers=headers)
    taxcode_data = taxcode_details_url.json()
    response = taxcode_mapping_func(taxcode_data)
    return response


def process_taxcode_list_data(data, zoho_org_id, zoho_access_token, zoho_refresh_token, zoho_client_id,
                              zoho_client_secret):
    response = []
    tax_list_url = data.json()
    total_taxes = tax_list_url["taxes"]

    for obj_index in range(len(total_taxes)):
        taxcode_data = tax_details_method(zoho_org_id, total_taxes[obj_index]['tax_id'], zoho_access_token,
                                          zoho_refresh_token, zoho_client_id, zoho_client_secret)
        response.append(taxcode_data)

    return {"QueryResponse": {"TaxCode": response}}


def taxrate_mapping_func(payload):
    qb_converted_json = {}
    for key in tax_rate_mapping:
        if key in payload['tax']:
            qb_converted_json[tax_rate_mapping[key]] = payload['tax'][key]

    try:
        agent_ref = payload['tax']['tax_authority_id']
    except:
        agent_ref = ""
    qb_converted_json['AgencyRef'] = {'value': agent_ref}

    return qb_converted_json

# taxrate details method
def taxrate_details_method(zoho_org_id, taxrate_id, zoho_access_token, zoho_refresh_token, zoho_client_id,
                           zoho_client_secret):
    taxrate_details_url = ZOHO_BOOKS_API_URL + "/settings/taxes/{0}?organization_id={1}".format(taxrate_id,
                                                                                                       zoho_org_id)
    if not zoho_access_token:
        zoho_access_token = get_zoho_access_token(zoho_refresh_token, zoho_client_id, zoho_client_secret)
    headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
    taxrate_detail_api_response = requests.get(taxrate_details_url, headers=headers)
    taxrate_data = taxrate_detail_api_response.json()
    response = taxrate_mapping_func(taxrate_data)
    return response


def process_taxrate_list_data(taxrate_list_url, zoho_org_id, zoho_access_token, zoho_refresh_token, zoho_client_id,
                              zoho_client_secret):
    # total_taxes = taxrate_list_url["taxes"]
    response = []

    for obj_index in range(len(taxrate_list_url)):
        taxrate_data = taxrate_details_method(zoho_org_id, taxrate_list_url[obj_index]['tax_id'], zoho_access_token,
                                              zoho_refresh_token, zoho_client_id, zoho_client_secret)
        response.append(taxrate_data)
    return {"QueryResponse": {"TaxRate": response}}


def process_items_list_data(data):
    list_api_response = data
    # items = list_api_response["items"]
    response = []

    def items_mapping_func(payload):
        qb_converted_json = {}
        for key in items_map:
            if key in payload:
                qb_converted_json[items_map[key]] = payload[key]

        qb_converted_json['Active'] = payload['status']
        qb_converted_json['IncomeAccountRef'] = {'value': payload['account_id'],
                                                 'name': payload['account_name']}
        qb_converted_json['ExpenseAccountRef'] = {'value': payload['purchase_account_id'],
                                                  'name': payload['purchase_account_name']}
        qb_converted_json['MetaData'] = {'CreateTime': payload['created_time'],
                                         'LastUpdatedTime': payload['last_modified_time']
                                         }

        response.append(qb_converted_json)
        return response

    items_mapping_func(list_api_response["items"])
    return {"QueryResponse": {"Item": response}}


def process_vendor_list_data(data):
    response = []
    vendor_list_data = data

    def vendor_mapping_func(payload):
        for vendor in payload:
            qb_converted_json = {}
            for key in vendor_mapping:
                qb_converted_json[vendor_mapping[key]] = vendor[key]

            if qb_converted_json["Active"] == 'active':
                qb_converted_json["Active"] = "True"
            else:
                qb_converted_json["Active"] = "False"
            qb_converted_json['CurrencyRef'] = {"value": vendor['currency_id'],
                                                "name": vendor['currency_code']}
            qb_converted_json['MetaData'] = {"CreateTime": vendor['created_time'],
                                             "LastUpdatedTime": vendor['last_modified_time']}

            response.append(qb_converted_json)
        return response

    vendor_mapping_func(vendor_list_data)
    return {"QueryResponse": {"Vendor": response}}


def process_accounts_list_data(data):
    list_api_response = data
    response = []

    def account_mapping_func(payload):
        # print(payload)
        qb_converted_json = {}
        for key in account_mapping:
            if key in payload:
                qb_converted_json[account_mapping[key]] = payload[key]

        qb_converted_json['MetaData'] = {'CreateTime': payload['created_time'],
                                         'LastUpdatedTime': payload['last_modified_time']
                                         }

        response.append(qb_converted_json)
        return response

    account_mapping_func(list_api_response["chart_of_account"])
    return {"QueryResponse": {"Account": response}}


def getZohoVendorInfo(zoho_refresh_token, zoho_org_id, zoho_client_id, zoho_client_secret):
    zoho_access_token = get_zoho_access_token(zoho_refresh_token, zoho_client_id, zoho_client_secret)
    # transaction_list = []
    # sort_column = ""
    # page = 1
    # per_page = 200
    # def api_call(page, per_page, sort_column):
    #     vendor_list_url = ZOHO_BOOKS_API_URL + "/vendors?filter_by=Status.Active&page={0}&per_page={1}" \
    #                     "&sort_column={2}&sort_order=A&organization_id={3}".format(page, per_page,sort_column,zoho_org_id)
    #     print("---------------------------------api call---------------------")
    #     print(vendor_list_url)
    #     print(zoho_access_token)
    #     auth_header = 'Bearer ' + zoho_access_token
    #     headers = {'Authorization': auth_header, 'accept': 'application/json'}
    #     r = requests.get(vendor_list_url, headers=headers)
    #     if r.status_code==200:
    #         api_response = json.loads(r.text)
    #         txns=api_response["contacts"]
    #         for txn in txns:
    #             transaction_list.append(txn)
    #         if api_response["page_context"]["has_more_page"]:
    #             page=page+1
    #             api_call(page, per_page,sort_column) # call api to get next page transactions
    #     return transaction_list,r.status_code

    # if zoho_access_token != None:
    #     vendor_list_url = ZOHO_BOOKS_API_URL + "/vendors?filter_by=Status.Active&page={0}&per_page={1}" \
    #                                            "&sort_column={2}&sort_order=A&organization_id={3}".format(page,
    #                                                                                                       per_page,
    #                                                                                                       sort_column,
    #                                                                                                       zoho_org_id)
    #     vendors_list, vendorstatus = api_call(page, per_page, "created_time", vendor_list_url, "contacts",
    #                                           zoho_access_token)
    vendor_response, vendor_status = Zoho_api_request(zoho_org_id, {}, "vendors", "created_time", "Status.Active",
                                                      zoho_access_token)
    if vendor_status == 200:
        vendor_processed_data = process_vendor_list_data(vendor_response)
        print("++++++++++++++++++++++++++vendor processed data +++++++++++++++++++++++++++++++++++=")
        vendor_arr = vendor_processed_data["QueryResponse"]["Vendor"]
        return vendor_arr, vendor_status, "success"
    else:
        return vendor_response, vendor_status, vendor_status["message"]


def getZohoItemsInfo(zoho_refresh_token, zoho_org_id, zoho_client_id, zoho_client_secret):
    zoho_access_token = get_zoho_access_token(zoho_refresh_token, zoho_client_id, zoho_client_secret)
    items_list_data, items_status = Zoho_api_request(zoho_org_id, {}, "items", "hsn_or_sac", "Status.Active",
                                                     zoho_access_token)

    if items_status == 200:
        items_processed_data = process_items_list_data(items_list_data)
        print("++++++++++++++++++++++++++ Item processed data +++++++++++++++++++++++++++++++++++")
        items_arr = items_processed_data["QueryResponse"]["Item"]
        return items_arr, items_status, "success"
    else:
        return items_list_data, items_status, items_list_data["message"]


def getZohoAccountsInfo(zoho_refresh_token, zoho_org_id, zoho_client_id, zoho_client_secret):
    zoho_access_token = get_zoho_access_token(zoho_refresh_token, zoho_client_id, zoho_client_secret)
    accounts_list, accounts_status = Zoho_api_request(zoho_org_id, {}, "chartofaccounts", "account_type",
                                                      "AccountType.All", zoho_access_token)
    if accounts_status == 200:
        accounts_processed_data = process_accounts_list_data(accounts_list)
        print("++++++++++++++++++++++++++Accounts processed data +++++++++++++++++++++++++++++++++++=")
        accounts_arr = accounts_processed_data["QueryResponse"]["Account"]
        return accounts_arr, accounts_status, "success"
    else:
        return accounts_list, accounts_status, accounts_status["message"]

def getZohoTaxrateInfo(zoho_refresh_token, zoho_org_id, zoho_client_id, zoho_client_secret):
    zoho_access_token = get_zoho_access_token(zoho_refresh_token, zoho_client_id, zoho_client_secret)

    taxrate_list, taxrate_status = Zoho_api_request(zoho_org_id, {}, "taxes", "", "Taxes.Active", zoho_access_token)
    if taxrate_status == 200:
        taxrate_processed_data = process_taxrate_list_data(taxrate_list, zoho_org_id, zoho_access_token,
                                                           zoho_refresh_token, zoho_client_id,
                                                           zoho_client_secret)
        print("++++++++++++++++++++++++++Taxrate processed data +++++++++++++++++++++++++++++++++++=")
        taxrate_arr = taxrate_processed_data["QueryResponse"]["TaxRate"]
        return taxrate_arr, taxrate_status, "success"
    else:
        return taxrate_list, taxrate_status, "Error"

