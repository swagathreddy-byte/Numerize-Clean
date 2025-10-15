from django.urls import path

from . import views

11

urlpatterns = [
    path('', views.index, name='index'),
    # path('profile/',views.profile,name='profile'),
    path('dashboard/',views.dashboard,name='dashboard'),
    path('tasks/overview/',views.overview_tasks,name='overview_tasks'),
    path('tasks/view/<int:id>/',views.view_task,name='view_task'),
    # path('tools/',views.tools,name='tools'),
    # path('tasks/initiate/',views.initiate_tasks,name='initiate_tasks'),
    # path('tasks/review/',views.review_tasks,name='review_tasks'),

    # path('tasks/peer_review/',views.peer_review_tasks,name='peer_review_tasks'),
    #
    #

    path('reports/summary/',views.reports_summary,name='reports_summary'),
    path('reports/detail/<str:reporttype>',views.reports_detail,name='report_detail'),

    path('ocr/',views.ocrhome,name='ocrhome'),
    path('ocr/textconv/',views.process_image,name='textconv'),

    path('reportissue/',views.helpdesk,name='helpdesk'),

    path('administration/',views.system_admin_dashboard,name="system_admin_dashboard"),
    path('administration/add/customer/',views.add_customer,name="addcustomer"),
    path('administration/manage/customer/<int:id>/',views.manage_customer,name="managecustomer"),
    path('administration/add/employee/',views.add_employee,name="addemployee"),
    path('administration/view/qbstatus/',views.view_qbstatus,name="qbstatus")


]
