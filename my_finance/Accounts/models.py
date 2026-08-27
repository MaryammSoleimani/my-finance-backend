# backend/Accounts/models.py
from django.db import models
from django.contrib.auth.models import User


class Account(models.Model):
    ACCOUNT_TYPES = [
        ('account', 'Regular Account'),
        ('investment', 'Investment'),
        ('card', 'Credit Card'),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    is_debt = models.BooleanField(default=False)
    color = models.CharField(max_length=7, default='#3b82f6')
    type = models.CharField(max_length=50, choices=ACCOUNT_TYPES, default='account')

    class Meta:
        db_table = 'accounts'


    def __str__(self):
        return self.name