import urllib

from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError,JsonResponse
from django.conf import settings
import json
from ThirdParty_APIManagement import getDiscoveryDocument
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from ReportManagement.models import Report
from .tasks import *
from .models import *
from CustomerManagement.models import *
import redis
from .serializer import *
from rest_framework.decorators import api_view
from rest_framework.response import Response
import datetime
from pytz import timezone

from .services import (
    getCompanyInfo,
    getBearerTokenFromRefreshToken,
    getUserProfile,
    getBearerToken,
    getSecretKey,
    validateJWTToken,
    revokeToken,
)

redis_instance = redis.StrictRedis(host=settings.REDIS_HOST,port=settings.REDIS_PORT, db=0)

client=requests.session()

def getlegalentity(realmid):
    csrfToken =settings.EXPRESS_API_HOST+":"+settings.EXPRESS_API_PORT+settings.CSRFTOKEN_API_URL
    headers= {'Accept': 'application/json','accept': 'application/json'}
    getcsrf = client.get(csrfToken)
    apiRes = json.loads(getcsrf.text)
    customerHeaders = {'Accept': 'application/json', 'accept': 'application/json','x-csrf-token': apiRes["csrfToken"]}
    legalentity_url="/api/entities/legalentity/get?qb_id="+str(realmid)
    les = client.get(settings.EXPRESS_API_HOST+":"+settings.EXPRESS_API_PORT+legalentity_url, headers=customerHeaders)
    les=json.loads(les.text)
    les=les["result"]
    return {"values":les,"header":customerHeaders}

def update_qbtoken(realmid,qb_token):
    print("Update qb token")
    les=getlegalentity(realmid)
    print(les)
    legalentity_url="/api/entities/legalentity/save"
    data={
        "id":les["values"][0]["id"],
        "qb_refreshtoken":qb_token
    }
    les1 = client.post(settings.EXPRESS_API_HOST+":"+settings.EXPRESS_API_PORT+legalentity_url, data=data, headers=les["header"])
    print(les1.text)
    return les1

def insert_report(entity,day,month,year,report_type,version,created_at,modified_at,result):
    data={
        "entity":entity,
        "day": day,
        "month": month,
        "year": year,
        "report_type": report_type,
        "version":version,
        "created_at":created_at,
        "modified_at":modified_at,
        "result":result
    }
    csrfToken =settings.EXPRESS_API_HOST+":"+settings.EXPRESS_API_PORT+settings.CSRFTOKEN_API_URL
    headers= {'Accept': 'application/json','accept': 'application/json'}
    getcsrf = client.get(csrfToken)
    apiRes = json.loads(getcsrf.text)
    customerHeaders = {'Accept': 'application/json', 'accept': 'application/json','x-csrf-token': apiRes["csrfToken"]}
    url="/api/reports/save"
    les1 = client.post(settings.EXPRESS_API_HOST+":"+settings.EXPRESS_API_PORT+url, data=data, headers=customerHeaders)
    print(les1.text)
    rep_id=json.loads(les1.text)["id"]
    print(rep_id)
    data1={
        "entity":entity,
        "report": rep_id,
        "day": day,
        "month": month,
        "year": year,
        "report_type": report_type,
        "version":version,
    }
    url='/api/report_entities/save'
    les1 = client.post(settings.EXPRESS_API_HOST+":"+settings.EXPRESS_API_PORT+url, data=data1, headers=customerHeaders)
    return les1

def is_crm(user):
    if(user.groups.filter(name='CRM').exists()):
        return True
    else:
        return False

