from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User,Group
from django.http import HttpResponse,JsonResponse
from ReportManagement.choices import *

def is_admin(user):
    return user.groups.filter(name__in=['Admin']).exists()

def is_manager(user):
    return user.groups.filter(name__in=["Manager"]).exists()

@login_required(login_url='/accounts/login')
@user_passes_test(is_admin)
def check_if_username_exists(request):
    if(request.method=="POST"):
        username=request.POST.get("emp_username")
        try:
            user= User.objects.get(username=username)
            response = JsonResponse({'status': 'false', 'message': 'User Exists'})
            response.status_code = 200
            return response
        except User.DoesNotExist:
            response = JsonResponse({'status': 'true', 'message': 'User Does Not Exists'})
            response.status_code = 200
            return response

@login_required(login_url='/accounts/login')
@user_passes_test(is_admin)
def check_if_email_exists(request):
    if(request.method=="POST"):
        email=request.POST.get("emp_email")
        try:
            user= User.objects.get(email=email)
            response = JsonResponse({'status': 'false', 'message': 'User Exists'})
            response.status_code = 200
            return response
        except User.DoesNotExist:
            response = JsonResponse({'status': 'true', 'message': 'User Does Not Exists'})
            response.status_code = 200
            return response

def initialize_master_onboarding():
    m_onboard={
        "data":[
            {
                "heading":"operational_flow",
                "values":[
                    {
                        "heading":"Preamble",
                        "values":[
                            {
                                "heading":"Legal Name",
                                "value":"",
                                "remarks":""
                            },
                            {
                                "heading":"Structure of organisation - proprietorship, firm or company?",
                                "value":"",
                                "remarks":""
                            },
                            {
                                "heading":"Details of operations - B2B or B2C or both ?",
                                "value":"",
                                "remarks":""
                            },
                            {
                                "heading":"No. of departments and names",
                                "value":"",
                                "remarks":""
                            },
                            {
                                "heading":"SPOC ",
                                "value":"",
                                "remarks":""
                            },
                        ],
                    },
                    {
                        "heading":"Revenue",
                        "values":[
                            {
                                "heading":"Sales",
                                "value":[
                                    {
                                        "heading":"Is POS used? If yes, which POS is used? If no, then how are sales recorded? ",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"How is cash sales currently recorded? ",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"How are card sales currently recorded? ",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"Are EDC statements obtained from bank every month?(EDC statements reflect the commision charged on swipes made through the machines linked with a particular account)",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"Are daily settlement report available for the card swipes made? ",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"List of online sales platforms ",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"List of online payment platforms ",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"How are non-chargeable sales recorded? ",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"Can we get the credentials for the POS, online sales platforms and payment platforms? ",
                                        "value":"",
                                        "remarks":""
                                    },
                                ],

                            },
                            {
                                "heading":"Franchise",
                                "value":[
                                    {
                                        "heading":"No. of franchise  ",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"Location - inside &/or outside the state? ",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"What is the billing process? ",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"Terms of rates and royalty?",
                                        "value":"",
                                        "remarks":""
                                    },

                                ],

                            },
                            {
                                "heading":"Outlet wise profitablity ",
                                "value":[
                                    {
                                        "heading":"Are indents prepared for transfers?  ",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"Are transfers made at a margin? ",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"Are details of expenses incurred at each outlet maintained? ",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"If answer to 'c' is yes then how is the following expenses maintained:-Cash expenses, Bank expenses",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"Are purchases directly made by the outlets? If yes then how are these bills maintained?",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"How is walkin sales (cash&card) recorded?",
                                        "value":"",
                                        "remarks":""
                                    },

                                ],
                            },
                            {
                                "heading":"Credit sales  ",
                                "value":[
                                    {
                                        "heading":"Credit terms   ",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"Invoicing  ",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"Conditions of sales ",
                                        "value":"",
                                        "remarks":""
                                    },
                                ],
                            },
                            {
                                "heading":"Other income details (i.e incomes other than sales. Like renting the outlet etc)  ",
                                "value":[
                                    {
                                        "heading":"Any Extra Information",
                                        "value":"",
                                        "remarks":""
                                    },

                                ],
                            }
                        ],
                    },
                    {
                        "heading":"Purchases",
                        "values":[
                            {
                                "heading":"Cash purchases",
                                "value":[
                                    {
                                        "heading":"Are vouchers used for cash purchases made?",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"Are bills available for such cash purchases?",
                                        "value":"",
                                        "remarks":""
                                    },
                                ]
                            },
                            {
                                "heading":"Credit",
                                "value":[
                                    {
                                        "heading":"Is there any fixed credit period?",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"Are bills maintained in a file?",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"How are payments made? Cash&/or bank?",
                                        "value":"",
                                        "remarks":""
                                    }
                                ]
                            },
                        ]
                    },
                    {
                        "heading":"Expenses",
                        "values":[
                            {
                                "heading":"Salary",
                                "value":[
                                    {
                                        "heading":"If payroll is a part of our deliverables, then, Is there an attendance sheet maintained or biometric devices?",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"If payroll is a part of our deliverables, then, How many week-offs are given?",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"If payroll is a part of our deliverables, then, Are service charges given? If yes, then what's the policy",
                                        "value":"",
                                        "remarks":""
                                    },
                                ]
                            },
                            {
                                "heading":"Rent",
                                "value":[
                                    {
                                        "heading":"Is rent paid for the outlets?",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"Is rent paid for the factory? if applicable.",
                                        "value":"",
                                        "remarks":""
                                    },
                                    {
                                        "heading":"Outlets rent based on Sales?",
                                        "value":"",
                                        "remarks":""
                                    }
                                ]
                            },
                            {
                                "heading":"Any other important recurring expenses? Are bills available for them?",
                                "value":[]
                            }
                        ]
                    },
                    {
                        "heading":"Stock management - Movement & other things",
                        "values":[
                            {
                                "value":"How many times are stock count taken?",
                                "remarks":"",
                            },
                            {
                                "value":"How is stock valuation done? Is there any master rate list or from the latest invoices?",
                                "remarks":"",
                            },
                            {
                                "value":"POS used for stock track ?",
                                "remarks":"",
                            },
                            {
                                "value":"Dc notes/Indents for issues?",
                                "remarks":"",
                            },
                            {
                                "value":"Who checks the quantity received?",
                                "remarks":"",
                            },

                        ]
                    },
                    {
                        "heading":"Cash Management",
                        "values":[
                            {
                                "heading":"Is there any cash book maintained?",
                                "values":"",
                                "remarks":""
                            },
                            {
                                "heading":"Are vouchers prepared/bills available for all cash expenses?",
                                "values":"",
                                "remarks":""
                            },
                            {
                                "heading":"Is counter sales (i.e cash sales) used for daily cash expenses or a seperately amount is given by the management?",
                                "values":"",
                                "remarks":""
                            },
                            {
                                "heading":"Is physical cash tallied with closing balance as per cash book on a daliy basis?",
                                "values":"",
                                "remarks":""
                            },
                            {
                                "heading":"Is daily cash report sent?",
                                "values":"",
                                "remarks":""
                            }
                        ]
                    },
                    {
                        "heading":"Bank transacations Management",
                        "values":[
                            {
                                "heading":"No of bank accounts",
                                "values":"",
                                "remarks":""
                            },
                            {
                                "heading":"Are cash sales deposited in bank on T+1 basis?",
                                "values":"",
                                "remarks":""
                            },
                            {
                                "heading":"Availbility of management for bank comments",
                                "values":"",
                                "remarks":""
                            },                {
                                "heading":"Would the client like to link bank account with QB or give weekly (10/15 days) bank statement with explanations.",
                                "values":"",
                                "remarks":""
                            }
                        ]
                    },
                    {
                        "heading":"Loans",
                        "values":[
                            {
                                "heading":"Are there any loans taken? (If yes, we would require the repayment schedule)",
                                "values":"",
                                "remarks":""
                            },
                        ]
                    },
                    {
                        "heading":"Visit timings",
                        "values":[
                            {
                                "heading":"",
                                "values":"",
                                "remarks":""
                            }
                        ]
                    },
                    {
                        "heading":"Is partner CA included? If yes, fill the below:-",
                        "values":[
                            {
                                "heading":"Compliances to be taken care of by the partner CA?",
                                "values":"",
                                "remarks":""
                            },
                            {
                                "heading":"ROC’s procedures",
                                "values":"",
                                "remarks":""
                            },
                            {
                                "heading":"Are compliances to be filed for the period before entering into agreement with Firstcourse?",
                                "values":"",
                                "remarks":""
                            },
                            {
                                "heading":"If yes, then the list of such compliances and the period",
                                "values":"",
                                "remarks":""
                            },
                        ]
                    },
                ]
            },
            {

            }
        ]
    }


    return m_onboard

