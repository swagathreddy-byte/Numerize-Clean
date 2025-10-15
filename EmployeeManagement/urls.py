from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views


urlpatterns = [
    # path('home/',views.home,name='home'),
    path('add_employee/',views.add_employee,name='add_employee'),
    path('admin/get/all',views.admin_get_users,name='get_users'),
    path('admin/get/groups',views.admin_get_groups,name='get_groups'),
    path('get/users/',views.get_users,name='get_users'),
    path('get/employees/<str:role>/',views.get_employees,name='get_employees'),
    path('get/myinfo/',views.get_myinfo,name='get_myinfo'),
    path('username_exists/',views.check_if_username_exists,name='emp_user_exists'),
    path('email_exists/',views.check_if_email_exists,name='emp_email_exists'),
]

urlpatterns = format_suffix_patterns(urlpatterns)