def check_realmid_valid(realmId):
    print("Check realmid valid")
    if(realmId!=''):
        try:
            le=getlegalentity(realmId)
            crm=User.objects.get(pk=4)
            if(len(le["values"])>1):
                raise ValueError("More than one value found")
            elif(len(le["values"])==0):
                raise TypeError("Empty array")
            else:
                print("Only one value found")
                refresh_token =le["values"][0]["qb_refreshtoken"]
                if(refresh_token == ''): #Refresh token empty
                    message="No token found. Please login and enable the Qb: " + realmId
                    print(message)
                    q=QbEvent(name="qb_token",type="qb_token",status=False,legalentity=le,crm=crm,qb_id=realmId,message=message)
                    q.save()
                    result={
                        "status":400,
                        "message":message

                    }
                    return result
                else: #Refresh token non empty
                    print("Ok! access token is found")
                    access_token=redis_instance.get(realmId)
                    if(access_token == None): #No access token
                        result=refreshTokenCall_Internal(realmId)
                        if(result["success"]): #Successfully got the new access token
                            access_token=redis_instance.get(realmId).decode()
                        else:
                            q=QbEvent(name="qb_token",type="qb_token",status=False,qb_id=realmId,crm=crm,message=result["message"])
                            q.save()
                            result={
                                "status":400,
                                "message":result["message"]
                            }
                            return result
                    else: #access token is present
                        access_token=access_token.decode()
                        message="Succesfully accessed token"
                        print(message)
                        q=QbEvent(name="qb_token",type="qb_token",status=True,qb_id=realmId,legalentity=le,crm=crm,message=message)
                        q.save()
                        message="Token found "+realmId

                        result={
                            "status":200,
                            "message":message
                        }
                        return result
        except TypeError: #No legal entity with the realmid
            crm=User.objects.filter(groups__name='CRM').first()
            message="Legal Entity not found - "+ realmId

            q=QbEvent(name="qb_qbid",type="qb_qbid",status=False,crm=crm,qb_id=realmId,message="Legal Entity not found")
            q.save()
            result={
                "status":400,
                "message":message
            }
            return result
        except ValueError: #Multiple legal entity with the realmid
            message="Qb ID is not unique - "+ realmId
            q=QbEvent(name="qb_qbid",type="qb_qbid",qb_id=realmId,status=False,crm=crm,message=message)
            q.save()
            result={
                "status":400,
                "message":message
            }
            return result
    else:
        result={
            "status":400,
            "message":"Empty realmid"

        }
        return result


@login_required
def updateSession(request, access_token, refresh_token, realmId, name=None):

    print("Update session ############################")
    print(realmId)
    if realmId is None or realmId == 'null':
        request.session['srefreshToken']=refresh_token
        request.session['saccessToken']=access_token
        request.session['realmId'] = None
        request.session['name'] = name
    else:
        les=getlegalentity(realmId)
        print(len(les["values"]))
        if(len(les["values"])==1):
            update_qbtoken(realmId,refresh_token)
            redis_instance.set(realmId, access_token)
            print("Seems like its done")

@login_required
def index(request):
    return render(request, 'index.html')

@login_required
def connectToQuickbooks(request):
    print("connect to Quickbooks called \n")
    url = getDiscoveryDocument.auth_endpoint
    params = {'scope': settings.ACCOUNTING_SCOPE, 'redirect_uri': settings.REDIRECT_URI,
              'response_type': 'code', 'state': get_CSRF_token(request), 'client_id': settings.CLIENT_ID}
    url += '?' + urllib.parse.urlencode(params)
    return redirect(url)

@login_required
def signInWithIntuit(request):
    print("Signin with Intuit called \n")
    url = getDiscoveryDocument.auth_endpoint
    scope = ' '.join(settings.OPENID_SCOPES)  # Scopes are required to be sent delimited by a space
    params = {'scope': scope, 'redirect_uri': settings.REDIRECT_URI,
              'response_type': 'code', 'state': get_CSRF_token(request), 'client_id': settings.CLIENT_ID}
    url += '?' + urllib.parse.urlencode(params)
    return redirect(url)

@login_required
def getAppNow(request):
    url = getDiscoveryDocument.auth_endpoint
    scope = ' '.join(settings.GET_APP_SCOPES)  # Scopes are required to be sent delimited by a space
    CSRFToken=get_CSRF_token(request)
    params = {'scope': scope, 'redirect_uri': settings.REDIRECT_URI,
              'response_type': 'code', 'state': CSRFToken, 'client_id': settings.CLIENT_ID}
    url += '?' + urllib.parse.urlencode(params)
    return redirect(url)

