import requests
from django.shortcuts import render
from django.http import HttpResponse,JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User,Group
from .models import *
from Workspace.utilities import *
from rest_framework.decorators import api_view
from .Serializer import *
from rest_framework.response import Response
from ReportManagement.choices import *
import json
from django.contrib.auth.models import Group
from Workspace.settings import *
# from ..Workspace.settings.development import *
from django.conf import settings



# Create your views here.


@login_required(login_url='/accounts/login')
#@user_passes_test(is_admin)
def add_customer1(request):
    print("+++++++++++++++++++++++++++++++++++++")
    print('Request looks like this - ')
    print("request ",request.POST)
    user=request.user
    # print("user>>>>>>>>>",request.user)
    if(user.groups.filter(name__in=['Admin','Manager']).exists()):
        if(request.method=="POST"):
            if "cust_info" not in request.POST:
                response = JsonResponse({'status': 'Invalid', 'message': 'Basic Info not provided',})
                response.status_code = 401
                return response
            if "cust_org_tree" not in request.POST:
                response = JsonResponse({'status': 'Invalid', 'message': 'Org Tree not provided',})
                response.status_code = 401
                return response
            if "cust_subscriptions" not in request.POST:

                response = JsonResponse({'status': 'Invalid', 'message': 'Subscriptions not provided',})
                response.status_code = 401
                return response
            else:
                cust_info=request.POST.get("cust_info")
                print("---cust_info---")
                print(cust_info)
                info=json.loads(cust_info)
                print(info)
                cust_subscriptions=request.POST.get("cust_subscriptions")
                sub=json.loads(cust_subscriptions)
                cust_org_tree=request.POST.get("cust_org_tree")
                tree=json.loads(cust_org_tree)
                ''' CSRF Token'''
                client = requests.session()
                csrfToken =settings.EXPRESS_API_HOST+":"+settings.EXPRESS_API_PORT+settings.CSRFTOKEN_API_URL
                headers= {'Accept': 'application/json','accept': 'application/json'}
                getcsrf = client.get(csrfToken)
                # print(getcsrf)
                api_status_code = getcsrf.status_code
                # print("status code")
                # print(api_status_code)
                apiRes = json.loads(getcsrf.text)
                # print("-------response-----")
                # print(apiRes)

                # Create user account
                # user = User.objects.create_user(username=info["username"], email=info["email"],
                #                                 password=info["password"])
                # user.save()
                # my_group = Group.objects.get(name='Customer')
                # my_group.user_set.add(user)


                # req = requests.post("http://localhost:3001/api/user/save",data=postdata,headers=headers)
                # api_status_code = req.status_code
                # print(api_status_code)
                # print("status code")






                #Create subscription first
                # s=Subscription(subscription=sub)
                # s.save()




                #onboading process
                # on=Onboarding()
                # on.save()

                # Create Customer
                # cust=Customer(user_account=user,onboarding=on,name=info["name"],address=info["address"])
                # cust.crm=User.objects.get(username=info["crm"])
                # cust.qc=User.objects.get(username=info["qc"])
                # cust.accountant=User.objects.get(username=info["accountant"])
                # cust.subscription=s
                # cust.save()

                '''customer API request'''
                customerHeaders = {'Accept': 'application/json', 'accept': 'application/json','x-csrf-token': apiRes["csrfToken"]}
                '''User API requests'''

                # role????
                usrpostdata = {
                    "username": info["username"],
                    "password": info["password"],
                    "email": info["email"],
                    "name": info["name"],
                    "owner": True,
                    "role": "owner",
                    "mobile": info["mobile"]
                }
                print("----UserData----")
                print(usrpostdata)
                usrReq = client.post(settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.USER_SAVE_API_URL,data=usrpostdata, headers=customerHeaders)
                print(usrReq.text)
                usrReq = json.loads(usrReq.text)
                exp_usr_id = usrReq["id"]
                accountant = User.objects.get(username=info["accountant"])
                qc = User.objects.get(username=info["qc"])
                crm = User.objects.get(username=info["crm"])
                Customerpostdata = {
                    "name" : info["name"],
                    "username": info["username"],
                    "subscription":cust_subscriptions,
                    "onboarding":"",
                    "crm" : crm.id,
                    "qc":qc.id,
                    "active": True,
                    "type": "customer",
                    "accountant": accountant.id
                }
                print("-----Customerpostdata----")
                print(Customerpostdata)
                customerReq = client.post(settings.EXPRESS_API_HOST+":"+settings.EXPRESS_API_PORT+settings.CUSTOMER_SAVE_API_URL, data=Customerpostdata, headers=customerHeaders)
                customerReq_api_status_code = customerReq.status_code
                print(customerReq.text)
                customerReq=json.loads(customerReq.text)
                exp_cust_id=customerReq["id"]
                usrentpostdata = {
                    'user_id': exp_usr_id,
                    'entity_id': exp_cust_id
                }
                usrentReq = client.post(settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.USR_ENT_SAVE_API_URL,data=usrentpostdata, headers=customerHeaders)
                print(usrentReq.text)
                usrentReq = json.loads(usrentReq.text)

                print(" customer id from express api : ",exp_cust_id)
                print("----customerReq status code----")

                '''LegalEntity API requests'''
                # legalentities=tree["legalentities"]
                lgs = tree["legalentities"]
                le_arr=[]
                out_arr=[]
                brand_arr=[]
                le_name_arr=[]
                out_name_arr=[]
                brand_name_arr=[]
                for i in range(len(lgs)):
                    lepostdata={
                        'name': lgs[i]["name"],
                        'gst' : lgs[i]["gst"],
                        'qb_id': lgs[i]["qb_id"],
                        'qb_refreshtoken':lgs[i]["qb_id"], #to be changed after discussing with chaitanya cto
                        'active' : True
                    }
                    leReq = client.post(settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.LEGALENTITY_SAVE_API_URL,data=lepostdata, headers=customerHeaders)
                    print(leReq.text)
                    leReq = json.loads(leReq.text)
                    exp_le_id = leReq["id"]
                    le_arr.append(exp_le_id)
                    le_name_arr.append(lgs[i]["name"])
                    culepostdata={
                        'customer_id':exp_cust_id,
                        'legalentity_id':exp_le_id
                    }
                    culeReq = client.post(settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.CU_LE_SAVE_API_URL,data=culepostdata, headers=customerHeaders)
                    print(culeReq.text)
                    culeReq = json.loads(culeReq.text)

                ots = tree["outlets"]
                for o in range(len(ots)):
                    otpostdata = {
                        'name': ots[o]["name"],
                        'branch': ots[o]["branch"],
                        'city': ots[o]["city"],
                        'active': True
                    }
                    otReq = client.post(
                        settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.OUTLET_SAVE_API_URL,
                        data=otpostdata, headers=customerHeaders)
                    print(otReq.text)
                    otReq = json.loads(otReq.text)
                    exp_ot_id = otReq["id"]
                    out_arr.append(exp_ot_id)
                    out_name_arr.append(ots[o]["name"])

                bds = tree["brands"]
                for b in range(len(bds)):
                    bpostdata = {
                        'name': bds[b]["name"],
                        'active': True
                    }
                    bReq = client.post(
                        settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.BRAND_SAVE_API_URL,
                        data=bpostdata, headers=customerHeaders)
                    print(bReq.text)
                    bReq = json.loads(bReq.text)
                    exp_b_id = bReq["id"]
                    brand_arr.append(exp_b_id)
                    brand_name_arr.append(bds[b]["name"])
                print(le_arr)
                print(out_arr)
                print(brand_arr)
                print(le_name_arr)
                print(out_name_arr)
                print(brand_name_arr)

                for o in range(len(ots)):
                    for c in ots[o]["connections"]:
                        print("le ot links-----")
                        print(o)
                        print(c)
                        leotpostdata = {
                            'legalentity_id': le_arr[c],
                            'outlet_id': out_arr[o]
                        }
                        leotReq = client.post(
                            settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.LE_OT_SAVE_API_URL,
                            data=leotpostdata, headers=customerHeaders)
                        print(leotReq.text)
                        leotReq = json.loads(leotReq.text)

                for b in range(len(bds)):
                    for c in bds[b]["connections"]:
                        otbpostdata = {
                            'outlet_id': out_arr[c],
                            'brand_id': brand_arr[b]
                        }
                        otbReq = client.post(
                            settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.OT_B_SAVE_API_URL,
                            data=otbpostdata, headers=customerHeaders)
                        print(otbReq.text)
                        otbReq = json.loads(otbReq.text)

                for s in range(len(sub)):
                    subs_arr=sub[s]["subscriptions"]
                    print
                    if(sub[s]["subscribe"] == True):
                        for e in range(len(subs_arr)):
                            print(subs_arr[e])
                            if(subs_arr[e]["subscribe"] == True):
                                outlet_name=subs_arr[e]["outlet"]
                                sub[s]["subscriptions"][e]["id"]=out_arr[out_name_arr.index(outlet_name)]

                print("sub after adding outlet ids")
                print(sub)
                Customerpostdata = {
                    "id": exp_cust_id,
                    "subscription": json.dumps(sub)
                    }
                print("-----Customerpostdata----")
                print(Customerpostdata)
                customerReq = client.post(settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.CUSTOMER_SAVE_API_URL,data=Customerpostdata, headers=customerHeaders)
                customerReq_api_status_code = customerReq.status_code
                print(customerReq.text)

                # LegalEntityHeaders = {'Accept': 'application/json', 'accept': 'application/json','x-csrf-token': apiRes["csrfToken"]}
                # print("-----legalentities----")
                # print(legalentities)
                # LegalEntityReq = client.post(settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.LEGALENTITY_SAVE_API_URL,data=Customerpostdata, headers=LegalEntityHeaders)
                # LegalEntityReq_api_status_code = LegalEntityReq.status_code
                # print(LegalEntityReq)
                # print("----LegalEntityReq status code----")

                '''Outlet API requests'''
                # outlets=tree["outlets"]
                # OutletHeaders = {'Accept': 'application/json', 'accept': 'application/json','x-csrf-token': apiRes["csrfToken"]}
                # print("-----outlets----")
                # print(outlets)
                # OutletReq = client.post(settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.CUSTOMER_SAVE_API_URL,data=Customerpostdata, headers=OutletHeaders)
                # OutletReq_api_status_code = OutletReq.status_code
                # print(OutletReq)
                # print("----OutletReq status code----")

                '''Brand API requests'''
                # brands=tree["brands"]
                # BrandHeaders = {'Accept': 'application/json', 'accept': 'application/json','x-csrf-token': apiRes["csrfToken"]}
                # print("-----brands----")
                # print(brands)
                # BrandReq = client.post(settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.CUSTOMER_SAVE_API_URL,data=Customerpostdata, headers=BrandHeaders)
                # BrandReq_api_status_code = BrandReq.status_code
                # print(BrandReq)
                # print("----BrandReq status code----")


                # ots=tree["outlets"]
                # print("Outlets are ")
                # print(ots)
                # bds=tree["brands"]

                # for i in range(len(lgs)):
                #     L=LegalEntity(customer=cust,name=lgs[i]["name"])
                #     if(lgs[i]["gst"] == ''):
                #         L.gst="not defined"
                #     else:
                #         L.gst=lgs[i]["gst"]
                #
                #     if(lgs[i]["qb_id"] == ''):
                #         L.qb_id="not defined"
                #     else:
                #         L.qb_id=lgs[i]["qb_id"]
                #     L.save()

                # for i in range(len(ots)):
                #     O=Outlet(name=ots[i]["name"])
                #     O.save()
                #     for c in ots[i]["connections"]:
                #         le= LegalEntity.objects.get(name = lgs[int(c)]["name"])
                #         O.legalentity.add(le)
                #         O.save()
                #
                # for i in range(len(bds)):
                #     B=Brand(name=bds[i]["name"])
                #     B.save()
                #     for c in bds[i]["connections"]:
                #         ot= Outlet.objects.get(name = ots[int(c)]["name"])
                #         B.outlet.add(ot)
                #         B.save()




                # print(on)

                #Create Tree

                response = JsonResponse({'status': 'Valid', 'message': 'Org Tree not provided',})
                response.status_code = 200
                return response
    else:
        result={
            "status":400,
            "logged":False,
        }
        return JsonResponse(result)

