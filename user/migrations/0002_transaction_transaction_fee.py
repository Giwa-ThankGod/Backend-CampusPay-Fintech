# Generated by Django 4.2.2 on 2023-10-25 14:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='transaction_fee',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=9),
        ),
    ]