def initialize_process_onboarding():
    m_onboard={
        "data":[
            {
                "heading":"Online Sales Platform",
                "values":[
                    {
                        "heading":"Swiggy",
                        "status":"unset",
                        "remarks":""
                    },
                    {
                        "heading":"Zomato",
                        "status":"unset",
                         "remarks":""
                    },
                    {
                        "heading":"Magic Pin",
                        "status":"unset",
                        "remarks":""
                    },
                    {
                        "heading":"POS",
                        "status":"unset",
                        "remarks":""
                    },
                    {
                        "heading":"Uber Eats",
                        "status":"unset",
                        "remarks":""
                    },
                    {
                        "heading":"Dine In",
                        "status":"unset",
                        "remarks":""
                    },
                    {
                        "heading":"Any Other",
                        "status":"unset",
                        "remarks":""
                    }
                ]
            },
            {
                "heading":"Bank Account Linking To Quickbooks",
                "values":[
                    {
                        "heading":"Bank Account Linking To Quickbooks",
                        "status":"unset",
                        "remarks":""
                    },
                ]

            },
            {
                "heading":"Quick Books",
                "values":[
                    {
                        "heading":"Quick Books",
                        "status":"unset",
                        "remarks":""
                    }
                ]
            },
            {
                "heading":"Stationery Setup",
                "values":[
                    {
                        "heading":"Vouchers",
                        "status":"unset",
                        "remarks":""
                    },
                    {
                        "heading":"Cashbook",
                        "status":"unset",
                        "remarks":""
                    },
                    {
                        "heading":"Indent",
                        "status":"unset",
                        "remarks":""
                    },
                    {
                        "heading":"GRN",
                        "status":"unset",
                        "remarks":""
                    },

                ]
            },
            {
                "heading":"Client Visits",
                "values":[
                    {
                        "heading":"First Visit",
                        "status":"unset",
                        "remarks":""
                    },
                    {
                        "heading":"Second Visit",
                        "status":"unset",
                        "remarks":""
                    },
                    {
                        "heading":"Third Visit",
                        "status":"unset",
                        "remarks":""
                    }
                ]
            },
            {
                "heading":"Onboarding Signoff Dates",
                "values":[
                    {
                        "heading":"Onboarding Signoff Dates",
                        "status":"unset",
                        "remarks":""
                    }
                ]
            }
        ]
    }
    return m_onboard