# @api_view(['GET'])
# @login_required(login_url='/accounts/login')
# @user_passes_test(is_manager)
# def get_customer(request,id):
#     if(request.method=="GET"):
#         customer=Customer.objects.get(id=id)
#         serializer = CustomerSerializer(customer)
#         data={
#             "customer":serializer.data
#         }
#         return Response(data)


# @api_view(['GET'])
# @login_required
# def admin_customer_list(request):
#     if request.user.groups.filter(name='Manager').exists():
#         customers=Customer.objects.all()
#         serializer = CustomerSerializer(customers, many=True)
#         data={
#             "customers":serializer.data
#         }
#         return Response(data)


# @api_view(['GET'])
# @login_required
# def customer_list(request,format=None):
#     print("Customer list called")
#     if request.method == 'GET':
#         name = request.GET.get('name')
#         # login_flag=request.GET.get('login_flag')
#         customers=[]
#         if(name==None):
#             if request.user.groups.filter(name='Accountant').exists():
#                 customers = Customer.objects.filter(accountant=request.user)
#             elif request.user.groups.filter(name='TeamLead').exists():
#                 customers = Customer.objects.filter(tl=request.user)
#             elif request.user.groups.filter(name='QC').exists():
#                 customers = Customer.objects.filter(qc=request.user)
#             elif request.user.groups.filter(name='CRM').exists():
#                 customers = Customer.objects.filter(crm=request.user)
#             elif request.user.groups.filter(name='Manager').exists():
#                 customers = Customer.objects.all()
#         else:
#             customers=Customer.objects.filter(name__icontains=name).filter(accountant=request.user)
#         serializer = CustomerSerializer(customers, many=True)
#         return Response(serializer.data)
#     elif request.method == 'POST':
#         message="Not Allowed"
#         return JsonResponse(message, status=400)


