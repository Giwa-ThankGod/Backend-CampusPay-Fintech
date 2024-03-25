import secrets
import requests

from decimal import Decimal

from django.db import models
from django.contrib.auth.models import AbstractUser

from django.shortcuts import get_object_or_404
from django.conf import settings

from django.dispatch import receiver
from django.db.models.signals import post_save

from django.utils.translation import gettext_lazy as _

from user.utils import generate_qrcode, generate_ID, generate_otp

class User(AbstractUser):
    username = models.CharField(max_length=50)

    phone = models.CharField(_('phone'), max_length=11, unique=True)
    email = models.EmailField(_('email'), unique=True)

    is_customer = models.BooleanField(default=False)
    is_vendor = models.BooleanField(default=False)

    USERNAME_FIELD = 'phone'
    # REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.phone
    

class Vendor(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, editable=False)
    VID = models.CharField(max_length=11, unique=True)
    balance = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, editable=False)

    business_name = models.CharField(max_length=50, blank=True)
    business_type = models.CharField(max_length=30, blank=True)
    institution = models.CharField(max_length=200, null=True, blank=True)
    qrcode = models.ImageField(upload_to='qrcode/vendors/', null=True, blank=True)
    transaction_pin = models.CharField(max_length=50, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        generated_ID = generate_ID(vendor=True)

        while Vendor.objects.filter(VID=generated_ID).exists():
            generated_ID = generate_ID(vendor=True)

        if not self.VID:  
            self.VID = generated_ID

        if (
            self.user.email 
            and self.business_name 
            and self.business_type 
            and self.institution 
            and not self.qrcode  # Checks if there's no existing QR code
        ):
            data = {
                'ID': self.VID,
                'phone': self.user.phone,
                'email': self.user.email,
                'business_name': self.business_name,
                'business_type': self.business_type,
                'institution': self.institution,
            }

            self.qrcode = generate_qrcode(data)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.VID
    
    def deposit(self, amount):
        self.balance += Decimal(amount)
        self.save()
        return self.balance

    def withdraw(self, amount):
        amount = Decimal(amount)
        if amount <= self.balance:
            self.balance -= amount
            self.save()
            return self.balance
        else:
            return None

    @receiver(post_save, sender=User)
    def create_user(created, instance, sender, **kwargs):
        if created and instance.is_vendor:
            Vendor.objects.create(user=instance)

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, editable=False)
    CID = models.CharField(max_length=11, unique=True)
    balance = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)

    fullname = models.CharField(max_length=50, blank=True)
    gender = models.CharField(max_length=20, null=True, blank=True)
    institution = models.CharField(max_length=200, blank=True)
    qrcode = models.ImageField(upload_to='qrcode/customers/', null=True, blank=True)
    transaction_pin = models.CharField(max_length=50, null=True, blank=True)

    def save(self, *args, **kwargs):
        generated_ID = generate_ID(customer=True)

        while Customer.objects.filter(CID=generated_ID).exists():
            generated_ID = generate_ID(customer=True)

        if not self.CID:  
            self.CID = generated_ID

        if(
            self.user.email 
            and self.fullname
            and self.institution 
            and not self.qrcode  # Checks if there's no existing QR code
        ):
            data = {
                'ID': self.CID,
                'phone': self.user.phone,
                'email': self.user.email,
                'fullname': self.fullname,
                'institution': self.institution,
            }

            self.qrcode = generate_qrcode(data)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.CID
    
    def deposit(self, amount):
        self.balance += Decimal(amount)
        self.save()
        return self.balance

    def withdraw(self, amount):
        amount = Decimal(amount)
        if amount <= self.balance:
            self.balance -= amount
            self.save()
            return self.balance
        else:
            return None
    
    @receiver(post_save, sender=User)
    def create_user(created, instance, sender, **kwargs):
        if created and instance.is_customer:
            Customer.objects.create(user=instance)

class Transaction(models.Model):
    sender = models.ForeignKey('User', on_delete=models.CASCADE, related_name='sender', null=True, blank=True)
    recepient = models.ForeignKey('User', on_delete=models.CASCADE, related_name='recepient', null=True, blank=True)

    ref = models.CharField(max_length=16, blank=True)
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    transaction_fee = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    transaction_type = models.CharField(max_length=20)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10)
    completed = models.BooleanField(default=False)

    def verify_transaction(self):
        user = get_object_or_404(User, phone=self.sender)

        url = "https://api.flutterwave.com/v3/transactions/verify_by_reference"

        token = settings.FLUTTERWAVE_SECRET_KEY
        headers = {
            "Authorization": f"Bearer {token}"
        }

        param = {
            "tx_ref": self.ref,
        }
        
        try:
            response = requests.get(url=url, headers=headers, params=param)
            if response.status_code == 200:
                if response.json()['status'] == 'success':
                    if not self.completed and response.json()['data']['amount'] == self.amount:
                        amount = Decimal(response.json()['data']['amount'] - self.transaction_fee)
                        if user.is_vendor:
                            vendor = get_object_or_404(Vendor, user=user)
                            vendor.deposit(amount)
                            vendor.save()
                        elif user.is_customer:
                            customer = get_object_or_404(Customer, user=user)
                            customer.deposit(amount)
                            customer.save()
                        
                        self.status = response.json()['status']
                        self.completed = True
                        self.save()
                    else:
                        return {"status": False, "message": "Transaction already verified"}
                elif response.json()['status'] == 'pending':
                    self.status = response.json()['status']
                    self.save()
                    return {"status": False, "message": ""}
                else:
                    return {"status": False, "message": ""}   

                context = {
                    'status': True,
                    'data': {
                        'ref': self.ref,
                        'sender': user.phone,
                        'recepient': "",
                        'amount': self.amount,
                        'transaction_fee': self.transaction_fee,
                        'transaction_type': self.transaction_type,
                        'description': self.description,
                        'created_at': self.created_at,
                        'status': self.status,
                    }
                }
                return context
            else:
                return {
                    "status": False, 
                    "message": {
                        "response_code": f"{response}",
                        # "data": response.json()
                    }
                }
        except requests.exceptions.ConnectionError:
            context = {
                "status": False,
                "message": "Connection Error"
            }
            return context

    def save(self, *args, **kwargs):
        generated_ref = secrets.token_urlsafe(16)
        while Transaction.objects.filter(ref=generated_ref).exists():
            generated_ref = secrets.token_urlsafe(16)

        if not self.ref:  
            self.ref = generated_ref

        super().save(*args, **kwargs)

class PaymentCode(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, default=None, blank=True)
    transaction = models.OneToOneField('Transaction', on_delete=models.CASCADE, default=None, blank=True)

    qrcode = models.ImageField(upload_to='qrcode/payment_code/')