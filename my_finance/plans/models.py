from django.db import models
from django.contrib.auth.models import User


class Asset(models.Model):
    ASSET_TYPES = [
        ('liquid', 'Liquid'),
        ('illiquid', 'Illiquid'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assets')
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    asset_type = models.CharField(max_length=50, choices=ASSET_TYPES, default='liquid')
    growth_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    annual_income_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    liquidity_penalty = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assets'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class CashFlow(models.Model):
    FLOW_TYPES = [
        ('in', 'Inflow'),
        ('out', 'Outflow'),
    ]

    FREQUENCIES = [
        ('monthly', 'Monthly'),
        ('weekly', 'Weekly'),
        ('yearly', 'Yearly'),
        ('one_time', 'One Time'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cash_flows')
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    flow_type = models.CharField(max_length=10, choices=FLOW_TYPES, default='in')
    frequency = models.CharField(max_length=50, choices=FREQUENCIES, default='monthly')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cash_flows'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Event(models.Model):
    EVENT_TYPES = [
        ('income_change', 'Income Change'),
        ('expense_change', 'Expense Change'),
        ('asset_transfer', 'Asset Transfer'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')
    name = models.CharField(max_length=255)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, default='income_change')
    month = models.IntegerField(default=1)
    cash_flow = models.ForeignKey(CashFlow, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'events'
        ordering = ['month']

    def __str__(self):
        return self.name