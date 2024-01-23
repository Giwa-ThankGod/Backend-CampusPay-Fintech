from django.urls import path

from user import views

urlpatterns = [
    path('users/', views.users),
    path('vendors/', views.vendors),
    path('vendors/<ID>/', views.vendor_detail),
    path('customers/', views.customers),
    path('customers/<ID>/', views.customer_detail),

    # Funding Wallet
    path('ussd-topup/', views.ussd_topup),
    path('bank-transfer-topup/', views.bank_transfer_topup),
    path('direct-bank-charge-topup/', views.direct_bank_charge_topup),
    path('verify-transaction/<ref>/', views.verify_transaction),

    path('transactions/<phone>/', views.transaction_history),

    # In App Transfer
    path('initiate-transfer/<phone>/', views.initiate_transfer),
    path('authorize-transfer/<ref>/', views.authorize_transfer),

    path('generate-code/<user>/<ID>/', views.generate_payment_code),
]