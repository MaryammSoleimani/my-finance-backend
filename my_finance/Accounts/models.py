from django.contrib.auth.models import User
from django.db import models

# Create your models here.


class Account(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    is_debt = models.BooleanField(default=False)
    color = models.CharField(max_length=7, default='#3b82f6')


    ACCOUNT = "account"  #regular account
    INVESTMENT = "investment"
    CARD = "card"
    Account_type ={
        ACCOUNT : 'Account',
        INVESTMENT : 'Investment',
        CARD : 'Card',
    }
    type = models.CharField(max_length=10, choices=Account_type, default=ACCOUNT)

    def __str__(self):
        status = "Liability" if self.is_debt else "Asset"
        return f"{self.name} ({status})"


