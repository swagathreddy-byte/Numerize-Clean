"""
WSGI config for Workspace project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
import environ

env = environ.Env()
environ.Env.read_env("Workspace/.env")

devel_flag = env.str('ENVIRONMENT')
if(devel_flag == "DEVELOPMENT"):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Workspace.settings.development')
elif(devel_flag == "TEST_AZURE"):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Workspace.settings.production_vnet_test')
elif(devel_flag == "PROD_AZURE"):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Workspace.settings.production_azure')

application = get_wsgi_application()
