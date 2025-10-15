from django.db import models
from django.conf import settings
# Create your models here.
from Workspace.storage_backend import PublicMediaStorage
from ReportManagement.models import FileValidator
from django.dispatch import receiver
import os

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    actualfilename=os.path.basename(filename)
    return 'input/{0}/{1}/{2}'.format(instance.user.username,"profile",actualfilename)

validate_file = FileValidator(max_size=1024 * 10000,content_types=('image/png','image/jpeg'))

class Employee(models.Model):
    #designation=models.CharField(max_length=25)
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="employee",null=True)
    manager=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="team",null=True)
    aboutme=models.TextField(max_length=200,default="about me")
    profile_picture = models.FileField(storage=PublicMediaStorage(),upload_to=user_directory_path,validators=[validate_file],null=True,blank=True)
    background=models.FileField(storage=PublicMediaStorage(),upload_to=user_directory_path,validators=[validate_file],null=True,blank=True)
    def __str__(self):
        return self.user.username


@receiver(models.signals.post_delete, sender=Employee)
def delete_user_account_post(sender, instance, *args, **kwargs):
    if instance.user:
        instance.user.delete()


