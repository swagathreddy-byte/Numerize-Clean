import os
from celery import Celery,signals
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

app = Celery('Workspace',backend='amqp')
@signals.celeryd_init.connect
def setup_log_format(sender, conf, **kwargs):
    conf.worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s] fc-celery-reports %(message)s"
    conf.worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s] fc-celery-reports  [%(task_name)s(%(task_id)s)] %(message)s"

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()