@login_required
def authCodeHandler(request):
    print("Auth Code Handler")
    state = request.GET.get('state', None)
    CSRFToken=get_CSRF_token(request)
    error = request.GET.get('error', None)
    if error == 'access_denied':
        return redirect('ext_api:index')
    if state is None:
        return HttpResponseBadRequest()
    elif state != CSRFToken:  # validate against CSRF attacks
        return HttpResponse('Its a CSRF Attack', status=401)

    auth_code = request.GET.get('code', None)
    if auth_code is None:
        return HttpResponseBadRequest()

    bearer = getBearerToken(auth_code)
    realmId = request.GET.get('realmId', None)
    if(realmId == 'null'):
        realmId=None
    if(realmId!='null'):
        # try:
        les=getlegalentity(realmId)
        print("realmid is not none")
        try:
            le=getlegalentity(realmId)
            crm=User.objects.get(pk=4)
            if(len(le["values"])>1):
                message="Qb ID is not unique - "+ realmId
                print(message)
                q=QbEvent(name="qb_qbid",type="qb_qbid",qb_id=realmId,status=False,crm=crm,message=message)
                q.save()
                result={
                    "status":400,
                    "message":message
                }
                return result
            elif(len(le["values"])==0):
                crm=User.objects.filter(groups__name='CRM').first()
                message="Legal Entity not found - "+ realmId
                print(message)
                q=QbEvent(name="qb_qbid",type="qb_qbid",status=False,crm=crm,qb_id=realmId,message="Legal Entity not found")
                q.save()
                result={
                    "status":400,
                    "message":message
                }
                return result
            else:
                # refresh_token =le["values"][0]["qb_refreshtoken"]
                crm=User.objects.get(pk=4)
                message="Succesfully accessed token"
                print(message)
                q=QbEvent(name="qb_token",type="qb_token",status=True,qb_id=realmId,legalentity={"id":le["values"][0]["id"],"name":le["values"][0]["name"]},crm=crm,message=message)
                q.save()
                print("Qb event saved")
                print(bearer)
                print(bearer.accessToken)
                print(bearer.refreshToken)
                try:
                    updateSession(request, bearer.accessToken, bearer.refreshToken, realmId)
                except:
                    print("There seems to be an error")

                if bearer.idToken is not None:
                    if not validateJWTToken(bearer.idToken):
                        return HttpResponse('JWT Validation failed. Please try signing in again.')
                    else:
                        return redirect('ext_api:connected',realmId=realmId)
                else:
                    return redirect('ext_api:connected',realmId=realmId)
        except:
            crm=User.objects.filter(groups__name='CRM').first()
            message="There seems to be an exception "+ realmId
            q=QbEvent(name="qb_qbid",type="qb_qbid",status=False,crm=crm,qb_id=realmId,message="Legal Entity not found")
            q.save()
            result={
                "status":400,
                "message":message
            }
            return result

@login_required
def is_connected(request):
    user=request.user
    if(user.groups.filter(name='CRM').exists()):
        if(request.method=="GET"):
            access_token = request.session.get('accessToken', None)
            if access_token is None:
                result={
                    "status":200,
                    "logged":False,

                }
                return JsonResponse(result)
            else:
                result={
                    "status":200,
                    "logged":True,

                }
                return JsonResponse(result)
    else:
        result={
            "status":400,
            "logged":False,
        }
        return JsonResponse(result)

@login_required
def connected(request,realmId):
    #Accounting scope
    if realmId is not None and realmId !='null':
        try:
            les=getlegalentity(realmId)
            refresh_token=les["values"][0]["qb_refreshtoken"]
            if(refresh_token!=''):
                return render(request,"Qb/connected.html")
        except Exception as e:
            print(e)
            return redirect('ext_api:getAppNow')
    else:#OpenID scope
        refresh_token = request.session.get('srefreshToken', None)
        access_token = request.session.get('saccessToken', None)
        if access_token is None:
            return HttpResponse('Your Bearer token has expired, please initiate Sign In With Intuit flow again')
    c={}
    if realmId is None:#OpenID scope
        user_profile_response, status_code = getUserProfile(access_token)
        if status_code >= 400:
            bearer = getBearerTokenFromRefreshToken(refresh_token)
            user_profile_response, status_code = getUserProfile(bearer.accessToken)
            updateSession(request, bearer.accessToken, bearer.refreshToken, request.session.get('realmId', None),
                          name=user_profile_response.get('givenName', None))

            if status_code >= 400:
                return HttpResponseServerError()
        c = {
            'first_name': user_profile_response.get('givenName', ' '),
            'connected': True,
        }
    else:#Accounting scope
        if request.session.get('name') is None:
            name = ''
        else:
            name = request.session.get('name')
        c = {
            'first_name': name,
            'connected':True,
            'realmId':realmId
        }

    return JsonResponse(c)

@login_required
def disconnect(request):
    access_token = request.session.get('saccessToken', None)
    refresh_token = request.session.get('srefreshToken',None)
    revoke_response = ''
    if access_token is not None:
        revoke_response = revokeToken(access_token)
    if refresh_token is not None:
        revoke_response = revokeToken(refresh_token)
    else:
        return HttpResponse('No accessToken or refreshToken found, Please connect again')
    # del request.session['csrfToken']
    # request.session.flush()
    return HttpResponse(revoke_response)

