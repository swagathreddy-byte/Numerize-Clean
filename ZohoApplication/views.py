#python specific imports
import requests
# import dotenv
import json

#django specific imports
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from django.shortcuts import render, redirect
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from datetime import datetime,date
from pytz import timezone

#application specific imports
from .services import process_invoice_list_data, process_accounts_list_data, process_bills_list_data, \
    process_billspayments_list_data, process_items_list_data, process_journals_list_data, process_expense_list_data, \
    process_taxcode_list_data, process_taxrate_list_data, getZohoVendorInfo, getTokenFromAuthCode, updatesessions, \
    process_vendor_list_data
from Workspace.settings.base import ZOHO_BOOKS_API_URL
from QbApplication.views import get_CSRF_token
from ThirdParty_APIManagement.models import QbEvent


#for both access_token and refresh_token
# def get_auth_tokens(request):
#     response = get_code(request.GET.get('code'),ZOHO_CLIENT_ID,ZOHO_CLIENT_SECRET)
#     env_file = dotenv.find_dotenv()
#     dotenv.load_dotenv(env_file)
#     dotenv.set_key(env_file, "ZOHO_REFRESH_TOKEN", response['refresh_token'])
#     dotenv.set_key(env_file, "ZOHO_ACCESS_TOKEN", response['access_token'])
#     result = {"response": response, "status": "200"}
#     return Response(result)