def initialize_hr_onboarding():
    m_onboard={
        "Online_Sales_Platform":[
            {
                "heading":"Swiggy",
                "status":"unset"
            },
            {
                "heading":"Zomato",
                "status":"unset"
            },
            {
                "heading":"Magic Pin",
                "status":"unset"
            },
            {
                "heading":"POS",
                "status":"unset"
            },
            {
                "heading":"Uber Eats",
                "status":"unset"
            },
            {
                "heading":"Dine In",
                "status":"unset"
            },
            {
                "heading":"Any Other",
                "status":"unset"
            }
        ],
        "Bank_Account_Linking_To_Quickbooks":{
            "status":"unset",

        },
        "Quick_Books":{
            "status":"unset",
            "value":""
        },
        "Stationery_Setup":[
            {
                "heading":"Vouchers",
                "status":"unset",
                "remarks":""
            },
            {
                "heading":"Cashbook",
                "status":"unset",
                "remarks":""
            },
            {
                "heading":"Indent",
                "status":"unset",
                "remarks":""
            },
            {
                "heading":"GRN",
                "status":"unset",
                "remarks":""
            },

        ],
        "Client_Visits":[
            {
                "heading":"First Visit",
                "status":"unset",
                "value":"",
                "remarks":""
            },
            {
                "heading":"Second Visit",
                "status":"unset",
                "value":"",
                "remarks":""
            },
            {
                "heading":"Third Visit",
                "status":"unset",
                "value":"",
                "remarks":""
            }
        ],
        "Onboarding_Signoff_Dates":{
            "status":"unset",
            "remarks":""
        }
    }
    return m_onboard

def initiatize_subscription():
    s_data={
        "data":[]
    }
    for i in REPORT_TYPE:
        s_data["data"].append(
            {
                "report_type":i[1],
                "subscribe":"",
                "frequency_type":[],
                "input_type":[]
            }
        )

    return s_data
