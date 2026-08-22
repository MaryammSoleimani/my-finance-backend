from django.db import models
from django.db.models import ForeignKey

from Accounts.models import Account
from Category.models import Category

# Create your models here.


class Transaction(models.Model):
    id = models.AutoField(primary_key=True)
    date = models.DateField()
    amount = models.FloatField()
    desc = models.CharField(max_length=200)
    INCOME = "income"
    EXPENSE = "expense"
    TRANS_KIND ={
        INCOME : 'Income',
        EXPENSE : 'Expense'
    }
    kind = models.CharField(max_length=7 , default=EXPENSE, choices=TRANS_KIND)
    account = ForeignKey(Account, on_delete=models.CASCADE)
    category = ForeignKey(Category, on_delete=models.CASCADE)

    def __str__(self):
        return self.desc