from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = [
    # path('', views.home, name='ocrhome'),#Processes Reports
    path('get/imglist/',views.get_imglist,name='imglist'),
    path('upload/',views.upload_image,name='upload'),
    path('get/imgdata/',views.get_imagedata,name='imgdata'),
    path('publish/invoicedata/',views.post_result,name='invoide_data'),
]

urlpatterns = format_suffix_patterns(urlpatterns)