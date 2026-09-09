from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from Accounts.models import Account
from categories.models import Category


class Transaction(models.Model):
    KIND_CHOICES = [
        ('expense', 'Expense'),
        ('income', 'Income'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    desc = models.CharField(max_length=255)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default='expense')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='transactions')
    # Imported historical statements are already reflected in the account's
    # current balance, so their lifecycle must not apply balance/budget deltas.
    affects_financial_totals = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transactions'
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.desc} - {self.amount}"
