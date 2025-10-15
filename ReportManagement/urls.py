from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views



urlpatterns = [
    path('process/report/', views.process_report, name='process_report'),#Processes Reports
    path('update/report/', views.update_report, name='update_report'), #Updates Reports
    path('get/records/', views.report_list,name='report_list'),#
    path('get/choices/', views.choices_list,name='choice_list'),
    path('get/insights/',views.get_insights,name='insights'),
    path('get/tasks/<str:status>/', views.task_list,name='task_list'),
    path('get/report/<int:id>',views.get_report,name='get_report'),
    path('get/result/<str:scope>/',views.get_results,name='get_result'),
    path('get/anomalies/<int:id>/',views.get_anomalies,name='get_anomalies'),
    path('get/comments/<int:id>/',views.get_comments,name='get_comments'),
    path('get/payables/<int:day>/<int:month>/<int:year>/',views.get_payables,name='get_payables'),
    path('get/payables/latest/',views.get_payables_latest,name='get_payables_latest'),
    path('get/receivables/<int:day>/<int:month>/<int:year>/',views.get_receivables,name='get_receivables'),
    path('get/receivables/latest/',views.get_receivables_latest,name='get_receivables_latest'),
    path('get/checklists/<int:id>/',views.get_checklists,name='get_checklists'),
    path('get/activities/<int:id>/',views.get_activities,name='get_activities'),
    path('post/entity/',views.post_entity,name='post_entity'),
    path('delete/entity/',views.delete_entity,name='delete_entity'),
    path('regenerate_report/',views.regenerate_report,name='regenerate_report'),
    path('get/file/<int:id>/<int:fileid>/<str:filetype>/',views.get_file,name='get_file'),
    path('get/status/<str:id>/',views.get_task_status,name='get_task_status')
]

urlpatterns = format_suffix_patterns(urlpatterns)