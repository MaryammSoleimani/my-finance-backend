from decimal import Decimal
from Accounts.models import Account
from Transactions.models import Transaction
from categories.models import Category


class HealthScoreCalculator:
    def __init__(self, user):
        self.user = user
        self.accounts = Account.objects.filter(owner=user)
        self.transactions = Transaction.objects.filter(user=user)
        self.categories = Category.objects.filter(user=user)

    def calculate(self):
        """محاسبه امتیاز سلامت مالی 0-100"""
        score = 0

        # 1. نسبت بدهی به دارایی (30 امتیاز)
        total_assets = sum(a.balance for a in self.accounts if not a.is_debt)
        total_liabilities = sum(a.balance for a in self.accounts if a.is_debt)

        if total_assets > 0:
            debt_ratio = total_liabilities / total_assets
            if debt_ratio < 0.3:
                score += 30
            elif debt_ratio < 0.5:
                score += 20
            elif debt_ratio < 0.7:
                score += 10
            # بیشتر از 0.7 = 0 امتیاز

        # 2. نقدینگی (20 امتیاز)
        liquid_assets = sum(a.balance for a in self.accounts if not a.is_debt and a.type == 'account')
        monthly_expenses = sum(t.amount for t in self.transactions.filter(kind='expense')) / 3  # میانگین 3 ماه

        if monthly_expenses > 0:
            emergency_fund_months = liquid_assets / monthly_expenses
            if emergency_fund_months >= 6:
                score += 20
            elif emergency_fund_months >= 3:
                score += 15
            elif emergency_fund_months >= 1:
                score += 10

        # 3. تنوع دارایی (20 امتیاز)
        unique_types = set(a.type for a in self.accounts)
        if len(unique_types) >= 3:
            score += 20
        elif len(unique_types) == 2:
            score += 15
        elif len(unique_types) == 1:
            score += 10

        # 4. پس‌انداز ماهانه (15 امتیاز)
        monthly_income = sum(t.amount for t in self.transactions.filter(kind='income')) / 3
        monthly_savings = monthly_income - monthly_expenses
        if monthly_savings > 0:
            savings_rate = monthly_savings / monthly_income if monthly_income > 0 else 0
            if savings_rate >= 0.3:
                score += 15
            elif savings_rate >= 0.2:
                score += 10
            elif savings_rate >= 0.1:
                score += 5

        # 5. رشد دارایی‌ها (15 امتیاز)
        growth_assets = sum(a.balance for a in self.accounts if not a.is_debt)
        if growth_assets >= 10000:
            score += 15
        elif growth_assets >= 5000:
            score += 10
        elif growth_assets >= 1000:
            score += 5

        # محدود کردن بین 0 تا 100
        score = min(max(score, 0), 100)

        # تعیین نمره
        if score >= 90:
            grade = 'A'
        elif score >= 75:
            grade = 'B'
        elif score >= 60:
            grade = 'C'
        elif score >= 40:
            grade = 'D'
        else:
            grade = 'F'

        return {
            'score': score,
            'grade': grade,
            'breakdown': {
                'debt_ratio': 30,
                'liquidity': 20,
                'diversification': 20,
                'savings_rate': 15,
                'growth': 15
            }
        }