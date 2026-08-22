from django.db import models
from django.contrib.auth.models import User


class Asset(models.Model):
    ASSET_TYPES = (
        ('liquid', 'Liquid'),
        ('illiquid', 'Illiquid'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    asset_type = models.CharField(max_length=10, choices=ASSET_TYPES, default='liquid')
    growth_rate = models.FloatField(default=0)

class CashFlow(models.Model):
    FLOW_TYPES = (
        ('in', 'Income'),
        ('out', 'Expense'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    flow_type = models.CharField(max_length=3, choices=FLOW_TYPES)

class PlanEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    month_offset = models.IntegerField()
    impact_amount = models.DecimalField(max_digits=15, decimal_places=2)