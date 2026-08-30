from decimal import Decimal
from Transactions.models import Transaction
from Accounts.models import Account


class SmartGoalCalculator:
    def __init__(self, user, goal_amount, months):
        self.user = user
        self.goal_amount = Decimal(str(goal_amount))
        self.months = months
        self.transactions = Transaction.objects.filter(user=user)
        self.accounts = Account.objects.filter(owner=user)

    def calculate(self):
        """محاسبه امکان‌پذیری هدف"""
        # میانگین پس‌انداز ماهانه - تبدیل به Decimal
        monthly_income = sum(t.amount for t in self.transactions.filter(kind='income')) / 3
        monthly_expenses = sum(t.amount for t in self.transactions.filter(kind='expense')) / 3

        # تبدیل به Decimal
        monthly_income = Decimal(str(monthly_income))
        monthly_expenses = Decimal(str(monthly_expenses))
        monthly_savings = monthly_income - monthly_expenses

        # پس‌انداز فعلی - تبدیل به Decimal
        current_savings = sum(a.balance for a in self.accounts if not a.is_debt)
        current_savings = Decimal(str(current_savings))

        # پیش‌بینی
        projected_savings = current_savings + (monthly_savings * self.months)
        needed_monthly_savings = (self.goal_amount - current_savings) / self.months if self.months > 0 else Decimal('0')

        # امکان‌پذیری
        is_feasible = projected_savings >= self.goal_amount
        additional_savings_needed = max(Decimal('0'), needed_monthly_savings - monthly_savings)

        return {
            'is_feasible': is_feasible,
            'current_savings': float(current_savings),
            'monthly_savings': float(monthly_savings),
            'needed_monthly_savings': float(needed_monthly_savings),
            'additional_savings_needed': float(additional_savings_needed),
            'projected_savings': float(projected_savings)
        }