# ACCOUNTS List Api call(Key Mapping)
class ListAccounts(APIView):

    def get(self, request, format=None):
        zoho_org_id = request.GET.get('zoho_org_id')
        zoho_access_token = request.GET.get('zoho_access_token')

        account_list_url = ZOHO_BOOKS_API_URL + "/chartofaccounts?" + zoho_org_id
        headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
        account_list_data = requests.get(account_list_url, headers=headers)

        if account_list_data.status_code == 200:
            data = process_accounts_list_data(account_list_data, zoho_org_id, headers)  # calling function from service
            return Response({"data": data}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Your token got expired"}, status=status.HTTP_401_UNAUTHORIZED)


# BILL List Api call
class ListBills(APIView):

    def get(self, request, format=None):
        zoho_org_id = request.GET.get('zoho_org_id')
        zoho_access_token = request.GET.get('zoho_access_token')
        bill_list_url = ZOHO_BOOKS_API_URL + "/bills" + zoho_org_id
        headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
        bill_api_data = requests.get(bill_list_url, headers=headers)
        if bill_api_data.status_code == 200:
            data = process_bills_list_data(bill_api_data, zoho_org_id, headers)
            return Response({"data": data}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Your Token got expired!!!"}, status=status.HTTP_401_UNAUTHORIZED)


# BILL PAYMENT List Api call
class ListBillPayments(APIView):

    def get(self, request, format=None):
        zoho_org_id = request.GET.get('zoho_org_id')
        zoho_access_token = request.GET.get('zoho_access_token')

        bill_list_url = ZOHO_BOOKS_API_URL + "/vendorpayments?" + zoho_org_id
        headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
        bill_api_data = requests.get(bill_list_url, headers=headers)

        if bill_api_data.status_code == 200:
            data = process_billspayments_list_data(bill_api_data, zoho_org_id, headers)
            return Response({"data": data}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Your Token got expired!!!"}, status=status.HTTP_401_UNAUTHORIZED)


# INVOICE List API call
class ListInvoices(APIView):

    def get(self, request, format=None):
        zoho_org_id = request.GET.get('zoho_org_id')
        zoho_access_token = request.GET.get('zoho_access_token')

        invoice_list_url = ZOHO_BOOKS_API_URL + "/invoices?" + zoho_org_id
        headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
        invoice_list_data = requests.get(invoice_list_url, headers=headers)

        if invoice_list_data.status_code == 200:
            data = process_invoice_list_data(invoice_list_data, zoho_org_id, headers)
            return Response({"data": data}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Your Token got expired!!!"}, status=status.HTTP_401_UNAUTHORIZED)


# ITEMS List Api call
class ListItems(APIView):

    def get(self, request, format=None):
        zoho_org_id = request.GET.get('zoho_org_id')
        zoho_access_token = request.GET.get('zoho_access_token')

        get_items_url = ZOHO_BOOKS_API_URL + "/items?" + zoho_org_id
        headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
        items_list_data = requests.get(get_items_url, headers=headers)
        if items_list_data.status_code == 200:
            data = process_items_list_data(items_list_data, zoho_org_id, headers)
            return Response({"data": data}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Your Token got expired!!!"}, status=status.HTTP_401_UNAUTHORIZED)


# JOURNAL List Api call
class ListJournals(APIView):

    def get(self, request, format=None):
        zoho_org_id = request.GET.get('zoho_org_id')
        zoho_access_token = request.GET.get('zoho_access_token')

        journal_list_url = ZOHO_BOOKS_API_URL + "/journals?" + zoho_org_id
        headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
        journal_api_data = requests.get(journal_list_url, headers=headers)  # response object with status code

        if journal_api_data.status_code == 200:
            data = process_journals_list_data(journal_api_data, zoho_org_id, headers)
            return Response({"data": data}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Your Token got expired!!!"}, status=status.HTTP_401_UNAUTHORIZED)


# Expenses List Api call
class ListExpenses(APIView):

    def get(self, request, format=None):
        zoho_org_id = request.GET.get('zoho_org_id')
        zoho_access_token = request.GET.get('zoho_access_token')

        expense_list_url = ZOHO_BOOKS_API_URL + "/expenses?" + zoho_org_id
        headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
        expense_list_data = requests.get(expense_list_url, headers=headers)

        if expense_list_data.status_code == 200:
            data = process_expense_list_data(expense_list_data, zoho_org_id, headers)
            return Response({"data": data}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Your Token got expired!!!"}, status=status.HTTP_401_UNAUTHORIZED)


# TaxCode List APi call
class ListTaxcodes(APIView):

    def get(self, request, format=None):
        zoho_org_id = request.GET.get('zoho_org_id')
        zoho_access_token = request.GET.get('zoho_access_token')

        tax_list_url = ZOHO_BOOKS_API_URL + "/settings/taxes?" + zoho_org_id
        headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
        tax_list_data = requests.get(tax_list_url, headers=headers)
        if tax_list_data.status_code == 200:
            data = process_taxcode_list_data(tax_list_data, zoho_org_id, headers)
            return Response({"data": data}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Your Token got expired!!!"}, status=status.HTTP_401_UNAUTHORIZED)


# TaxRate List  Api Call
class ListTaxrates(APIView):

    def get(self, request, format=None):
        zoho_org_id = request.GET.get('zoho_org_id')
        zoho_access_token = request.GET.get('zoho_access_token')

        taxrate_list_url = ZOHO_BOOKS_API_URL + "/settings/taxes?" + zoho_org_id
        headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
        taxrate_list_data = requests.get(taxrate_list_url, headers=headers)

        if taxrate_list_data.status_code == 200:
            data = process_taxrate_list_data(taxrate_list_data, zoho_org_id, headers)
            return Response({"data": data}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Your Token got expired!!!"}, status=status.HTTP_401_UNAUTHORIZED)


# Vendor  List Api call
class ListVendors(APIView):

    def get(self, request, format=None):
        zoho_org_id = request.GET.get('zoho_org_id')
        zoho_access_token = request.GET.get('zoho_access_token')

        vendor_list_url = ZOHO_BOOKS_API_URL + "/vendors?filter_by=Status.Active&organization_id={0}".format(
            zoho_org_id)
        headers = {"Authorization": "Bearer {0}".format(zoho_access_token)}
        vendor_list_data = requests.get(vendor_list_url, headers=headers)

        if vendor_list_data.status_code == 200:
            data = process_vendor_list_data(vendor_list_data)
            return Response({"data": data}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Your Token got expired!!!"}, status=status.HTTP_401_UNAUTHORIZED)
        # response = getZohoVendorInfo(zoho_refresh_token, zoho_org_id, zoho_client_id, zoho_client_secret)
        # return response


class AuthCodeHandler(APIView):
    def get(self, request, format=None):
        print("Auth Code Handler")
        state = request.GET.get('state', None)
        # statearr=state.split("~")
        # state_csrftoken=statearr[0]
        # customer_id=statearr[1]
        state_csrftoken=state
        print("---state---",state);
        print("---state_csrftoken---",state_csrftoken);
        # print("---customer_id---",customer_id);
        CSRFToken=get_CSRF_token(request)
        print("---CSRFToken---",CSRFToken);
        error = request.GET.get('error', None)
        print("---error---",error);
        if error == 'access_denied':
            return redirect('ext_api:index')
        if state is None:
            return HttpResponseBadRequest()
        elif state_csrftoken != CSRFToken:  # validate against CSRF attacks
            return HttpResponse('Its a CSRF Attack', status=401)

        auth_code = request.GET.get('code', None)
        if auth_code is None:
            return HttpResponseBadRequest()

        print("-------auth_code-----------------")
        print(auth_code);
        crm=self.request.user
        print(crm)
        # crm1=User.objects.filter(groups__name='CRM').first()
        # print(crm1)
        # headers = {'Accept': 'application/json', 'accept': 'application/json'}
        # apiUrl = settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + "/api/entities/zoho_auth_details/get"
        # # apiUrl=apiUrl+"?id="+customer_id
        # # apiUrl=apiUrl+"&active=True"
        # print(apiUrl)
        # apiReq = requests.get(apiUrl, headers=headers)
        # api_status_code = apiReq.status_code
        # if api_status_code == 200:
        #     zoho_auth_json = json.loads(apiReq.text)['result']
        #     if len(zoho_auth_json)>0:
        #         zoho_auth_json=zoho_auth_json[0]
        #     else:
        #         return HttpResponse("Zoho Auth Details Not Found", status=500)
        # else:
        #     return HttpResponse("Zoho Auth Details Not Found", status=500)

        token_res=getTokenFromAuthCode(auth_code,settings.ZOHO_CLIENT_ID,settings.ZOHO_CLIENT_SECRET)
        # token_generated_at=datetime.now().astimezone(timezone('Asia/Kolkata'))
        print(token_res)
        if "error" in token_res:
            print(token_res["error"])
            return HttpResponse(token_res["error"], status=500)
        else:
            refresh_token =token_res['refresh_token']
            message="Succesfully accessed token"
            print(message)
            q=QbEvent(name="zoho_token",type="zoho_token",status=True,qb_id=settings.ZOHO_CLIENT_ID,legalentity={},crm=crm,message=message)
            q.save()
            print("Qb event saved")
            try:
                updatesessions(token_res['access_token'], token_res['refresh_token'], settings.ZOHO_CLIENT_ID)
            except Exception as e:
                print(e)
                return HttpResponse("Unable to update token", status=500)
            print("---updated sessions---")

            return render(request,"Qb/connected.html")

            # cust_le_apiUrl = settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.CUST_LE_GET_API_URL
            # cust_le_apiUrl = cust_le_apiUrl + "?id="+customer_id+"&active=True"
            # print(cust_le_apiUrl)
            # cust_le_apiReq = requests.get(cust_le_apiUrl, headers=headers)
            # cust_le_api_status_code = cust_le_apiReq.status_code
            # if cust_le_api_status_code == 200:
            #     legal_entities = json.loads(cust_le_apiReq.text)['result']
            #     print(legal_entities)
            #     for le in range(len(legal_entities)):
            #         q=QbEvent(name="zoho_token",type="zoho_token",status=True,qb_id=legal_entities[le]["qb_id"],legalentity={"id":legal_entities[le]["_id"],"name":legal_entities[le]["name"]},crm=crm,message=message)
            #         q.save()
            #         print("Qb event saved")
            #         try:
            #             updatesessions(token_res['access_token'], token_res['refresh_token'], legal_entities[le]["qb_id"],legal_entities[le]["_id"])
            #         except Exception as e:
            #             print(e)
            #             return HttpResponse("Unable to update token", status=500)
            #
            #     return redirect('/ext_api/connected/'+legal_entities[le]["qb_id"])

class AuthDetails(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, format=None):
        response={}
        authdetails=[]
        headers = {'Accept': 'application/json', 'accept': 'application/json'}
        apiUrl = settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + "/api/entities/zoho_auth_details/get?active=True"
        print(apiUrl)
        apiReq = requests.get(apiUrl, headers=headers)
        api_status_code = apiReq.status_code
        if api_status_code == 200:
            authdetails = json.loads(apiReq.text)['result']
            print(authdetails);

        response = JsonResponse({'result': authdetails})
        response.status_code = 200
        return response
