from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Avg, StdDev
from Transactions.models import Transaction
from categories.models import Category

class AnomalyDetector:
    def __init__(self, user):
        self.user = user
        self.categories = Category.objects.filter(user=user)

    def detect(self):
        """تشخیص ناهنجاری در هزینه‌ها"""
        alerts = []
        today = datetime.now().date()

        # 3 ماه اخیر
        three_months_ago = today - timedelta(days=90)
        current_month_start = today.replace(day=1)

        # یک کوئری برای همه دسته‌ها
        transactions = Transaction.objects.filter(
            user=self.user,
            kind='expense',
            date__gte=three_months_ago
        )

        # گروه‌بندی بر اساس دسته و ماه
        from django.db.models.functions import TruncMonth
        monthly_data = transactions.annotate(
            month=TruncMonth('date')
        ).values('category', 'month').annotate(
            total=Sum('amount')
        ).order_by('category', 'month')

        # محاسبه میانگین و انحراف معیار برای هر دسته
        category_data = {}
        for item in monthly_data:
            cat_id = item['category']
            if cat_id not in category_data:
                category_data[cat_id] = []
            category_data[cat_id].append(float(item['total']))  # تبدیل به float

        for category in self.categories:
            if category.id in category_data:
                values = category_data[category.id]
                if len(values) > 1:
                    avg = sum(values) / len(values)
                    std = (sum((v - avg) ** 2 for v in values) / len(values)) ** 0.5

                    # هزینه ماه جاری
                    current_month_expense = Transaction.objects.filter(
                        user=self.user,
                        category=category,
                        kind='expense',
                        date__gte=current_month_start
                    ).aggregate(total=Sum('amount'))['total'] or 0

                    if current_month_expense > avg + (2 * std):
                        deviation = ((current_month_expense - avg) / avg) * 100
                        alerts.append({
                            'category': category.id,
                            'category_name': category.name,
                            'month': today.strftime('%B %Y'),
                            'expected_amount': avg,
                            'actual_amount': float(current_month_expense),
                            'deviation_percentage': deviation
                        })

        return alerts