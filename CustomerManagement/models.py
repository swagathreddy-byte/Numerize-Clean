from django.db import models
from SubscriptionManagement.models import Subscription
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from Workspace.utilities import *
from django.dispatch import receiver
# Create your models here.

# class Onboarding(models.Model):
#     start_date=models.DateField(auto_now_add=True)
#     end_date=models.DateField(null=True)
#     master_onboarding=JSONField(default=initialize_master_onboarding)
#     process_onboarding=JSONField(default=initialize_process_onboarding)
#     hr_onboarding=JSONField(default=initialize_hr_onboarding)

# class Customer(models.Model):
#     name=models.CharField(max_length=200)
#     address=models.TextField(max_length=400)
#     user_account = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="cust_account",null=True,limit_choices_to={'groups__name': "Customer"})
#     #branch=JSONField(null=True,default=list,blank=True)
#     accountant=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,default=2,related_name="accountant",limit_choices_to={'groups__name': "Accountant"})
#     tl=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="tl_customer",default=2,limit_choices_to={'groups__name': "TeamLead"},null=True,blank=True)
#     qc=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="qc_customer",default=2,limit_choices_to={'groups__name': "QC"})
#     crm=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="crm_customer",default=2,limit_choices_to={'groups__name': "CRM"})
#     onboarding=models.ForeignKey(Onboarding,on_delete=models.CASCADE,default=1,null=True,blank=True)
#     subscription=models.ForeignKey(Subscription,on_delete=models.CASCADE,default=1,null=True,blank=True)
#     active=models.BooleanField(default=False)
#     def __str__(self):
#         return '%s' % (self.name)



# @receiver(models.signals.post_delete, sender=Customer)
# def delete_user_account_post(sender, instance, *args, **kwargs):
#     if instance.user_account:
#         instance.user_account.delete()



# class LegalEntity(models.Model):
#     name=models.CharField(max_length=100)
#     gst=models.CharField(max_length=100)
#     qb_id=models.CharField(max_length=100)
#     customer=models.ForeignKey(Customer,on_delete=models.CASCADE,related_name="legal_entities")
#     qb_refreshtoken=models.CharField(max_length=500,default='',blank=True, null=True)
#     active=models.BooleanField(default=False)
#     def __str__(self):
#         return '%s - %s' % (self.customer.name , self.name)
#
#     def save(self, *args, **kwargs):
#         if self.customer.active == False:
#             self.active=False # Yoko shall never have her own blog!
#
#         super().save(*args, **kwargs)

# class Outlet(models.Model):
#     name=models.CharField(max_length=100)
#     legalentity=models.ManyToManyField(LegalEntity,related_name="outlets")
#     branch=models.CharField(max_length=100,default="branch")
#     active=models.BooleanField(default=False)
#     def __str__(self):
#         return '%s - %s' % (self.legalentity.name , self.name)
#
#     def save(self, *args, **kwargs):
#         # if self.legalentity.active == False:
#         #     self.active=False # Yoko shall never have her own blog!
#
#         super().save(*args, **kwargs)

# class Brand(models.Model):
#     name=models.CharField(max_length=100)
#     outlet=models.ManyToManyField(Outlet,related_name="brands")
#     active=models.BooleanField(default=False)
#     def __str__(self):
#         return '%s' % (self.name)
#
#     def save(self, *args, **kwargs):
#         super().save(*args, **kwargs)


# @receiver(models.signals.post_save, sender=Customer)
# def modify_customer_post(sender, instance, *args, **kwargs):
#     instance.user_account.is_active=instance.active
#     instance.user_account.save()
#     if(instance.active==False):
#         le=instance.legal_entities.all()
#         for i in range(len(le)):
#             le[i].active=False
#             le[i].save()
#
# @receiver(models.signals.post_save, sender=LegalEntity)
# def modify_legalentity_post(sender, instance, *args, **kwargs):
#     if(instance.active==False):
#         le=instance.outlets.all()
#         for i in range(len(le)):
#             le[i].active=False
#             le[i].save()
#
#
# @receiver(models.signals.post_save, sender=Outlet)
# def modify_brand_post(sender, instance, *args, **kwargs):
#     if(instance.active==False):
#         le=instance.brands.all()
#         for i in range(len(le)):
#             le[i].active=False
#             le[i].save()

