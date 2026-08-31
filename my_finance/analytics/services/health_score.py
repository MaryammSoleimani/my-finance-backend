from decimal import Decimal
from django.db.models import Sum
from Accounts.models import Account
from Transactions.models import Transaction

class HealthScoreCalculator:
    def __init__(self, user):
        self.user = user
        self.accounts = Account.objects.filter(owner=user)
        self.transactions = Transaction.objects.filter(user=user)

    def calculate(self):
        """محاسبه امتیاز سلامت مالی 0-100 با جزئیات کامل"""
        score = 0
        details = {}

        # 1. نسبت بدهی به دارایی (30 امتیاز)
        total_assets = self.accounts.filter(is_debt=False).aggregate(Sum('balance'))['balance__sum'] or 0
        total_liabilities = self.accounts.filter(is_debt=True).aggregate(Sum('balance'))['balance__sum'] or 0

        total_assets = Decimal(str(total_assets))
        total_liabilities = Decimal(str(total_liabilities))

        if total_assets > 0:
            debt_ratio = total_liabilities / total_assets
            if debt_ratio < Decimal('0.3'):
                score += 30
                details['debt_ratio'] = {'score': 30, 'status': 'good', 'label': 'Low Debt'}
            elif debt_ratio < Decimal('0.5'):
                score += 20
                details['debt_ratio'] = {'score': 20, 'status': 'ok', 'label': 'Moderate Debt'}
            elif debt_ratio < Decimal('0.7'):
                score += 10
                details['debt_ratio'] = {'score': 10, 'status': 'warning', 'label': 'High Debt'}
            else:
                details['debt_ratio'] = {'score': 0, 'status': 'danger', 'label': 'Very High Debt'}
        else:
            details['debt_ratio'] = {'score': 0, 'status': 'danger', 'label': 'No Data'}

        # 2. نقدینگی (20 امتیاز)
        liquid_assets = self.accounts.filter(is_debt=False, type='account').aggregate(Sum('balance'))['balance__sum'] or 0
        monthly_expenses = self.transactions.filter(kind='expense').aggregate(Sum('amount'))['amount__sum'] or 0

        liquid_assets = Decimal(str(liquid_assets))
        monthly_expenses = Decimal(str(monthly_expenses))

        if monthly_expenses > 0:
            avg_monthly_expenses = monthly_expenses / 3
            emergency_fund_months = liquid_assets / avg_monthly_expenses if avg_monthly_expenses > 0 else 0

            if emergency_fund_months >= 6:
                score += 20
                details['liquidity'] = {'score': 20, 'status': 'good', 'label': '6+ Months'}
            elif emergency_fund_months >= 3:
                score += 15
                details['liquidity'] = {'score': 15, 'status': 'ok', 'label': '3-6 Months'}
            elif emergency_fund_months >= 1:
                score += 10
                details['liquidity'] = {'score': 10, 'status': 'warning', 'label': '1-3 Months'}
            else:
                details['liquidity'] = {'score': 0, 'status': 'danger', 'label': '< 1 Month'}
        else:
            details['liquidity'] = {'score': 0, 'status': 'danger', 'label': 'No Data'}

        # 3. تنوع دارایی (20 امتیاز)
        unique_types = set(self.accounts.values_list('type', flat=True))
        if len(unique_types) >= 3:
            score += 20
            details['diversification'] = {'score': 20, 'status': 'good', 'label': 'Well Diversified'}
        elif len(unique_types) == 2:
            score += 15
            details['diversification'] = {'score': 15, 'status': 'ok', 'label': 'Some Diversification'}
        elif len(unique_types) == 1:
            score += 10
            details['diversification'] = {'score': 10, 'status': 'warning', 'label': 'Low Diversification'}
        else:
            details['diversification'] = {'score': 0, 'status': 'danger', 'label': 'No Assets'}

        # 4. پس‌انداز ماهانه (15 امتیاز)
        monthly_income = self.transactions.filter(kind='income').aggregate(Sum('amount'))['amount__sum'] or 0
        monthly_expenses_total = self.transactions.filter(kind='expense').aggregate(Sum('amount'))['amount__sum'] or 0

        monthly_income = Decimal(str(monthly_income))
        monthly_expenses_total = Decimal(str(monthly_expenses_total))

        avg_monthly_income = monthly_income / 3
        avg_monthly_expenses = monthly_expenses_total / 3
        monthly_savings = avg_monthly_income - avg_monthly_expenses

        if monthly_savings > 0:
            savings_rate = monthly_savings / avg_monthly_income if avg_monthly_income > 0 else 0
            if savings_rate >= Decimal('0.3'):
                score += 15
                details['savings_rate'] = {'score': 15, 'status': 'good', 'label': '30%+ Savings'}
            elif savings_rate >= Decimal('0.2'):
                score += 10
                details['savings_rate'] = {'score': 10, 'status': 'ok', 'label': '20-30% Savings'}
            elif savings_rate >= Decimal('0.1'):
                score += 5
                details['savings_rate'] = {'score': 5, 'status': 'warning', 'label': '10-20% Savings'}
            else:
                details['savings_rate'] = {'score': 0, 'status': 'danger', 'label': '< 10% Savings'}
        else:
            details['savings_rate'] = {'score': 0, 'status': 'danger', 'label': 'No Savings'}

        # 5. رشد دارایی‌ها (15 امتیاز)
        growth_assets = self.accounts.filter(is_debt=False).aggregate(Sum('balance'))['balance__sum'] or 0
        growth_assets = Decimal(str(growth_assets))

        if growth_assets >= 10000:
            score += 15
            details['growth'] = {'score': 15, 'status': 'good', 'label': '10k+ Assets'}
        elif growth_assets >= 5000:
            score += 10
            details['growth'] = {'score': 10, 'status': 'ok', 'label': '5k-10k Assets'}
        elif growth_assets >= 1000:
            score += 5
            details['growth'] = {'score': 5, 'status': 'warning', 'label': '1k-5k Assets'}
        else:
            details['growth'] = {'score': 0, 'status': 'danger', 'label': '< 1k Assets'}

        # محدود کردن بین 0 تا 100
        score = min(max(score, 0), 100)

        # تعیین نمره
        if score >= 90:
            grade = 'A'
            message = 'Excellent!'
        elif score >= 75:
            grade = 'B'
            message = 'Good!'
        elif score >= 60:
            grade = 'C'
            message = 'Fair'
        elif score >= 40:
            grade = 'D'
            message = 'Needs Improvement'
        else:
            grade = 'F'
            message = 'At Risk'

        return {
            'score': score,
            'grade': grade,
            'message': message,
            'color': self.get_color(score),
            'details': details
        }

    def get_color(self, score):
        if score >= 90:
            return '#10b981'
        elif score >= 75:
            return '#3b82f6'
        elif score >= 60:
            return '#f59e0b'
        elif score >= 40:
            return '#f97316'
        return '#ef4444'