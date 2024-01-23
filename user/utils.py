import os
import qrcode
import pyotp
from io import BytesIO
from django.core.files import File
from random import randint
from datetime import date

os.environ['otp-secret'] = pyotp.random_base32()

def generate_ID(vendor=False, customer=False):
    lowest_digit = 00000
    highest_digit = 99999
    number = randint(lowest_digit, highest_digit)
    year = date.today().strftime("%y")

    if vendor:
        return f"VEND{year}{number}"
    else:
        return f"CUST{year}{number}"


def generate_qrcode(data, fg='black', bg='white', box_size=25):
    QR = qrcode.QRCode(
        version = 1,
        box_size= box_size,
        border = 5
    )

    # Add data to Qrcode instance
    QR.add_data(data)

    # Ensures entire dimension of the QRcode is utilized.
    QR.make(fit=True)

    # Converts the QRcode object into an image.
    img = QR.make_image(
        fill_color = fg,
        back_color = bg
    )

    filename = data['sender']

    buffer = BytesIO()
    img.save(buffer)
    buffer.seek(0)

    qrcode_image = File(buffer, name=f"{filename}.jpg")

    return qrcode_image


def generate_otp():
    otp_secret = os.environ.get('otp-secret')
    otp_generator = pyotp.TOTP(otp_secret, interval=30)
    otp = otp_generator.now()
    return otp