@login_required
def refreshTokenCall(request,realmId):
    # try:
    if(realmId !='0'):
        le=getlegalentity(realmId)
        refresh_token = le["values"][0]["qb_refreshtoken"]
        if refresh_token is None:
            return HttpResponse('Not authorized')
        bearer = getBearerTokenFromRefreshToken(refresh_token)
        if isinstance(bearer, str):
            return HttpResponse(bearer)
        else:
            ############################Submit refresh token#####################
            update_qbtoken(realmId,refresh_token)
            redis_instance.set(realmId, bearer.accessToken,ex=bearer.accessTokenExpiry)
            return HttpResponse("Success")
    else:
        refresh_token=request.session.get('srefreshToken')
        if refresh_token is None:
            return HttpResponse('Not authorized')
        bearer = getBearerTokenFromRefreshToken(refresh_token)

        if isinstance(bearer, str):
            return HttpResponse(bearer)
        else:
            request.session['srefreshToken']=bearer.refreshToken
            request.session['saccessToken']=bearer.accessToken
            return HttpResponse("Success")

def refreshTokenCall_Internal(realmId):
    le=getlegalentity(realmId)
    refresh_token = le["values"][0]["qb_refreshtoken"]
    if refresh_token is None:
        return HttpResponse('Not authorized')

    bearer = getBearerTokenFromRefreshToken(refresh_token)
    if isinstance(bearer, str):
        return HttpResponse(bearer)
    else:
        if('accessTokenExpiry' in bearer):
            le.qb_refreshtoken=refresh_token
            le.save()
            redis_instance.set(realmId, bearer.accessToken,ex=bearer.accessTokenExpiry)
            result={
                "success" : True,
                "message" : "Success"
            }
            return result
        else:
            message= "Failure to get access token for realmId:"+ realmId +", Legal entity is " +  le.name + " & The message from QB is "+ json.dumps(bearer) + " Did you initiate qb id?"
            result={
                "success" : False,
                "message" : message
            }
            return result

@api_view(['GET'])
@login_required
def qbevent_status(request,token):
    client = requests.session()
    csrfToken =settings.EXPRESS_API_HOST+":"+settings.EXPRESS_API_PORT+settings.CSRFTOKEN_API_URL
    headers= {'Accept': 'application/json','accept': 'application/json'}
    getcsrf = client.get(csrfToken)
    apiRes = json.loads(getcsrf.text)
    customerHeaders = {'Accept': 'application/json', 'accept': 'application/json','x-csrf-token': apiRes["csrfToken"]}
    les = client.get(settings.EXPRESS_API_HOST+":"+settings.EXPRESS_API_PORT+"/api/entities/legalentity/get?active=True", headers=customerHeaders)
    les=json.loads(les.text)
    les=les["result"]
    # id=les["id"]
    # les=LegalEntity.objects.all()
    qbevs=QbEvent.objects.none()
    qbevents=[]
    for i in range(len(les)):
        print(les[i]["id"])
        qbev=QbEvent.objects.filter(type=token).filter(legalentity__id=les[i]["id"]).order_by("-date").first()
        if(qbev!=None):
            qbevents.append(qbev)


    if(len(qbevents)>0):
        qbserializer=QBEventSerializer(qbevents,many=True)
        return Response(qbserializer.data)
    else:
        qbserializer=QBEventSerializer(qbevs,many=True)
        return Response(qbserializer.data)

