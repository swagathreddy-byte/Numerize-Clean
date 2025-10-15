from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

urlpatterns = [
    # path('admin/get/all/', views.admin_customer_list,name='admin_customer_list'),
    # path('get/<int:id>/',views.get_customer,name="get_customer"),
    # path('get/all/', views.customer_list,name='customer_list'),
    # path('get/all/legalentities', views.legalentity_list,name='customer_list'),
    path('get/choices/', views.choices_list,name='choice_list'),
    path('add/',views.add_customer1,name='add_customer1'),
    path('get/onboarding/master/',views.get_master_onboarding,name='get_master_onboarding'),
    path('get/onboarding/process/',views.get_process_onboarding,name='get_process_onboarding'),
    path('username_exists/',views.check_if_username_exists,name='user_exists'),
    path('email_exists/',views.check_if_email_exists,name='email_exists'),
    path('get/myinfo/',views.get_myinfo,name='get_myinfo'),
]

urlpatterns = format_suffix_patterns(urlpatterns)