# @api_view(['GET'])
# @login_required
# def legalentity_list(request):
#     legalentities=LegalEntity.objects.all()
#     le=LegalEntitySerializer(legalentities,many=True)
#     return Response(le.data)


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
def get_master_onboarding(request):
    m_data=initialize_master_onboarding()
    return JsonResponse(m_data,status=200)


@api_view(['GET'])
@login_required
def get_process_onboarding(request):
    m_data=initialize_process_onboarding()
    return JsonResponse(m_data,status=200)


@login_required(login_url='/accounts/login')
@user_passes_test(is_manager)
def check_if_username_exists(request):
    if(request.method=="POST"):
        username=request.POST.get("emp_username")
        print(username)
        # user= User.objects.get(username=username)
        headers = {'Accept': 'application/json', 'accept': 'application/json'}
        apiUrl = settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.USER_GET_API_URL
        apiUrl = apiUrl + "?username=" + username
        print(apiUrl)
        apiReq = requests.get(apiUrl, headers=headers)
        api_status_code = apiReq.status_code
        if api_status_code == 200:
            user = json.loads(apiReq.text)['result']
            print(user)
            if (len(user) > 0):
                if (len(user) == 1):
                    response = JsonResponse({'status': 'false', 'message': 'User Exists'})
                    print("wassup?")
                    response.status_code = 200
                    return response
                else:
                    response = JsonResponse({'status': 'false', 'message': 'Multiple Users exist'})
                    print("wassup2?")
                    response.status_code = 200
                    return response

            else:
                response = JsonResponse({'status': 'true', 'message': 'User Does Not Exists'})
                response.status_code = 200
                return response