@login_required
def GetPayables(request,initdate,finaldate,realmid):
    realmId=realmid
    #realmId = 193514846602714
    if(realmId!=''):
        value=check_realmid_valid(realmId)
        print(value)
        if(value["status"]==200):
            print("its a valid realmid with access token")
            le=getlegalentity(realmId)
            refresh_token =le["values"][0]["qb_refreshtoken"]
            # le=LegalEntity.objects.get(qb_id=realmId)
            # crm=le.customer.crm
            # refresh_token =le.qb_refreshtoken
            access_token=redis_instance.get(realmId).decode()
            # print(refresh_token)
            response, status_code = getPayablesInfo(access_token, realmId,initdate,finaldate)
            values=json.dumps(response)
            print(values)
            #report.qb_api=company_info_response
            #report.save()
            #pull_invoice_api.delay(reportid,custid,access_token)
            if status_code >= 400:
                # if call to QBO doesn't succeed then get a new bearer token from refresh token and try again
                bearer = getBearerTokenFromRefreshToken(refresh_token)
                updateSession(request, bearer.accessToken, bearer.refreshToken, realmId)
                access_token=redis_instance.get(realmId).decode()
                response, status_code = getPayablesInfo(access_token, realmId,initdate,finaldate)
                values=json.dumps(response)
                print(response)
                if status_code >= 400:
                    message="Get Payables Info unable to get the required information, Qb id is  " + realmId
                    crm=User.objects.filter(groups__name='CRM').first()
                    q=QbEvent(name="qb_payables",type="qb_payables",qb_id=realmId, status=False,crm=crm,legalentity=le,message=message)
                    q.save()
                    result={
                        "status":400,
                        "message": message
                    }
                    return JsonResponse(result)

            # cust=le.customer
            d = datetime.datetime.now().astimezone(timezone('Asia/Kolkata'))
            print(json.loads(values))
            print(le["values"][0]["id"])
            c=insert_report(entity=str(le["values"][0]["id"]),day=d.day,month=d.month,year=d.year,report_type="Payables",version=1.0,created_at=d.strftime("%m/%d/%Y, %H:%M:%S"),modified_at=d.strftime("%m/%d/%Y, %H:%M:%S"),result=values)
            print(c)
            #p=Payables(customer=cust,legalentity=le,day=d.day,month=d.month,year=d.year,results=json.loads(values))
            #p.save()
            #company_name = company_info_response['CompanyInfo']['CompanyName']
            #address = company_info_response['CompanyInfo']['CompanyAddr']
            crm=User.objects.filter(groups__name='CRM').first()
            message="Successfully accessed Payables Info, Qb id is  " + realmId
            q=QbEvent(name="qb_payables",type="qb_payables",qb_id=realmId,status=True,crm=crm,legalentity=le,message=message)
            q.save()
            result={
                "status":200,
                "message": message
            }
            return JsonResponse(result)

        elif(value["status"]==400):
            result={
                "status":400,
                "message":value["message"]
            }
        return JsonResponse(result)

    else:
        result={
            "status":400,
            "message":"Empty realmid"
        }
        return JsonResponse(result)

@login_required
def GetReceivables(request,initdate,finaldate,realmid):
    realmId=realmid
    if(realmId!=''):
        value=check_realmid_valid(realmId)
        print(value)
        if(value["status"]==200):
            print("its a valid realmid with access token")
            le=getlegalentity(realmId)
            refresh_token =le["values"][0]["qb_refreshtoken"]
            access_token=redis_instance.get(realmId).decode()
            response, status_code = getReceivablesInfo(access_token, realmId,initdate,finaldate)
            values=json.dumps(response)
            if status_code >= 400:
                # if call to QBO doesn't succeed then get a new bearer token from refresh token and try again
                bearer = getBearerTokenFromRefreshToken(refresh_token)
                updateSession(request, bearer.accessToken, bearer.refreshToken, realmId)
                access_token=redis_instance.get(realmId).decode()
                response, status_code = getReceivablesInfo(access_token, realmId,initdate,finaldate)
                values=json.dumps(response)
                print(response)
                if status_code >= 400:
                    message="Get Receivables Info unable to get the required information, Qb id is  " + realmId
                    crm=User.objects.filter(groups__name='CRM').first()
                    q=QbEvent(name="qb_receivables",type="qb_receivables",qb_id=realmId,status=False,crm=crm,legalentity=le,message=message)
                    q.save()
                    result={
                        "status":400,
                        "message": message

                    }
                    return JsonResponse(result)

            # cust=le.customer
            d = datetime.datetime.now().astimezone(timezone('Asia/Kolkata'))
            print(json.loads(values))
            print(le["values"][0]["id"])
            c=insert_report(entity=str(le["values"][0]["id"]),day=d.day,month=d.month,year=d.year,report_type="Receivables",version=1.0,created_at=d.strftime("%m/%d/%Y, %H:%M:%S"),modified_at=d.strftime("%m/%d/%Y, %H:%M:%S"),result=values)
            print(c)
            crm=User.objects.filter(groups__name='CRM').first()
            message="Successfully accessed Receivables Info, Qb id is  " + realmId
            q=QbEvent(name="qb_receivables",type="qb_receivables",qb_id=realmId,status=True,crm=crm,legalentity=le,message=message)
            q.save()
            result={
                "status":200,
                "message": message
            }
            return JsonResponse(result)

        elif(value["status"]==400):
            result={
                "status":400,
                "message":value["message"]
            }
        return JsonResponse(result)
    else:
        result={
            "status":400,
            "message":"Empty realmid"
        }
        return JsonResponse(result)

