from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from .models import Transaction
from .serialize import *
from rest_framework import viewsets
from django.utils.timezone import now
from datetime import timedelta
from django.db.models.functions import TruncDay
from django.utils import timezone
from django.db.models import Sum, Q
from collections import defaultdict
import calendar
from datetime import timedelta, date


def get_date_range(period):
    today = timezone.now().date()

    days_since_saturday = (today.weekday() + 2) % 7
    start_of_current_week = today - timedelta(days=days_since_saturday)

    if period == 'current-week':
        return start_of_current_week, today

    elif period == 'last-week':
        end_of_last_week = start_of_current_week - timedelta(days=1)
        start_of_last_week = end_of_last_week - timedelta(days=6)
        return start_of_last_week, end_of_last_week

    elif period == 'current-month' or period == 'per-day':
        return today.replace(day=1), today

    elif period == 'last-month':
        last_month_end = today.replace(day=1) - timedelta(days=1)
        return last_month_end.replace(day=1), last_month_end

    elif period == 'today':
        return today, today

    elif period == 'yesterday':
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday

    elif period == 'year-to-date':
        return today.replace(month=1, day=1), today

    elif period == 'last-year':
        last_year = today.year - 1
        return date(last_year, 1, 1), date(last_year, 12, 31)

    elif period == 'all-time':
        first_transaction = Transaction.objects.order_by('date').first()
        if first_transaction:
            start_date = first_transaction.date
        else:
            start_date = today  # اگر تراکنشی نبود، همان امروز
        return start_date, today
    return start_of_current_week, today


class CategoryExpensesChart(APIView):

    def get(self, request):
        period = request.GET.get('period', 'current-month')
        category_name = request.GET.get('category', None)
        start, end = get_date_range(period)

        queryset = Transaction.objects.filter(kind='expense')
        if start and end:
            queryset = queryset.filter(date__range=[start, end])

        if category_name:
            queryset = queryset.filter(category__name=category_name)

        stats = (
            queryset.values('category__name', 'category__color')
            .annotate(total_amount=Sum('amount'))
            .order_by('-total_amount')
        )
        data = {
            'labels': [item['category__name'] for item in stats],
            'series': [float(item['total_amount']) for item in stats],
            'colors': [item['category__color'] for item in stats] # ارسال لیست رنگ‌ها
        }

        if not stats.exists():
            return Response({'labels': [], 'series': [], 'colors': []})

        return Response(data)


class DailyExpensesChart(APIView):
    def get(self, request):
        period = request.GET.get('period', 'current-week')
        category_name = request.GET.get('category', None)
        start, end = get_date_range(period)

        base_filter = Q(kind='expense')
        if start and end:
            base_filter &= Q(date__range=[start, end])

        if category_name:
            base_filter &= Q(category__name=category_name)

        if period == 'per-day':
            _, num_days = calendar.monthrange(start.year, start.month)
            labels = [str(day) for day in range(1, num_days + 1)]
            values = []
            for day in range(1, num_days + 1):
                curr_date = start.replace(day=day)
                total = Transaction.objects.filter(base_filter, date=curr_date).aggregate(Sum('amount'))[
                            'amount__sum'] or 0
                values.append(float(total))
            return Response({'categories': labels, 'data': values})

        elif period in ['year-to-date', 'last-year']:
            labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            values = []
            for month in range(1, 13):
                total = Transaction.objects.filter(
                    base_filter,
                    date__year=start.year,
                    date__month=month
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                values.append(float(total))
            return Response({'categories': labels, 'data': values})

        elif period == 'all-time':
            all_time_filter = Q(kind='expense')
            if category_name:
                all_time_filter &= Q(category__name=category_name)

            stats = Transaction.objects.filter(all_time_filter) \
                .values('date__year') \
                .annotate(total=Sum('amount')) \
                .order_by('date__year')

            return Response({
                'categories': [str(item['date__year']) for item in stats] or ["No Data"],
                'data': [float(item['total']) for item in stats] or [0]
            })

        else:
            labels, values = [], []
            num_days = (end - start).days + 1
            if num_days > 31: num_days = 7

            for i in range(num_days):
                curr_date = start + timedelta(days=i)
                labels.append(curr_date.strftime('%a'))
                total = Transaction.objects.filter(base_filter, date=curr_date).aggregate(Sum('amount'))[
                            'amount__sum'] or 0
                values.append(float(total))

            return Response({'categories': labels, 'data': values})


class GroupedTransactionsView(APIView):
    def get(self, request):
        period = request.GET.get('period', 'current-month')
        category_name = request.GET.get('category', None)
        is_per_day = (period == 'per-day')

        start, end = get_date_range(period)
        queryset = Transaction.objects.filter(
            date__range=[start, end]).select_related('category', 'account')

        if category_name:
            queryset = queryset.filter(category__name=category_name)

        queryset = queryset.order_by('-date')

        grouped_data = defaultdict(lambda: {'total_expense': 0, 'total_deposit': 0, 'items': []})

        for t in queryset:
            group_key = t.date.strftime('%Y-%m-%d') if is_per_day else (t.category.name if t.category else "Other")

            grouped_data[group_key]['items'].append({
                'desc': t.desc,
                'account': t.account.name if t.account else 'N/A',
                'date': t.date.strftime('%Y-%m-%d'),
                'amount': float(t.amount),
                'kind': t.kind
            })

            if t.kind == 'expense':
                grouped_data[group_key]['total_expense'] += float(t.amount)
            else:
                grouped_data[group_key]['total_deposit'] += float(t.amount)

        final_groups = []
        sorted_keys = sorted(grouped_data.keys(), reverse=True) if is_per_day else grouped_data.keys()

        for key in sorted_keys:
            final_groups.append({
                'category__name': key,
                'total_expense': grouped_data[key]['total_expense'],
                'total_deposit': grouped_data[key]['total_deposit'],
                'items': grouped_data[key]['items']
            })

        grand_totals = queryset.aggregate(
            total_expense=Sum('amount', filter=Q(kind='expense')),
            total_deposit=Sum('amount', filter=Q(kind='income'))
        )

        return Response({
            'groups': final_groups,
            'grand_total_expense': grand_totals['total_expense'] or 0,
            'grand_total_deposit': grand_totals['total_deposit'] or 0
        })

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer


class LatestTransactionsView(APIView):
    def get(self, request):
        transactions = Transaction.objects.filter(account__owner=request.user).order_by('-date')[:7]
        data = []
        for t in transactions:
            data.append({
                'id': t.id,
                'description': t.description,
                'amount': float(t.amount),
                'date': t.date,
                'kind': t.kind,
                'category_name': t.category.name if t.category else "Uncategorized",
                'account_name': t.account.name
            })
        return Response(data)