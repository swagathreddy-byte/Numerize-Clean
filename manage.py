#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import environ

env = environ.Env()
environ.Env.read_env("Workspace/.env")

devel_flag = env.str('ENVIRONMENT')


def main():
    if(devel_flag == "DEVELOPMENT"):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Workspace.settings.development')
    elif(devel_flag == "TEST_AZURE"):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Workspace.settings.production_vnet_test')
    elif(devel_flag == "PROD_AZURE"):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Workspace.settings.production_azure')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