@login_required
def GetP_L(request,initdate,finaldate,realmid):
    realmId=realmid
    if(realmId!=''):
        value=check_realmid_valid(realmId)
        print(value)
        if(value["status"]==200):
            # print("its a valid realmid with access token")
            le=getlegalentity(realmId)
            refresh_token =le["values"][0]["qb_refreshtoken"]
            access_token=redis_instance.get(realmId).decode()
            response, status_code = getPLInfo(access_token, realmId,initdate,finaldate)
            values=json.dumps(response)
            if status_code >= 400:
                # if call to QBO doesn't succeed then get a new bearer token from refresh token and try again
                bearer = getBearerTokenFromRefreshToken(refresh_token)
                updateSession(request, bearer.accessToken, bearer.refreshToken, realmId)
                access_token=redis_instance.get(realmId).decode()
                response, status_code = getPLInfo(access_token, realmId,initdate,finaldate)
                values=json.dumps(response)
                print(response)
                if status_code >= 400:
                    message="Get PL Info unable to get the required information, Qb id is  " + realmId
                    crm=User.objects.filter(groups__name='CRM').first()
                    q=QbEvent(name="qb_profitloss",type="qb_profitloss",qb_id=realmId,status=False,crm=crm,legalentity=le,message=message)
                    q.save()
                    result={
                        "status":400,
                        "message": message

                    }
                    return JsonResponse(result)

            # cust=le.customer
            d = datetime.datetime.now().astimezone(timezone('Asia/Kolkata'))
            print("Values is")
            print(values)
            #print(json.loads(values))
            #print(le["values"][0]["id"])
            #c=insert_report(entity=str(le["values"][0]["id"]),day=d.day,month=d.month,year=d.year,report_type="P_L",version=1.0,created_at=d.strftime("%m/%d/%Y, %H:%M:%S"),modified_at=d.strftime("%m/%d/%Y, %H:%M:%S"),result=values)
            #print(c)
            crm=User.objects.filter(groups__name='CRM').first()
            message="Successfully accessed P_L Info, Qb id is  " + realmId
            q=QbEvent(name="qb_profitloss",type="qb_profitloss",qb_id=realmId,status=True,crm=crm,legalentity=le,message=message)
            q.save()
            result={
                "status":200,
                "message": message,
                "values":json.loads(values)
            }
            return JsonResponse(result)

        elif(value["status"]==400):
            result={
                "status":400,
                "message":value["message"]
            }
        return JsonResponse(result)
    else:
        result={
            "status":400,
            "message":"Empty realmid"
        }
        return JsonResponse(result)

# @login_required
# def P_LCall(request,reportid,initdate,finaldate):
#     #report=Report.objects.get(pk=reportid)
#     #custid=report.customer.id
#     #print("Customer Id is")
#     realmId = 193514846602714
#     le=LegalEntity.objects.get(qb_id=realmId)
#     refresh_token =le.qb_refreshtoken
#     if(refresh_token == ''):
#         return HttpResponseServerError()
#     else:
#         access_token=redis_instance.get(realmId).decode()
#         user=request.user
#         print("Calling PL Info")
#         company_info_response, status_code = getPLInfo(access_token, realmId, 1,initdate,finaldate)
#         values=json.dumps(company_info_response)
#         print(company_info_response)
#
#         #report.qb_api=company_info_response
#         #report.save()
#         #pull_invoice_api.delay(reportid,custid,access_token)
#         if status_code >= 400:
#             # if call to QBO doesn't succeed then get a new bearer token from refresh token and try again
#             bearer = getBearerTokenFromRefreshToken(refresh_token)
#             updateSession(request, bearer.accessToken, bearer.refreshToken, realmId)
#             company_info_response, status_code = getPLInfo(access_token, realmId, 1,initdate,finaldate)
#             values=json.dumps(company_info_response)
#             if status_code >= 400:
#                 result={
#                     "status":400,
#                     "message":"No token found. Please login and enable the Qb"
#                 }
#                 return JsonResponse(result)
#
#         #company_name = company_info_response['CompanyInfo']['CompanyName']
#         #address = company_info_response['CompanyInfo']['CompanyAddr']
#         return HttpResponse(values)

@login_required
def get_CSRF_token(request):
    token = request.session.get('csrfToken', None)
    if token is None:
        token = getSecretKey()
        request.session['csrfToken'] = token
    return token




