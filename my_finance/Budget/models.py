from django.db import models
from django.db.models import ForeignKey
from Accounts.models import Account
from Category.models import Category

# Create your models here.


class Budget(models.Model):
    category = ForeignKey(Category, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    month = models.PositiveIntegerField()  # 1 تا 12
    year = models.PositiveIntegerField()  # مثلا 2024

    class Meta:
        unique_together = ('category', 'month', 'year')

    def __str__(self):
        return f"{self.category.name} - {self.month}/{self.year}: {self.amount}"