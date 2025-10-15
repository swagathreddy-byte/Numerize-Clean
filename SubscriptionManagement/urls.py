from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

urlpatterns = [
    path('get/choices/', views.choices_list,name='choice_list'),
    path('get/reports/',views.get_reports,name='subscription_services'),
    path('get/template/',views.get_subscription_template,name='subscription_template')
    ]

urlpatterns = format_suffix_patterns(urlpatterns)