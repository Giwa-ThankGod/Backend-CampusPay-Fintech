import requests
import bcrypt
from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from django.core.paginator import Paginator
from django.http import Http404
from django.conf import settings
from django.db.models import Q

from user.models import User, Vendor, Customer, PaymentCode, Transaction
from user.serializers import UserSerializer, VendorSerializer, CustomerSerializer, TransactionSerializer
from user.utils import generate_qrcode
from user.decorators import roles_required

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework import status

# Authentication
from rest_framework.permissions import IsAdminUser, IsAuthenticated


# ------------------------------------------------------------------------------
# USER ENDPOINTS
# ------------------------------------------------------------------------------
@api_view(['GET','POST'])
def users(request):
    if request.method == "GET":
        if getattr(request.user, 'is_superuser'):
            users = User.objects.filter(is_superuser=False)
            serializer = UserSerializer(users, many=True)

            context = {
                'users': serializer.data,
                'count': users.count(),
                'status': True,
            }

            return Response(context)
        else:
            context = {
                "status": False,
                "message": "User is not authorized to access this endpoint."
            }

            return Response(context)
     
    elif request.method == "POST":
        # User Inputs
        phone = request.data.get('phone')
        email = request.data.get('email', None)
        password = request.data.get('password', None)
        is_vendor = request.data.get('vendor', None)
        is_customer = request.data.get('customer', None)

        if phone and password:
            try:
                user = User(phone=phone, email=email, is_vendor = is_vendor, is_customer = is_customer)
                user.set_password(password)
                user.save()
            except IntegrityError:
                return Response({
                    'status': False,
                    'message': f'User with phone {phone} already exist!!!',
                })

            serializer = UserSerializer(user)

            context = {
                'user': {
                    ** serializer.data, 
                    "phone": user.vendor,
                },
                'status': True,            
            }

            return Response(context)
        else:
            context = {
                'status': True,
            }

            return Response(context)
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# VENDOR ENDPOINTS
# ------------------------------------------------------------------------------
@api_view(['GET','POST'])
@roles_required(['is_superuser', 'is_vendor'])
def vendors(request):
    if request.method == "GET":
        vendor = Vendor.objects.all()

        serializer = VendorSerializer(vendor, many=True)

        context = {
            'vendors': serializer.data,
            'count': vendor.count(),
            'status': True,
        }

        return Response(context)

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
@roles_required(['is_superuser', 'is_vendor'])
def vendor_detail(request, ID):
    if request.method == "GET":
        vendor = get_object_or_404(Vendor, VID=ID)

        if request.user.is_superuser or request.user.phone == vendor.user.phone:
            serializer = VendorSerializer(vendor)

            context = {
                'vendor': {
                    ** serializer.data, 
                    "phone": vendor.user.phone,
                    "email": vendor.user.email,
                },
                'status': True,
            }

            return Response(context, status=status.HTTP_404_NOT_FOUND)
        else:
            context = {
                "status": False,
                "message": "User is not authorized to access this endpoint."
            }
            return Response(context)
    
    if request.method == "PATCH":
        if request.user.is_superuser or request.user.phone == vendor.user.phone:
            email = request.data.get('email')
            business_name = request.data.get('business_name')
            business_type = request.data.get('business_type')
            institution = request.data.get('institution')

            vendor = get_object_or_404(Vendor, VID=ID)
            if not vendor.user.email:
                vendor.user.email = email
            vendor.business_name = business_name
            vendor.business_type = business_type
            vendor.institution = institution
            vendor.save()

            serializer = VendorSerializer(vendor)

            context = {
                'vendor': {
                    ** serializer.data, 
                    "phone": vendor.user.phone,
                    "email": vendor.user.email,
                },
                'updated': True,
                'status': True,
            }

            return Response(context, status=status.HTTP_202_ACCEPTED)
        else:
            context = {
                "status": False,
                "message": "User is not authorized to access this endpoint."
            }
            return Response(context)
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# CUSTOMER ENDPOINTS
# ------------------------------------------------------------------------------
@api_view(['GET'])
@permission_classes([IsAdminUser])
def customers(request):
    if request.method == "GET":
        customer = Customer.objects.all()

        serializer = CustomerSerializer(customer, many=True)

        context = {
            'customers': serializer.data,
            'count': customer.count(),
            'status': True,
        }

        return Response(context)     
    

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
@roles_required(['is_superuser', 'is_vendor'])
def customer_detail(request, ID):
    customer = get_object_or_404(Customer, CID=ID)

    if request.method == "GET":
        if request.user.is_superuser or request.user.phone == customer.user.phone:
            serializer = CustomerSerializer(customer)

            context = {
                'customer': {
                    ** serializer.data, 
                    "phone": customer.user.phone,
                    "email": customer.user.email,
                },
                'status': True,
            }

            return Response(context, status=status.HTTP_404_NOT_FOUND)
        else:
            context = {
                "status": False,
                "message": "User is not authorized to access this endpoint."
            }
            return Response(context)
    
    elif request.method == "PATCH":
        if request.user.phone == customer.user.phone:
            email = request.data.get('email')
            fullname = request.data.get('fullname')
            institution = request.data.get('institution')

            if not customer.user.email:
                customer.user.email = email
            customer.fullname = fullname
            customer.institution = institution
            customer.save()
            serializer = CustomerSerializer(customer)

            context = {
                'customer': {
                    ** serializer.data, 
                    "phone": customer.user.phone,
                    "email": customer.user.email,
                },
                'updated': True,
                'status': True,
            }

            return Response(context)
        else:
            context = {
                "status": False,
                "message": "User is not authorized to access this endpoint."
            }
            return Response(context)
