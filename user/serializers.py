from user.models import User, Vendor, Customer, Transaction

from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['phone', 'email', 'is_customer', 'is_vendor', 'is_active', 'date_joined']

class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        exclude = ['id']

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        exclude = ['id']
        
class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        exclude = ['id', 'sender', 'recepient']