from celery import shared_task
# from .report_generator import *
import os
from .models import *
from django.contrib.auth.models import User
from django.core.files import File
from datetime import datetime,date
from django.conf import settings
from CustomerManagement.models import *
import requests
from django.core.mail import send_mail
import boto3
from botocore.client import Config
from pytz import timezone
import re
from itertools import groupby
import sys
sys.path.insert(0, '../reportgeneration')
from report_generator import *
import json

def get_file_path(name,filename):
    d = date.today()
    mon=d.strftime("%b")
    actualfilename=os.path.basename(filename)
    return 'input/{0}/{1}/{2}'.format(name,mon,actualfilename)


@shared_task
def Periodic_report_task():

    # all cutomer list api call
    headers = {'Accept': 'application/json', 'accept': 'application/json'}
    apiUrl = settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.CUSTOMER_GET_API_URL
    print(apiUrl)
    apiReq = requests.get(apiUrl, headers=headers)
    api_status_code = apiReq.status_code
    if api_status_code == 200:
        cust = json.loads(apiReq.text)['result']
        print(cust)
        # cust=Customer.objects.all()
        sub_PL = ""
        sub_GST = ""
        sub_CL_ST = ""
        sub_CON_ANA = ""
        sub_S_C_R = ""
        sub_SW_IN = ""
        sub_SW_DUMP = ""
        sub_TDS = ""
        sub_PUR_EFF = ""

        for i in range(len(cust)):
            subs=cust[i]['subscription']
            print(subs)
            for j in range(len(subs)):
                if(subs[j]["report_name"] == "Profit Statement"):
                    if(subs[j]["input_type"] == "outlet"):
                        sub_PL=subs[j]["subscriptions"]
                # if(subs[j]["report_name"] == "Closing Stock"):
                #     sub_CL_ST=subs[j]["subscribe"]
                # if(subs[j]["report_name"] == "GST Summary"):
                #     if(subs[j]["input_type"] == "outlet"):
                #         sub_GST=subs[j]["subscriptions"]
                # if(subs[j]["report_name"] == "Consumption Analysis"):
                #     if(subs[j]["input_type"] == "outlet"):
                #         sub_CON_ANA=subs[j]["subscriptions"]
                # if(subs[j]["report_name"] == "Sales Channel Reconciliation"):
                #     if(subs[j]["input_type"] == "customer"):
                #         sub_S_C_R=subs[j]["subscribe"]
                # if(subs[j]["report_name"] == "Swiggy Invoice Level Reconciliation"):
                #     if(subs[j]["input_type"] == "customer"):
                #         sub_SW_IN=subs[j]["subscribe"]
                # if(subs[j]["report_name"] == "Swiggy Dump Level Reconciliation"):
                #     if(subs[j]["input_type"] == "customer"):
                #         sub_SW_DUMP=subs[j]["subscribe"]
                # if(subs[j]["report_name"] == "TDS Summary"):
                #     sub_TDS=subs[j]["subscribe"]
                # if(subs[j]["report_name"] == "Purchase Efficiency"):
                #     sub_PUR_EFF=subs[j]["subscribe"]

        if(sub_PL!=""):
            print(sub_PL)
            for k in range(len(sub_PL)):
                if(sub_PL[k]["subscribe"]==True):

                    print(sub_PL[k]["outlet"])
                    print(sub_PL[k]["id"])
                    #outlet=Outlet.objects.get(name=sub_PL[k]["outlet"])

                    # les=outlet.legalentity
                    # le=les.objects.get()
                    apiUrl = settings.EXPRESS_API_HOST + ":" + settings.EXPRESS_API_PORT + settings.OUTLET_GET_API_URL
                    apiUrl = apiUrl+"?_id="+sub_PL[k]["id"]
                    print(apiUrl)
                    apiReq = requests.get(apiUrl, headers=headers)
                    api_status_code = apiReq.status_code
                    if api_status_code == 200:
                        outlet = json.loads(apiReq.text)['result']
                        outlet=outlet[0]
                        print(outlet)
                        print(cust[i])
                        print(outlet)
                        accountant = User.objects.get(id=cust[i]['accountant'])
                        qc = User.objects.get(id=cust[i]['qc'])
                        crm = User.objects.get(id=cust[i]['crm'])
                        cust_json={"name":cust[i]['name'],"id":cust[i]['_id']}
                        outlet_json = {"name": outlet["name"], "id": outlet["_id"]}
                        print(cust_json)
                        print(outlet_json)
                        r=Report(customer=cust_json,owner=accountant,qc=qc,crm=crm,report_type="P_L",outlet=outlet_json)
                        d = datetime.now().astimezone(timezone('Asia/Kolkata'))
                        r.month=d.month
                        r.year=d.year
                        r.save()
                        print(r)

                        mon=d.strftime("%b")
                        event={
                            "ownerid" : accountant.id,
                            "ownername" : accountant.name,
                            "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                            "month" : mon,
                            "eventtype" : "lifecycle",
                            "eventvalue" : "Initiated",
                            "message" : "Profit and Loss Task has been created"
                        }

                        checklist={
                            "qc_checklist": {
                                "commonChecklist": [
                                    {
                                        "name": "Swiggy",
                                        "checklists": [
                                            {
                                                "check": "Is the taxable sales values entered/considered in the report correct/macthing?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the commission entered in the report correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Are all the other charges related to sales apart from from commission are correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the TDS rate entered correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the GST rates entered correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is TCS charged correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            }
                                        ]
                                    },
                                    {
                                        "name": "Zomato",
                                        "checklists": [
                                            {
                                                "check": "Is the taxable sales values entered/considered in the report correct/macthing?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the commission entered in the report correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Are all the other charges related to sales apart from from commission are correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the TDS rate entered correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the GST rates entered correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is TCS charged correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            }
                                        ]
                                    },
                                    {
                                        "name": "Dunzo",
                                        "checklists": [
                                            {
                                                "check": "Is the taxable sales values entered/considered in the report correct/macthing?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the commission entered in the report correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Are all the other charges related to sales apart from from commission are correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the TDS rate entered correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the GST rates entered correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is TCS charged correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            }
                                        ]
                                    },
                                    {
                                        "name": "Ubereats",
                                        "checklists": [
                                            {
                                                "check": "Is the taxable sales values entered/considered in the report correct/macthing?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the commission entered in the report correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Are all the other charges related to sales apart from from commission are correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the TDS rate entered correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the GST rates entered correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is TCS charged correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            }
                                        ]
                                    },
                                    {
                                        "name": "Card Sales",
                                        "checklists": [
                                            {
                                                "check": "Is the taxable sales values entered/considered in the report correct/macthing?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the commission entered in the report correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Are all the other charges related to sales apart from from commission are correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the GST rates entered correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            }
                                        ]
                                    },
                                    {
                                        "name": "Razorpay Sales",
                                        "checklists": [
                                            {
                                                "check": "Is the taxable sales values entered/considered in the report correct/macthing?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the commission entered in the report correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Are all the other charges related to sales apart from from commission are correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the GST rates entered correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            }
                                        ]
                                    },
                                    {
                                        "name": "Ezetap Sales",
                                        "checklists": [
                                            {
                                                "check": "Is the taxable sales values entered/considered in the report correct/macthing?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the commission entered in the report correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Are all the other charges related to sales apart from from commission are correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the GST rates entered correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            }
                                        ]
                                    },
                                    {
                                        "name": "Nearbuy",
                                        "checklists": [
                                            {
                                                "check": "Is the taxable sales values entered/considered in the report correct/macthing?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the commission entered in the report correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Are all the other charges related to sales apart from from commission are correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the GST rates entered correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            }
                                        ]
                                    },
                                    {
                                        "name": "Paytm Sales",
                                        "checklists": [
                                            {
                                                "check": "Is the taxable sales values entered/considered in the report correct/macthing?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the commission entered in the report correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Are all the other charges related to sales apart from from commission are correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the GST rates entered correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            }
                                        ]
                                    },
                                    {
                                        "name": "Any other payment gateways",
                                        "checklists": [
                                            {
                                                "check": "Is the taxable sales values entered/considered in the report correct/macthing?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the commission entered in the report correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Are all the other charges related to sales apart from from commission are correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the GST rates entered correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            }
                                        ]
                                    },
                                    {
                                        "name": "Cash Sales",
                                        "checklists": [
                                            {
                                                "check": "Is the taxable sales values entered/considered in the report correct/macthing?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the commission entered in the report correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Are all the other charges related to sales apart from from commission are correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the GST rates entered correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            }
                                        ]
                                    },
                                    {
                                        "name": "B2B Sales",
                                        "checklists": [
                                            {
                                                "check": "Are the B2B taxable value of sales correct/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the input credit has been considered?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Are the rates considered for input GST correct?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the section 17 of GST Act considered?",
                                                "input": "",
                                                "remarks": ""
                                            }
                                        ]
                                    },
                                    {
                                        "name": "Other Income",
                                        "checklists": [
                                            {
                                                "check": "Is the applicable royalty amount correctly calculated?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the GST rate considered correctly for above income?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the taxable value of rental income accounted/reported correctly/matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is the GST rate considered correctly for above income?",
                                                "input": "",
                                                "remarks": ""
                                            }
                                        ]
                                    }
                                ],
                                "reportChecklist": [
                                    {
                                        "name": "Profit & Loss Satatement",
                                        "checklists": [
                                            {
                                                "check": "Is Page 4 and QB profit matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Is page 2 and page 4 profits matching?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Are the page 4 COA's correctly categorised under respective head in Page 2?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Are stock adjustments are considered correctly from stock valuation?",
                                                "input": "",
                                                "remarks": ""
                                            },
                                            {
                                                "check": "Are notes given as per instructions given?",
                                                "input": "",
                                                "remarks": ""
                                            }
                                        ]
                                    }
                                ]
                            },
                            "tl_checklist": {
                                "loans": [
                                    {
                                        "check": "In case of loans, is due entry passed for interest repayment?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "In case of loans, is due entry passed for principal repayment?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "In case of loans, is payment entry passed for interest repayment?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "In case of loans, is payment entry passed for principal repayment?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are due entries and payment entries passed for interest and principal repayment?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ],
                                "sales": [
                                    {
                                        "check": "Is the table in the sale channels' commission table 1 filled up?",
                                        "input": "True",
                                        "remarks": "esrtyukhj,n xczsrdtfgh"
                                    },
                                    {
                                        "check": "Is the a variance in Zomato commision less than 10%?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the a variance in Swiggy commision less than 10%?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the a variance in Paytm commision less than 10%?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the a variance in Ubereats commision less than 10%?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the a variance in card swipe commision less than 10%?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Whether due entry is passed for all sales other than cash sales?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Whether Payment entry passed for Sales channel sales (Swiggy, Paytm, Card sales, etc)?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Whether difference between received and receivable less than 5% of total sales?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are pending B2B invoices recorded in Qb?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ],
                                "cashbook": [
                                    {
                                        "check": "Is cash book (Or, alternative document for recording cash transactions) verified?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the month-end cash balance as per Qb same as per cash book/alternative document?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is cash balance as per Qb positive on all days in the month?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ],
                                "expenses": [
                                    {
                                        "check": "Is the expenditure as per vouchers/alternate document same as that of QB?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are all the line items posted?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are all the expense types mentioned in the last 2 months, present this month?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are all expenses accounted on accrual basis?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the variance in salaries of this month compared to the last 2 months' average less than 10%?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the due entry for salaries matching with the payments?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ],
                                "purchases": [
                                    {
                                        "check": "Are the no.of bills as per Qb and physical bills the same? (as per table 2 in the working sheet)",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is accounting for payments made to the vendors done on bill to bill basis/FIFO basis?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is bank mapping done for all vendor payments?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ],
                                "otherincome": [
                                    {
                                        "check": "Is the fixed other incomes same this month compared to the previous months?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Were all the other incomes (Variable) of the previous months mentioned this month?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ],
                                "closing_stock": [
                                    {
                                        "check": "Are rates available for all the items in closing stock?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ],
                                "profit_statement": [
                                    {
                                        "check": "Is the Profit/(Loss) matching in page 2 and page 4?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the variance in expenses less the 10%?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ],
                                "statutory_duties": [
                                    {
                                        "check": "Are due entries passed for GST, TDS, PT, ESI, EPF, Advance tax?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are payment entries passed for GST, TDS, PT, ESI, EPF, Advance tax?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are entries for interest and penalty (On payments and refunds, if any) passed separately?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are due and payment entries passed for refund of statutory duties/taxes, if any?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ],
                                "bank_transactions": [
                                    {
                                        "check": "Are all bank debits and credits mapped/accounted for?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are unexplained debits and credits declared in the profit statement?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the balance as per Qb matching with the closing bank balance?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ],
                                "other_balance_sheet": [
                                    {
                                        "check": "Are purchases of assets accounted for?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the money brought in (In cash) by partners/directors recorded?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the money brought in (In bank) by partners/directors recorded?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ],
                                "partner_directors_transactions": [
                                    {
                                        "check": "Are transactions made by partners/directors accounted for?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is due entry passed for salaries to partners/directors?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is payment entry passed for salaries to partners/directors?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are payments made by partners/directors directly on behalf of the organisation accounted for?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are loan transactions with partners/directors accounted for?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ]
                            },
                            "acc_checklist": {
                                "sales": [
                                    {
                                        "check": "Is the table in the sale channels' commission table 1 filled up?",
                                        "input": "True",
                                        "remarks": "bvnbm,m"
                                    },
                                    {
                                        "check": "Is the a variance in Zomato commision less than 10%?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the a variance in Swiggy commision less than 10%?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the a variance in Paytm commision less than 10%?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the a variance in Ubereats commision less than 10%?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the a variance in card swipe commision less than 10%?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Whether due entry is passed for all sales other than cash sales?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Whether Payment entry passed for Sales channel sales (Swiggy, Paytm, Card sales, etc)?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Whether difference between received and receivable less than 5% of total sales?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are pending B2B invoices recorded in Qb?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ],
                                "expenses": [
                                    {
                                        "check": "Is the expenditure as per vouchers/alternate document same as that of QB?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are all expenses accounted on accrual basis?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the variance in salaries of this month compared to the last 2 months' average less than 10%?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the due entry for salaries matching with the payments?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ],
                                "purchases": [
                                    {
                                        "check": "Are the no.of bills as per Qb and physical bills the same? (as per table 2 in the working sheet)",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is accounting for payments made to the vendors done on bill to bill basis/FIFO basis?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is bank mapping done for all vendor payments?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ],
                                "closing_stock": [
                                    {
                                        "check": "Are rates available for all the items in closing stock?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ],
                                "profit_statement": [
                                    {
                                        "check": "Is the Profit/(Loss) matching in page 2 and page 4?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the variance in expenses less the 10%?",
                                        "input": "True",
                                        "remarks": "safdhj"
                                    }
                                ],
                                "statutory_duties": [
                                    {
                                        "check": "Are due entries passed for GST, TDS, PT, ESI, EPF, Advance tax?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are payment entries passed for GST, TDS, PT, ESI, EPF, Advance tax?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are entries for interest and penalty (On payments and refunds, if any) passed separately?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are due and payment entries passed for refund of statutory duties/taxes, if any?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ],
                                "bank_transactions": [
                                    {
                                        "check": "Are all bank debits and credits mapped/accounted for?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Are unexplained debits and credits declared in the profit statement?",
                                        "input": "",
                                        "remarks": ""
                                    },
                                    {
                                        "check": "Is the balance as per Qb matching with the closing bank balance?",
                                        "input": "",
                                        "remarks": ""
                                    }
                                ]
                            }
                        }
                        r.checklists=checklist
                        r.activity.append(event)
                        print(r)
                        r.save()

        if(sub_GST!=""):
            for k in range(len(sub_GST)):
                if(sub_GST[k]["subscribe"]==True):
                    outlet=Outlet.objects.get(name=sub_GST[k]["outlet"])
                    r=Report(customer=cust[i],owner=cust[i].accountant,tl=cust[i].tl,qc=cust[i].qc,crm=cust[i].crm,report_type="GST",outlet=outlet)
                    d = datetime.now().astimezone(timezone('Asia/Kolkata'))
                    r.month=d.month
                    r.year=d.year
                    r.save()
                    mon=d.strftime("%b")
                    event={
                        "ownerid" : cust[i].accountant.id,
                        "ownername" : cust[i].accountant.username,
                        "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                        "month" : mon,
                        "eventtype" : "lifecycle",
                        "eventvalue" : "Initiated",
                        "message" : "GST Task has been created"
                    }
                    r.activity.append(event)
                    r.save()
        # if(sub_CL_ST):
        #     r=Report(customer=cust[i],owner=cust[i].accountant,tl=cust[i].tl,qc=cust[i].qc,crm=cust[i].crm,report_type="CL_ST")
        #     d = datetime.now().astimezone(timezone('Asia/Kolkata'))
        #     r.month=d.month
        #     r.year=d.year
        #     r.save()
        #     mon=d.strftime("%b")
        #     event={
        #         "ownerid" : cust[i].accountant.id,
        #         "ownername" : cust[i].accountant.username,
        #         "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
        #         "month" : mon,
        #         "eventtype" : "lifecycle",
        #         "eventvalue" : "Initiated",
        #         "message" : "GST Task has been created"
        #     }
        #     r.activity.append(event)
        #     r.save()
        if(sub_CON_ANA!=""):
            for k in range(len(sub_CON_ANA)):
                if(sub_CON_ANA[k]["subscribe"]==True):
                    outlet=Outlet.objects.get(name=sub_CON_ANA[k]["outlet"])
                    r=Report(customer=cust[i],owner=cust[i].accountant,tl=cust[i].tl,qc=cust[i].qc,crm=cust[i].crm,report_type="CON_ANA",outlet=outlet)
                    d = datetime.now().astimezone(timezone('Asia/Kolkata'))
                    r.month=d.month
                    r.year=d.year
                    r.save()
                    mon=d.strftime("%b")
                    event={
                        "ownerid" : cust[i].accountant.id,
                        "ownername" : cust[i].accountant.username,
                        "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                        "month" : mon,
                        "eventtype" : "lifecycle",
                        "eventvalue" : "Initiated",
                        "message" : "GST Task has been created"
                    }
                    r.activity.append(event)
                    r.save()



        if(sub_S_C_R):
            r=Report(customer=cust[i],owner=cust[i].accountant,tl=cust[i].tl,qc=cust[i].qc,crm=cust[i].crm,report_type="S_C_R")
            d = datetime.now().astimezone(timezone('Asia/Kolkata'))
            r.month=d.month
            r.year=d.year
            r.save()
            mon=d.strftime("%b")
            event={
                "ownerid" : cust[i].accountant.id,
                "ownername" : cust[i].accountant.username,
                "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                "month" : mon,
                "eventtype" : "lifecycle",
                "eventvalue" : "Initiated",
                "message" : "Sales Channel Reconciliation Task has been created"
            }
            r.activity.append(event)
            r.save()
        # if(sub_SW_IN):
        #     r=Report(customer=cust[i],owner=cust[i].accountant,tl=cust[i].tl,qc=cust[i].qc,crm=cust[i].crm,report_type="SW_IN")
        #     d = datetime.now().astimezone(timezone('Asia/Kolkata'))
        #     r.month=d.month
        #     r.year=d.year
        #     r.save()
        #     mon=d.strftime("%b")
        #     event={
        #         "ownerid" : cust[i].accountant.id,
        #         "ownername" : cust[i].accountant.username,
        #         "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
        #         "month" : mon,
        #         "eventtype" : "lifecycle",
        #         "eventvalue" : "Initiated",
        #         "message" : "Swiggy Invoice Task has been created"
        #     }
        #     r.activity.append(event)
        #     r.save()
        if(sub_SW_DUMP):
            r=Report(customer=cust[i],owner=cust[i].accountant,tl=cust[i].tl,qc=cust[i].qc,crm=cust[i].crm,report_type="SW_DUMP")
            d = datetime.now().astimezone(timezone('Asia/Kolkata'))
            r.month=d.month
            r.year=d.year
            r.save()
            mon=d.strftime("%b")
            event={
                "ownerid" : cust[i].accountant.id,
                "ownername" : cust[i].accountant.username,
                "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                "month" : mon,
                "eventtype" : "lifecycle",
                "eventvalue" : "Initiated",
                "message" : "Swiggy Dump Task has been created"
            }
            r.activity.append(event)
            r.save()
        # if(sub_TDS):
        #     r=Report(customer=cust[i],owner=cust[i].accountant,tl=cust[i].tl,qc=cust[i].qc,crm=cust[i].crm,report_type="TDS")
        #     d = datetime.now().astimezone(timezone('Asia/Kolkata'))
        #     r.month=d.month
        #     r.year=d.year
        #     r.save()
        #     mon=d.strftime("%b")
        #     event={
        #         "ownerid" : cust[i].accountant.id,
        #         "ownername" : cust[i].accountant.username,
        #         "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
        #         "month" : mon,
        #         "eventtype" : "lifecycle",
        #         "eventvalue" : "Initiated",
        #         "message" : "TDS Task has been created"
        #     }
        #     r.activity.append(event)
        #     r.save()
        if(sub_PUR_EFF):
            r=Report(customer=cust[i],owner=cust[i].accountant,tl=cust[i].tl,qc=cust[i].qc,crm=cust[i].crm,report_type="PUR_EFF")
            d = datetime.now().astimezone(timezone('Asia/Kolkata'))
            r.month=d.month
            r.year=d.year
            r.save()
            mon=d.strftime("%b")
            event={
                "ownerid" : cust[i].accountant.id,
                "ownername" : cust[i].accountant.username,
                "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
                "month" : mon,
                "eventtype" : "lifecycle",
                "eventvalue" : "Initiated",
                "message" : "Purchase Efficiency Task has been created"
            }
            r.activity.append(event)
            r.save()



@shared_task
def generate_swiggy_dump_report(input_file_url,week_input_file_url,master_in_data_url,unzip_url,user_id,cust_id,report_id,in_data_url,week_in_data_url):

    user=User.objects.get(id=user_id)
    cust=Customer.objects.get(id=cust_id)
    r=Report.objects.get(id=report_id)
    try:
        output=SDLR(input_file_url,week_input_file_url,master_in_data_url,unzip_url)
    except:
        if os.path.exists(input_file_url):
            shutil.rmtree(input_file_url)
        if os.path.exists(week_input_file_url):
            shutil.rmtree(week_input_file_url)

        if os.path.exists(in_data_url):
            os.remove(in_data_url)
        if os.path.exists(week_in_data_url):
            os.remove(week_in_data_url)
        if os.path.exists(master_in_data_url):
            os.remove(master_in_data_url)
        raise
    else:
        if os.path.exists(input_file_url):
            shutil.rmtree(input_file_url)
        if os.path.exists(week_input_file_url):
            shutil.rmtree(week_input_file_url)
        if os.path.exists(in_data_url):
            os.remove(in_data_url)
        if os.path.exists(week_in_data_url):
            os.remove(week_in_data_url)
        if os.path.exists(master_in_data_url):
            os.remove(master_in_data_url)
        print("Success")
        report_url=output.fname1
        localfile=open(report_url,"rb")
        djangofile=File(localfile)
        filepath=get_file_path(user.username,localfile.name)
        fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
        fileurl+=filepath
        outputfile=PrivateExcelDocument(user=user,record=r,upload=djangofile,document_link=filepath)
        outputfile.save()
        if os.path.exists(report_url):
            os.remove(report_url)
        report_url=output.fname2
        localfile=open(report_url,"rb")
        djangofile=File(localfile)
        filepath=get_file_path(user.username,localfile.name)
        fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
        fileurl+=filepath
        outputfile=PrivateExcelDocument(user=user,record=r,upload=djangofile,document_link=filepath)
        outputfile.save()
        if os.path.exists(report_url):
            os.remove(report_url)
        fileurl='/get_file/'+str(r.id)+'/'
        r.status="Review"
        # result=json.loads(output.result)
        r.tl=cust.tl #User
        r.qc=cust.qc #User
        r.crm=cust.crm #User
        # r.results=result
        r.status="Review"
        d = datetime.now().astimezone(timezone('Asia/Kolkata'))
        mon=d.strftime("%b")
        event={
            "modifierid" : user.id,
            "modifiername" : user.username,
            "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
            "month" : mon,
            "eventtype" : "lifecycle",
            "eventvalue" : "Updated",
            "message" : "Swiggy Dump Level Report has been created",
            "status" : "Review"
        }
        r.activity.append(event)
        r.save()
        #f.close()
        return {'status': 'Valid', 'message': 'File processed','fileurl':fileurl}


@shared_task
def generate_profit_loss(qb_url,cat_url,file_suffix,user_id,cust_id,report_id):
    user=User.objects.get(id=user_id)
    cust=Customer.objects.get(id=int(cust_id))
    #r=Report(report_type=report_type,owner=user,customer=cust,status="Generated")
    #r.save()
    r=Report.objects.get(id=report_id)
    try:
        output=Prof_Stat(qb_url,cat_url,file_suffix)
    except:

        if os.path.exists(qb_url):
            os.remove(qb_url)
        if os.path.exists(cat_url):
            os.remove(cat_url)
        raise
    else:
        if os.path.exists(qb_url):
            os.remove(qb_url)
        if os.path.exists(cat_url):
            os.remove(cat_url)
        report_url=settings.BASE_DIR+"/"+output.fname
        localfile=open(report_url,"rb")
        djangofile=File(localfile)
        filepath=get_file_path(user.username,localfile.name)
        fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
        fileurl+=filepath
        outputfile=PrivateExcelDocument(user=user,record=r,upload=djangofile,document_link=filepath)
        outputfile.save()

        result=json.loads(output.result)
        r.tl=cust.tl #User
        r.qc=cust.qc #User
        r.crm=cust.crm #User
        r.results=result
        r.status="Review"
        #Deleting old output files
        links=r.pdf_attachments.all()
        s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
        for i in range(len(links)):
            attach=links[i]
            fileurl=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+attach.document_link
            s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=fileurl)
            attach.delete()


        d = datetime.now().astimezone(timezone('Asia/Kolkata'))
        mon=d.strftime("%b")
        event={
            "modifierid" : user.id,
            "modifiername" : user.username,
            "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
            "month" : mon,
            "eventtype" : "lifecycle",
            "eventvalue" : "Updated",
            "message" : "Profit and Loss Report has been created",
            "status" : "Review"
        }
        r.activity.append(event)
        r.save()


        ##########Get Manager
        ##########Get Email
        ##########Send Email

        # print(json.dumps(result, indent=4, sort_keys=True))

        comments=r.comments
        comments=json.dumps(comments)
        comments=json.loads(comments)
        grouped_comments=[]
        keys=[]
        v=[]
        if comments is not None:
            comments["values"].sort(key=lambda content: content['comment_category'])
            gp=groupby(comments["values"],lambda content: content['comment_category'])

            for key,g in gp:
                types=[]
                content=[]
                if(key not in keys):
                    keys.append(key)

                for con in g:

                    if(con["comment_type"] not in types):
                        types.append(con["comment_type"])
                    content.append(con)

                v={"category":key,"types":types,"values":content}

                grouped_comments.append(v)

        jsonparams={
            "template": { "name" : "PL-Main","recipe": "chrome-pdf" },
            "data" : {"result":result,"comments":grouped_comments,"keys":keys},
            "options": { "reports": { "save": True },"reportName": "myreport"}
        }
        print(jsonparams)
        jsreporturl=settings.JSREPORTENGINE_HOST+":"+settings.JSREPORTENGINE_PORT+"/api/report"
        print(jsreporturl)
        jsreportdata=settings.JSREPORTENGINE_DATA
        print(jsreportdata)
        jsrep=requests.post(jsreporturl,json=jsonparams,auth=('ca-reporting','fatca123@'))
        link=jsrep.headers['Report-BlobName']
        print(link)
        fileurl_pdf=jsreportdata+link
        rename_pdf_url=jsreportdata+file_suffix+"_"+link
        os.rename(fileurl_pdf,rename_pdf_url)
        fileurl_pdf=rename_pdf_url
        localfile=open(fileurl_pdf,"rb")
        djangofile=File(localfile)
        filepath=get_file_path(user.username,localfile.name)
        fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
        fileurl+=filepath
        pdffile=PrivatePdfDocument(user=user,record=r,upload=djangofile,document_link=filepath)
        pdffile.save()


        man_email=cust.accountant.email
        print(man_email)
        send_mail('Report Created', 'Hi, A new report has been created and has been sent for your approval. Please login to your firstcourse workflow to check it.', 'chaitanya.nandigama@firstcourse.in', [man_email], fail_silently=False)
        fileurl='/get_file/'+str(r.id)+'/'
        return {'status': 'Valid', 'message': 'File processed','fileurl':fileurl}



@shared_task
def generate_gst(b2c_input_url,b2b_input_url,tax_credit_url,file_suffix,user_id,cust_id,report_id):

    user=User.objects.get(id=user_id)
    cust=Customer.objects.get(id=int(cust_id))
    #r=Report(report_type=report_type,owner=user,customer=cust,status="Generated")
    #r.save()
    r=Report.objects.get(id=report_id)
    try:
        output=Gst_Sum(b2c_input_url,b2b_input_url,tax_credit_url,file_suffix)
    except:
        if (b2c_input_url!='' and os.path.exists(b2c_input_url)):
            os.remove(b2c_input_url)
        if (b2b_input_url!='' and os.path.exists(b2b_input_url)):
            os.remove(b2b_input_url)
        if (tax_credit_url!='' and os.path.exists(tax_credit_url)):
            os.remove(tax_credit_url)
        raise
    else:
        if (b2c_input_url!='' and os.path.exists(b2c_input_url)):
            os.remove(b2c_input_url)
        if (b2b_input_url!='' and os.path.exists(b2b_input_url)):
            os.remove(b2b_input_url)
        if (tax_credit_url!='' and os.path.exists(tax_credit_url)):
            os.remove(tax_credit_url)
        report_url=settings.BASE_DIR+"/"+output.fname
        localfile=open(report_url,"rb")
        djangofile=File(localfile)

        print("Saved")
        filepath=get_file_path(user.username,localfile.name)
        # filepath='media/private/'+filepath
        fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
        fileurl+=filepath
        outputfile=PrivateExcelDocument(user=user,record=r,upload=djangofile,document_link=filepath)
        outputfile.save()
        print("saved Excel file")
        # output.result["customer"]=cust.name
        # d = datetime.now().astimez`one(timezone('Asia/Kolkata'))
        # mon=d.strftime("%b")
        # output.result["month"]=mon
        result=output.result

        r.tl=cust.tl #User
        r.qc=cust.qc #User
        r.crm=cust.crm #User
        links=r.pdf_attachments.all()
        comments=r.comments
        s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
        for i in range(len(links)):
            attach=links[i]
            fileurl=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+attach.document_link
            s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=fileurl)
            attach.delete()

        comments=r.comments

        jsonparams={
            "template": { "name" : "GST-Main","recipe": "chrome-pdf" },
            "data" : {"result":result,"comments":comments},
            "options": { "reports": { "save": True },"reportName": "myreport"}
        }
        jsreporturl=settings.JSREPORTENGINE_HOST+":"+settings.JSREPORTENGINE_PORT+"/api/report"
        jsreportdata=settings.JSREPORTENGINE_DATA
        jsrep=requests.post(jsreporturl,json=jsonparams,auth=('ca-reporting','fastca123@'))
        link=jsrep.headers['Report-BlobName']
        fileurl_pdf=jsreportdata+link
        rename_pdf_url=jsreportdata+file_suffix+"_"+link
        os.rename(fileurl_pdf,rename_pdf_url)
        fileurl_pdf=rename_pdf_url
        print(fileurl_pdf)
        localfile=open(fileurl_pdf,"rb")
        djangofile=File(localfile)
        filepath=get_file_path(user.username,localfile.name)
        fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
        fileurl+=filepath
        pdffile=PrivatePdfDocument(user=user,record=r,upload=djangofile,document_link=filepath)
        pdffile.save()
        r.status="Review"
        r.results=result
        d = datetime.now().astimezone(timezone('Asia/Kolkata'))
        mon=d.strftime("%b")
        event={
            "modifierid" : user.id,
            "modifiername" : user.username,
            "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
            "month" : mon,
            "eventtype" : "Lifecycle",
            "eventvalue" : "Updated",
            "message" : "GST Report has been created",
            "status" : "Review"
        }
        r.activity.append(event)
        r.save()

        fileurl='/get_file/'+str(r.id)+'/'

        man_email=cust.accountant.email
        print(man_email)
        send_mail('Report Created', 'Hi, A new report has been created and has been sent for your approval. Please login to your firstcourse workflow to check it.', 'chaitanya.nandigama@firstcourse.in', [man_email], fail_silently=False)
        fileurl='/get_file/'+str(r.id)+'/'
        return {'status': 'Valid', 'message': 'File processed','fileurl':fileurl}


@shared_task
def generate_pe(input_url,file_suffix,user_id,cust_id,report_id):

    user=User.objects.get(id=user_id)
    cust=Customer.objects.get(id=int(cust_id))
    r=Report.objects.get(id=report_id)
    try:
        output=Purchase_Efficiency(input_url,file_suffix)
    except:
        if os.path.exists(input_url):
            os.remove(input_url)
        raise
    else:
        if os.path.exists(input_url):
            os.remove(input_url)
        #######################################Deleting old Excel files#############################################################
        links=r.excel_attachments.all()
        s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
        for i in range(len(links)):
            attach=links[i]
            fileurl=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+attach.document_link
            s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=fileurl)
            attach.delete()

        #####################################Processing and storing in S3 Excel sheet #############################################
        report_url=settings.BASE_DIR+"/"+output.fname
        localfile=open(report_url,"rb")
        djangofile=File(localfile)
        filepath=get_file_path(user.username,localfile.name)
        fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
        fileurl+=filepath
        outputfile=PrivateExcelDocument(user=user,record=r,upload=djangofile,document_link=filepath)
        outputfile.save()


        #Extract the results in json and store in the object

        result=output.result
        result=json.loads(result)
        # print(result)
        r.tl=cust.tl #User
        r.qc=cust.qc #User
        r.crm=cust.crm #User
        r.results=result
        r.status="Review"

        ######################################Deleting old pdf files#############################################################
        links=r.pdf_attachments.all()
        s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
        for i in range(len(links)):
            attach=links[i]
            fileurl=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+attach.document_link
            s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=fileurl)
            attach.delete()

        d = datetime.now().astimezone(timezone('Asia/Kolkata'))
        mon=d.strftime("%b")
        event={
            "modifierid" : user.id,
            "modifiername" : user.username,
            "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
            "month" : mon,
            "eventtype" : "lifecycle",
            "eventvalue" : "Updated",
            "message" : "Purchase Efficiency Report has been created",
            "status" : "Review"
        }
        r.activity.append(event)
        r.save()

        comments=r.comments
        jsonparams={
            "template": { "name" : "PE-Main","recipe": "chrome-pdf" },
            "data" : {"result":result,"comments":comments},
            "options": { "reports": { "save": True },"reportName": "myreport"}
        }
        jsreporturl=settings.JSREPORTENGINE_HOST+":"+settings.JSREPORTENGINE_PORT+"/api/report"
        jsreportdata=settings.JSREPORTENGINE_DATA
        jsrep=requests.post(jsreporturl,json=jsonparams,auth=('ca-reporting','fastca123@'))
        link=jsrep.headers['Report-BlobName']
        fileurl_pdf=jsreportdata+link
        rename_pdf_url=jsreportdata+file_suffix+"_"+link
        os.rename(fileurl_pdf,rename_pdf_url)
        fileurl_pdf=rename_pdf_url
        localfile=open(fileurl_pdf,"rb")
        djangofile=File(localfile)
        filepath=get_file_path(user.username,localfile.name)
        fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
        fileurl+=filepath
        pdffile=PrivatePdfDocument(user=user,record=r,upload=djangofile,document_link=filepath)
        pdffile.save()


        man_email=cust.accountant.email
        print(man_email)
        send_mail('Report Created', 'Hi, A new report has been created and has been sent for your approval. Please login to your firstcourse workflow to check it.', 'chaitanya.nandigama@firstcourse.in', [man_email], fail_silently=False)
        fileurl='/get_file/'+str(r.id)+'/'
        return {'status': 'Valid', 'message': 'File processed','fileurl':fileurl}


@shared_task
def generate_con_analysis(cs_files,os_files,purchase_file,months,years,file_suffix,user_id,cust_id,report_id):

    user=User.objects.get(id=user_id)
    cust=Customer.objects.get(id=int(cust_id))
    r=Report.objects.get(id=report_id)
    try:

        output=Consumption_Analysis(os_files,purchase_file,cs_files,months,years,file_suffix)
    except:
        raise
    #
    # if os.path.exists(input_url):
    #     os.remove(input_url)
    else:
        print("Hey output is success")
        #######################################Deleting old Excel files#############################################################
        links=r.excel_attachments.all()
        s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
        for i in range(len(links)):
            attach=links[i]
            fileurl=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+attach.document_link
            s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=fileurl)
            attach.delete()

        ######################################Processing and storing in S3 Excel sheet #############################################
        report_url=settings.BASE_DIR+"/"+output.fname
        localfile=open(report_url,"rb")
        djangofile=File(localfile)
        filepath=get_file_path(user.username,localfile.name)
        fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
        fileurl+=filepath
        outputfile=PrivateExcelDocument(user=user,record=r,upload=djangofile,document_link=filepath)
        outputfile.save()


        #Extract the results in json and store in the object

        print("output")

        result=output.json
        # result = re.sub('nan', '0', result)
        # result = re.sub('NaN', '0', result)
        result=json.loads(result)
        print(result)
        r.tl=cust.tl #User
        r.qc=cust.qc #User
        r.crm=cust.crm #User
        r.results=result
        r.status="Review"

        #######################################Deleting old pdf files#############################################################
        links=r.pdf_attachments.all()
        s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
        for i in range(len(links)):
            attach=links[i]
            fileurl=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+attach.document_link
            s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=fileurl)
            attach.delete()

        d = datetime.now().astimezone(timezone('Asia/Kolkata'))
        mon=d.strftime("%b")
        event={
            "modifierid" : user.id,
            "modifiername" : user.username,
            "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
            "month" : mon,
            "eventtype" : "lifecycle",
            "eventvalue" : "Updated",
            "message" : "Consumption Analysis Report has been created",
            "status" : "Review"
        }
        r.activity.append(event)
        r.save()

        comments=r.comments
        jsonparams={
            "template": { "name" : "CA-Main","recipe": "chrome-pdf" },
            "data" : {"results":result,"comments":comments},
            "options": { "reports": { "save": True,"blobName": "reports" },"reportName": "myreport"}
        }
        jsreporturl=settings.JSREPORTENGINE_HOST+":"+settings.JSREPORTENGINE_PORT+"/api/report"
        jsreportdata=settings.JSREPORTENGINE_DATA
        jsrep=requests.post(jsreporturl,json=jsonparams,auth=('ca-reporting','fastca123@'))
        print("calling report generator")
        link=jsrep.headers['Report-BlobName']
        fileurl_pdf=jsreportdata+link
        rename_pdf_url=jsreportdata+file_suffix+"_"+link
        os.rename(fileurl_pdf,rename_pdf_url)
        fileurl_pdf=rename_pdf_url
        localfile=open(fileurl_pdf,"rb")
        djangofile=File(localfile)
        filepath=get_file_path(user.username,localfile.name)
        fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
        fileurl+=filepath
        pdffile=PrivatePdfDocument(user=user,record=r,upload=djangofile,document_link=filepath)
        pdffile.save()


        man_email=cust.accountant.email
        print(man_email)
        send_mail('Report Created', 'Hi, A new report has been created and has been sent for your approval. Please login to your firstcourse workflow to check it.', 'chaitanya.nandigama@firstcourse.in', [man_email], fail_silently=False)
        fileurl='/get_file/'+str(r.id)+'/'
        return {'status': 'Valid', 'message': 'File processed','fileurl':fileurl}


@shared_task
def generate_scr_report(bankTranx_file, swiggy_file, zomato_file, dunzo_file, nearbuy_file, dineout_file, swiggy_pos, zomato_pos, dunzo_pos, nearbuy_pos, dineout_pos,file_suffix,user_id,cust_id,report_id):
    user=User.objects.get(id=user_id)
    cust=Customer.objects.get(id=int(cust_id))
    r=Report.objects.get(id=report_id)
    try:
        output=Sales_Recon(bankTranx_file, swiggy_file, zomato_file, dunzo_file, nearbuy_file, dineout_file, swiggy_pos, zomato_pos, dunzo_pos, nearbuy_pos, dineout_pos,file_suffix)
    except:
        if os.path.exists(bankTranx_file):
            os.remove(bankTranx_file)
        if os.path.exists(swiggy_file):
            shutil.rmtree(swiggy_file)
        if os.path.exists(zomato_file):
            shutil.rmtree(zomato_file)
        if os.path.exists(dunzo_file):
            shutil.rmtree(dunzo_file)
        if os.path.exists(nearbuy_file):
            shutil.rmtree(nearbuy_file)
        if os.path.exists(dineout_file):
            shutil.rmtree(dineout_file)
        raise
    else:
        if os.path.exists(bankTranx_file):
            os.remove(bankTranx_file)
        if os.path.exists(swiggy_file):
            shutil.rmtree(swiggy_file)
        if os.path.exists(zomato_file):
            shutil.rmtree(zomato_file)
        if os.path.exists(dunzo_file):
            shutil.rmtree(dunzo_file)
        if os.path.exists(nearbuy_file):
            shutil.rmtree(nearbuy_file)
        if os.path.exists(dineout_file):
            shutil.rmtree(dineout_file)
        #######################################Deleting old Excel files#############################################################
        # links=r.excel_attachments.all()
        # s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
        # for i in range(len(links)):
        #     attach=links[i]
        #     fileurl=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+attach.document_link
        #     s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=fileurl)
        #     attach.delete()
        #
        # #####################################Processing and storing in S3 Excel sheet #############################################
        # report_url=settings.BASE_DIR+"/"+output.fname
        # localfile=open(report_url,"rb")
        # djangofile=File(localfile)
        # filepath=get_file_path(user.username,localfile.name)
        # fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
        # fileurl+=filepath
        # outputfile=PrivateExcelDocument(user=user,record=r,upload=djangofile,document_link=filepath)
        # outputfile.save()
        #
        #
        # #Extract the results in json and store in the object
        #
        d = datetime.now().astimezone(timezone('Asia/Kolkata'))
        mon=d.strftime("%b")
        result=output.json
        result=json.loads(result)
        result["head"]["customer"]=cust.name
        print(result)
        r.tl=cust.tl #User
        r.qc=cust.qc #User
        r.crm=cust.crm #User
        r.results=result
        r.status="Review"
        #
        ######################################Deleting old pdf files#############################################################
        links=r.pdf_attachments.all()
        s3 = boto3.client('s3',aws_access_key_id=settings.AWS_ACCESS_KEY_ID,aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,config=Config(signature_version='s3v4'),region_name='ap-south-1')
        for i in range(len(links)):
            attach=links[i]
            fileurl=settings.AWS_PRIVATE_MEDIA_LOCATION+"/"+attach.document_link
            s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=fileurl)
            attach.delete()


        event={
            "modifierid" : user.id,
            "modifiername" : user.username,
            "date" : d.strftime('%Y-%m-%d %H:%M:%S'),
            "month" : mon,
            "eventtype" : "lifecycle",
            "eventvalue" : "Updated",
            "message" : "Sales Channel Reconciliation Report has been created",
            "status" : "Review"
        }
        r.activity.append(event)
        r.save()
        comments=r.comments
        print("Generating report")
        jsonparams={
            "template": { "name" : "SCR-Main","recipe": "chrome-pdf" },
            "data" : {"result":result,"comments":comments},
            "options": { "reports": { "save": True },"reportName": "myreport"}
        }
        jsreporturl=settings.JSREPORTENGINE_HOST+":"+settings.JSREPORTENGINE_PORT+"/api/report"
        jsreportdata=settings.JSREPORTENGINE_DATA
        jsrep=requests.post(jsreporturl,json=jsonparams,auth=('ca-reporting','fastca123@'))
        link=jsrep.headers['Report-BlobName']
        fileurl_pdf=jsreportdata+link
        rename_pdf_url=jsreportdata+file_suffix+"_"+link
        os.rename(fileurl_pdf,rename_pdf_url)
        fileurl_pdf=rename_pdf_url
        localfile=open(fileurl_pdf,"rb")
        djangofile=File(localfile)
        filepath=get_file_path(user.username,localfile.name)
        fileurl='https://%s/%s/' % (settings.AWS_S3_CUSTOM_DOMAIN,settings.AWS_PRIVATE_MEDIA_LOCATION)
        fileurl+=filepath
        pdffile=PrivatePdfDocument(user=user,record=r,upload=djangofile,document_link=filepath)
        pdffile.save()


        man_email=cust.accountant.email
        print(man_email)
        send_mail('Report Created', 'Hi, A new report has been created and has been sent for your approval. Please login to your firstcourse workflow to check it.', 'chaitanya.nandigama@firstcourse.in', [man_email], fail_silently=False)
        fileurl='/get_file/'+str(r.id)+'/'
        return {'status': 'Valid', 'message': 'File processed','fileurl':fileurl}


