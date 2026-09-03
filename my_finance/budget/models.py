from django.db import models
from django.contrib.auth.models import User
from categories.models import Category


class Budget(models.Model):
    RESET_CHOICES = [
        ('monthly', 'Per Month'),
        ('yearly', 'Per Year'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    spent_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    reset_period = models.CharField(max_length=10, choices=RESET_CHOICES, default='monthly')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'budgets'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.amount}"


class BudgetTransaction(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='transactions')
    transaction = models.ForeignKey('Transactions.Transaction', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'budget_transactions'
        ordering = ['-date']

    def __str__(self):
        return f"{self.budget.name} - {self.amount}"