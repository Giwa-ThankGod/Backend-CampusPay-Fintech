from django.contrib import admin
from user.models import User, Vendor, Customer, Transaction, PaymentCode

# Register your models here.

class VendorAdmin(admin.ModelAdmin):
    list_display = ['VID', 'user', 'balance']

class CustomerAdmin(admin.ModelAdmin):
    list_display = ['CID', 'user', 'balance']

class TransactionAdmin(admin.ModelAdmin):
    list_display = ['ref', 'sender', 'transaction_type', 'status', 'completed']


admin.site.register(User)
admin.site.register(Vendor, VendorAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(PaymentCode)