# ------------------------------------------------------------------------------
# 

# START AUTHORIZATION PIN
# ---------------------------------------------------------------------------------------------------------------------------------------------------------
@api_view(['POST', 'PATCH'])
@permission_classes([IsAuthenticated])
@roles_required(['is_vendor', 'is_customer'])
def authorization_pin(request, phone):
    if request.method == "POST":
        pin = request.data.get("authorization_pin", None)

        if pin is None:
            return Response({"status": False,"message": "Bad Request"}, status=status.HTTP_400_BAD_REQUEST)

        initiator = get_object_or_404(User, phone=phone)
        try:
            initiator = initiator.vendor
        except Vendor.DoesNotExist:
            initiator = initiator.customer

        """@TODO
        - download and install bcrypt
        - hash the user's authorization pin and save to database
        """
        hashed_authorization_pin = bcrypt.hashpw(
            authorization_pin.encode(),
            bcrypt.gensalt()
        )
        initiator.transaction_pin = hashed_authorization_pin
        initiator.save()
    elif request.method == "PATCH":
        return

# START QRCODE MANAGEMENT
# ---------------------------------------------------------------------------------------------------------------------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@roles_required(['is_vendor', 'is_customer'])
def generate_payment_code(request, phone):

        recepientID = request.data.get('recepientID', None)
        amount = request.data.get('amount', None)
        transaction_type = request.data.get('transaction_type', None)
        description = request.data.get('description', None)

        if (recepientID is None or amount is None or transaction_type is None):
            context = {
                "status": False,
                "message": "Bad Request"
            }
            return Response(context, status=status.HTTP_400_BAD_REQUEST)
        
        initiator = get_object_or_404(User, phone=phone)
        receiver = get_object_or_404(User, phone=recepientID)

        try:
            sender = initiator.vendor
        except Vendor.DoesNotExist:
            sender = initiator.customer

        if sender.withdraw(amount) is None:
            # Create a Transaction instance for failed transactions here.
            return Response({"status": False, "message": "Insufficient balance"}, status=status.HTTP_200_OK)
        
        try:
            recepient = receiver.vendor
        except Vendor.DoesNotExist:
            recepient = receiver.customer

        transaction = Transaction.objects.create(
            sender = sender,
            recepient = recepient,
            amount = Decimal(amount),
            transaction_type = transaction_type,
            description = description,
            status = 'pending'
        )

        data = {
            "ref": transaction.ref,
            "sender": sender,
            "recepient": recepient,
            "amount": amount,
            "description": transaction.description,
            "status": transaction.status,
            "created_at": transaction.created_at
        }
        # Should the authorization pin of the sender be added to the qrcode data
        # so it can be authorized by the receiver of the money. 
        generated_qrcode = generate_qrcode(data)
        
        payment = PaymentCode.objects.create(
            user=initiator,
            transaction = transaction,
            qrcode = generated_qrcode
        )

        serializer = TransactionSerializer(transaction)

        context = {
            "status": True,
            "data": {
                ** serializer,
                "qrcode": payment.qrcode
            }
        }
        return Response(context, status=status.HTTP_200_OK)
# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# END QRCODE MANAGEMENT


# START TRANSFER
# ---------------------------------------------------------------------------------------------------------------------------------------------------------
@api_view(['POST'])
# @permission_classes([IsAuthenticated])
# @roles_required(['is_vendor', 'is_customer'])
def initiate_transfer(request, phone):
    recepientID = request.data.get("recepient", None)
    email = request.data.get("email", None)
    amount = request.data.get("amount", None)
    description = request.data.get("description", None)

    if recepientID is None or amount is None:
        return Response({"status": False, "message": "Bad Request"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        initiator = get_object_or_404(User, phone=phone)
        receiver = get_object_or_404(User, phone=recepientID)
    except Http404:
        return Response({"status": False, "message": "Resource not Found"}, status=status.HTTP_404_NOT_FOUND)

    # Performance Optimized!!!
    try:
        sender = initiator.vendor
    except Vendor.DoesNotExist:
        sender = initiator.customer

    if sender.withdraw(amount) is None:
        # Create a Transaction instance for failed transactions here.
        amount = Decimal(amount)
        transaction = Transaction.objects.create(
            sender = initiator,
            recepient = receiver,
            amount = amount,
            transaction_type = "transfer",
            description = description,
            status = "failed"
        )
        return Response({"status": False, "message": "Insufficient balance"}, status=status.HTTP_200_OK)
    
    # try:
    #     recepient = receiver.vendor
    # except Vendor.DoesNotExist:
    #     recepient = receiver.customer
        
    transaction = Transaction.objects.create(
        sender = initiator,
        recepient = receiver,
        amount = Decimal(amount),
        transaction_type = "transfer",
        description = description,
        status = "pending"
    )
    serializer = TransactionSerializer(transaction)


    context = {
        "status": True,
        "data": {
            **serializer.data
        }
    }
    return Response(context, status=status.HTTP_201_CREATED)


@api_view(['POST'])
# @permission_classes([IsAuthenticated])
# @roles_required(['is_vendor', 'is_customer'])
def authorize_transfer(request, ref):
    authorization_pin = request.data.get("authorization_pin", None)

    if authorization_pin is None:
        return Response({"status": False, "message": "Bad Request"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        transaction = get_object_or_404(Transaction, ref=ref)
    except Http404:
        return Response({"status": False, "message": "Resource not Found"}, status=status.HTTP_404_NOT_FOUND)
    
    # Makes sure the logged in user is the initiator/sender on the transaction
    # before payment can be authorized.
    # if request.user == transaction.sender.user:

    if transaction.completed:
        context = {
            "status": False,
            "message": "Transaction has been authorized"
        }
        return Response(context, status=status.HTTP_208_ALREADY_REPORTED)

    # Transfer Order of Accounts
    try:
        sender = transaction.sender.customer
    except Customer.DoesNotExist:
        sender = transaction.sender.vendor

    try:
        recepient = transaction.recepient.vendor
    except Vendor.DoesNotExist:
        recepient = transaction.recepient.customer

    if transaction.transaction_type == 'transfer':

        sender.withdraw(transaction.amount)
        recepient.deposit(transaction.amount)
        transaction.status = 'success'
        transaction.completed = True
        transaction.save()

        serializer = TransactionSerializer(transaction)

        context = {
            "status": True,
            "data": {
                **serializer.data
            }
        }
        return Response(context, status=status.HTTP_200_OK)
    elif transaction.transaction_type == 'withdrawal':
        pass
    else:
        return Response({"status": False, "message": "Invalid Transaction Type"}, status=status.HTTP_400_BAD_REQUEST)
    
    # else:
    #     return Response({"status": False, "message": "Unauthorized User"}, status=status.HTTP_401_UNAUTHORIZED)

# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# END TRANSFER


# START WITHDRAW
# ---------------------------------------------------------------------------------------------------------------------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@roles_required(['is_vendor', 'is_customer'])
def withdraw(request, phone):
    authorization_pin = request.data.get("authorization_pin", None)
    email = request.data.get("email", None)
    amount = request.data.get("amount", None)

    if authorization_pin is None or email is None or amount is None:
        return Response({"status": False, "message": "Bad Request"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        initiator = get_object_or_404(User, phone=phone, email=request.user.email)
    except Http404:
        return Response({"status": False, "message": "Resource not Found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        sender = initiator.vendor
    except Vendor.DoesNotExist:
        sender = initiator.customer
    
    transaction = Transaction.objects.create(
        sender=initiator, 
        amount=amount, 
        transaction_type='withdraw'
    )

    if sender.withdraw(amount) is None:
        transaction.status = 'failed'
        transaction.save()
        return Response({"status": False, "message": "Insufficient balance"}, status=status.HTTP_200_OK)
    
    url = "https://api.flutterwave.com/v3/charges?type=ussd"

    token = settings.FLUTTERWAVE_SECRET_KEY
    headers = {
        "Authorization": f"Bearer {token}"
    }
    json = {
        "account_bank": "057", # To be change to actual variable.
        "amount": amount,
        "email": email,
        "tx_ref": transaction.ref,
        "currency": "NGN",
        "fullname": "",
        "phone": phone,
    }

    try:
        response = requests.post(url=url, headers=headers, json=json)
        if response.status_code == 200:
            transaction.status = response.json()['data']['status']

            serializer = TransactionSerializer(transaction)

            context = {
                'status': True,
                'data': {
                    ** serializer.data,
                    'charged_amount': response.json()['data']['charged_amount'],
                    'transaction_fee': response.json()['data']['app_fee'],
                },
                'meta': {
                    'mode': response.json()['meta']['authorization']['mode'],
                    'code': response.json()['meta']['authorization']['note']
                }
            }

            return Response(context, status=status.HTTP_200_OK)
    except requests.exceptions.ConnectTimeout:
        context = {
            "status": False,
            "message": "Connection Timed Out"
        }
        return Response(context)
# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# END WITHDRAW

# START TRANSACTION
# ---------------------------------------------------------------------------------------------------------------------------------------------------------
@api_view(['GET', 'POST'])
# @permission_classes([IsAuthenticated])
# @roles_required(['is_vendor', 'is_customer'])
def transaction_history(request, phone):
    try:
        initiator = get_object_or_404(User, phone=phone)
    except Http404:
        return Response({"status": False, "message": "Resource not Found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        transactions = Transaction.objects.filter(sender=initiator).order_by("created_at")
        paginator = Paginator(transactions, per_page=10)
        page_number = request.GET.get('page', 1)
        transactions = paginator.get_page(page_number)
        serializer = TransactionSerializer(transactions, many=True)

        context = {
            "status": True,
            "data": serializer.data,
            "current_page": page_number,
            "total_pages": paginator.num_pages
        }

        return Response(context, status=status.HTTP_200_OK)

    elif request.method == "POST":
        search_string = request.data.get('search-string', None)

        if search_string is None:
            return Response({"status": False, "message": "Bad Request"}, status=status.HTTP_400_BAD_REQUEST)

        transactions = Transaction.objects.filter(sender=initiator)
        transactions = transactions.filter(
            Q(ref__contains=search_string) |
            Q(transaction_type__icontains=search_string)|
            Q(status__icontains=search_string)
        ).order_by("created_at")
        
        paginator = Paginator(transactions, per_page=10)
        page_number = request.GET.get('page', 1)
        transactions = paginator.get_page(page_number)
        serializer = TransactionSerializer(transactions, many=True)

        context = {
            "status": True,
            "data": serializer.data,
            "current_page": page_number,
            "total_pages": paginator.num_pages,
            "search_string": search_string
        }

        return Response(context, status=status.HTTP_200_OK)
# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# END TRANSACTION


# FLUTTERWAVE INTEGRATION
# START TOPUP        
# ---------------------------------------------------------------------------------------------------------------------------------------------------------
@api_view(['POST'])
# @authentication_classes([IsAuthenticated])
# @roles_required(['is_vendor', 'is_customer'])
def ussd_topup(request):
    account_bank = request.data.get('account_bank', None)
    phone = request.data.get('phone', None)
    email = request.data.get('email', None)
    amount = request.data.get('amount', None)

    if(account_bank is None or phone is None or email is None or amount is None):
        context = {
            "status": False,
            "message": "Bad Request"
        }
        return Response(context, status=status.HTTP_400_BAD_REQUEST)
    
    user = get_object_or_404(User, phone=phone)
    transaction = Transaction.objects.create(sender=user, amount=amount, transaction_type="topup")

    url = "https://api.flutterwave.com/v3/charges?type=ussd"

    token = settings.FLUTTERWAVE_SECRET_KEY
    headers = {
        "Authorization": f"Bearer {token}"
    }
    json = {
        "account_bank": "057", # To be change to actual variable.
        "amount": amount,
        "email": email,
        "tx_ref": transaction.ref,
        "currency": "NGN",
        "fullname": "",
        "phone": phone,
    }

    try:
        response = requests.post(url=url, headers=headers, json=json)
        if response.status_code == 200:
            transaction.status = response.json()['data']['status']
            transaction.transaction_fee = response.json()['data']['app_fee']
            transaction.save()

            serializer = TransactionSerializer(transaction)

            context = {
                'status': True,
                'data': {
                    ** serializer.data,
                    'charged_amount': response.json()['data']['charged_amount'],
                    'transaction_fee': response.json()['data']['app_fee'],
                },
                'meta': {
                    'mode': response.json()['meta']['authorization']['mode'],
                    'code': response.json()['meta']['authorization']['note']
                }
            }

            return Response(context, status=status.HTTP_200_OK)
    except requests.exceptions.ConnectTimeout:
        transaction.status = "pending"
        transaction.save()
        context = {
            "status": False,
            "message": "Connection Timed Out"
        }
        return Response(context)
    except Exception:
        transaction.status = "failed"
        transaction.save()
        context = {
            "status": False,
            "message": "An Error Occured."
        }
        return Response(context)

@api_view(['POST'])
# @authentication_classes([IsAuthenticated])
# @roles_required(['is_vendor', 'is_customer'])
def bank_transfer_topup(request):
    phone = request.data.get('phone', None)
    email = request.data.get('email', None)
    amount = request.data.get('amount', None)

    if(phone is None or email is None or amount is None):
        context = {
            "status": False,
            "message": "Bad Request"
        }
        return Response(context, status=status.HTTP_400_BAD_REQUEST)
    
    user = get_object_or_404(User, phone=phone, email=email)
    transaction = Transaction.objects.create(sender=user, amount=amount, transaction_type="topup")
    
    url = "https://api.flutterwave.com/v3/charges?type=bank_transfer"

    token = settings.FLUTTERWAVE_SECRET_KEY
    headers = {
        "Authorization": f"Bearer {token}"
    }
    json = {
        "tx_ref": transaction.ref,
        "amount": amount,
        "email": email,
        "currency": "NGN",
        "fullname": "",
        "phone": phone,
        "narration": "CampusPay"
    }

    try:
        response = requests.post(url=url, headers=headers, json=json)
        if response.status_code == 200:
            transaction.status = "pending"
            transaction.save()

            serializer = TransactionSerializer(transaction)

            context = {
                'status': True,
                'data': {
                    ** serializer.data,
                },
                'meta': {
                    'mode': response.json()['meta']['authorization']['mode'],
                    'transfer_account': response.json()['meta']['authorization']['transfer_account'],
                    'transfer_bank': response.json()['meta']['authorization']['transfer_bank'],
                    'transfer_amount': response.json()['meta']['authorization']['transfer_amount'],
                    'account_expiration': response.json()['meta']['authorization']['account_expiration']
                }
            }

            return Response(context, status=status.HTTP_200_OK)
    except requests.exceptions.ConnectTimeout:
        context = {
            "status": False,
            "message": "Connection Timed Out"
        }
        return Response(context)
    except Exception as error:
        print(error)
        context = {
            "status": False,
            "message": "An Error Occured."
        }
        return Response(context)
    
@api_view(['POST'])
# @authentication_classes([IsAuthenticated])
# @roles_required(['is_vendor', 'is_customer'])
def direct_bank_charge_topup(request):
    account_bank = request.data.get('account_bank', None)
    account_number = request.data.get('account_number', None)
    phone = request.data.get('phone', None)
    email = request.data.get('email', None)
    amount = request.data.get('amount', None)

    if(account_bank is None or account_number is None or phone is None or email is None or amount is None):
        context = {
            "status": False,
            "message": "Bad Request"
        }
        return Response(context, status=status.HTTP_400_BAD_REQUEST)
    
    user = get_object_or_404(User, phone=phone)
    transaction = Transaction.objects.create(sender=user, amount=amount, transaction_type="topup")
    
    url = "https://api.flutterwave.com/v3/charges?type=account"

    token = settings.FLUTTERWAVE_SECRET_KEY
    headers = {
        "Authorization": f"Bearer {token}"
    }
    json = {
        "tx_ref": transaction.ref,
        "amount": amount,
        "email": email,
        "account_bank": account_bank,
        "account_number": account_number,
        "currency": "NGN",
        "fullname": "",
        "phone": phone,
        "narration": "CamPay"
    }

    try:
        response = requests.post(url=url, headers=headers, json=json)
        if response.status_code == 200:
            transaction.status = response.json()['data']['status']
            transaction.transaction_fee = response.json()['data']['app_fee']
            transaction.save()

            serializer = TransactionSerializer(transaction)

            context = {
                'status': True,
                'data': {
                    ** serializer.data,
                    'charged_amount': response.json()['data']['charged_amount'],
                    'transaction_fee': response.json()['data']['app_fee'],
                },
                'account': {
                    'account_number': response.json()['data']['account']['account_number'],
                    'account_name': response.json()['data']['account']['account_name'],
                    'bank_code': response.json()['data']['account']['bank_code'],
                },
                'meta': {
                    'mode': response.json()['meta']['authorization']['mode'],
                    'validate_instructions': response.json()['meta']['authorization']['validate_instructions'],
                }
            }

            return Response(context, status=status.HTTP_200_OK)
    except requests.exceptions.ConnectTimeout:
        context = {
            "status": False,
            "message": "Connection Timed Out"
        }
        return Response(context)
    except Exception:
        context = {
            "status": False,
            "message": "An Error Occured."
        }
        return Response(context)
# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# END TOPUP



# ADMIN ENDPOINTS
# ---------------------------------------------------------------------------------------------------------------
@api_view(['GET'])
# @authentication_classes([IsAuthenticated])
# @roles_required(['is_vendor', 'is_customer'])
def verify_transaction(request, ref):
    transaction = get_object_or_404(Transaction, ref=ref)
    
    response = transaction.verify_transaction()
    if response['status']:
        return Response(response, status=status.HTTP_200_OK)
    else:
        return Response(response, status=status.HTTP_200_OK)

# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# END VERIFY TRANSACTIONS