from django.urls import path, re_path
from ZohoApplication import views

urlpatterns = [
    # path('', views.zoho_view),  # Home url
    # path('auth_code/', views.auth_code),  # it gives the code
    # re_path(r'^zoho_authtokens', views.get_auth_tokens),  # we use that code to generate access token and refresh tokens

    # path('account_list/', views.ListAccounts.as_view()),
    # path('billing_list/', views.ListBills.as_view()),
    # path('bill_payment_list/', views.ListBillPayments.as_view()),
    # path('invoice_list/', views.ListInvoices.as_view()),
    # path('items_list/', views.ListItems.as_view()),
    # path('journal_list/', views.ListJournals.as_view()),
    # path('expense_list/', views.ListExpenses.as_view()),
    # path('taxcode_list/', views.ListTaxcodes.as_view()),
    # path('taxrate_list/', views.ListTaxrates.as_view()),
    # path('vendor_list/', views.ListVendors.as_view()),
    path('authCodeHandler/', views.AuthCodeHandler.as_view(),name="authCodeHandler"),
    path('authdetails/', views.AuthDetails.as_view(),name="authDetails"),
    # path('authCodeHandler/', views.authCodeHandler, name='authCodeHandler'),
]
