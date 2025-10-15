from django.conf.urls import url
from django.urls import path, re_path
from . import views


urlpatterns = [
    path('qb/', views.index, name='index'),
    path('qb/connect/', views.connectToQuickbooks, name='connectToQuickbooks'),
    path('qb/signInWithIntuit/', views.signInWithIntuit, name='signInWithIntuit'),
    path('qb/getAppNow/', views.getAppNow, name='getAppNow'),
    path('qb/authCodeHandler/', views.authCodeHandler, name='authCodeHandler'),
    path('qb/disconnect/', views.disconnect, name='disconnect'),
    path('qb/get/PL/<str:initdate>/<str:finaldate>/<str:realmid>', views.GetP_L, name='P_LCall'),

    path('qb/connected/<str:realmId>/', views.connected, name='connected'),
    path('qb/refreshTokenCall/<str:realmId>/', views.refreshTokenCall, name='refreshTokenCall'),
    path('qb/is_connected/',views.is_connected,name='is_connected'),
    path('qb/get/payables/<str:initdate>/<str:finaldate>/<str:realmid>', views.GetPayables, name='payables'),
    path('qb/get/qbevent/status/latest/<str:token>/',views.qbevent_status,name='payables_status'),
    path('qb/get/receivables/<str:initdate>/<str:finaldate>/<str:realmid>', views.GetReceivables, name='receivables'),
    # path('qb/get/receivables/status/latest',views.receivables_status,name='receivables_status'),

]