@login_required(login_url='/accounts/login')
@api_view(['GET'])
def get_myinfo(request):
    u=User.objects.get(username=request.user.username)
    user=UserSerializer(request.user)
    print(user.data)
    return Response(user.data)

@login_required(login_url='/accounts/login')
@user_passes_test(is_manager)
def check_if_email_exists(request):
    if(request.method=="POST"):
        email=request.POST.get("emp_email")
        # user= User.objects.get(email=email)
        headers = {'Accept': 'application/json', 'accept': 'application/json'}
        apiUrl = settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.USER_GET_API_URL
        apiUrl = apiUrl + "?email=" + email
        print(apiUrl)
        apiReq = requests.get(apiUrl, headers=headers)
        api_status_code = apiReq.status_code
        print(apiReq.text)
        if api_status_code == 200:
            user = json.loads(apiReq.text)['result']
            print(user)
            if (len(user) > 0):
                if (len(user) == 1):
                    response = JsonResponse({'status': 'false', 'message': 'User Exists'})
                    print("wassup?")
                    response.status_code = 200
                    return response
                else:
                    response = JsonResponse({'status': 'false', 'message': 'Multiple Users exist'})
                    print("wassup2?")
                    response.status_code = 200
                    return response

            else:
                response = JsonResponse({'status': 'true', 'message': 'User Does Not Exists'})
                response.status_code = 200
                return response





