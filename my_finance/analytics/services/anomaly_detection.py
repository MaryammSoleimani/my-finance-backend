from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Avg, StdDev
from Transactions.models import Transaction
from categories.models import Category


class AnomalyDetector:
    def __init__(self, user):
        self.user = user
        self.transactions = Transaction.objects.filter(user=user)
        self.categories = Category.objects.filter(user=user)

    def detect(self):
        """تشخیص ناهنجاری در هزینه‌ها"""
        alerts = []
        today = datetime.now().date()

        # 3 ماه اخیر
        three_months_ago = today - timedelta(days=90)
        current_month_start = today.replace(day=1, hour=0, minute=0, second=0)

        for category in self.categories:
            # میانگین هزینه 3 ماه اخیر
            historical = self.transactions.filter(
                category=category,
                kind='expense',
                date__gte=three_months_ago,
                date__lt=current_month_start
            ).aggregate(
                avg=Avg('amount'),
                std=StdDev('amount')
            )

            # هزینه ماه جاری
            current_month_expense = self.transactions.filter(
                category=category,
                kind='expense',
                date__gte=current_month_start
            ).aggregate(total=Sum('amount'))['total'] or 0

            if historical['avg'] and historical['avg'] > 0:
                expected = historical['avg']
                std_dev = historical['std'] or 0

                # اگر انحراف بیش از 2 برابر انحراف معیار است
                if current_month_expense > expected + (2 * std_dev):
                    deviation = ((current_month_expense - expected) / expected) * 100

                    alerts.append({
                        'category': category.id,
                        'category_name': category.name,
                        'month': today.strftime('%B %Y'),
                        'expected_amount': expected,
                        'actual_amount': current_month_expense,
                        'deviation_percentage': deviation
                    })

        return alerts