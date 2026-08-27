from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from django.db.models.functions import TruncDay
from datetime import datetime, timedelta

from categories.models import Category
from .models import Transaction
from .serializers import TransactionSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def grouped(self, request):
        period = request.query_params.get('period', 'current-month')
        category = request.query_params.get('category', '')

        transactions = Transaction.objects.filter(user=request.user)

        if period == 'current-month':
            start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0)
            transactions = transactions.filter(date__gte=start_date)
        elif period == 'last-month':
            today = datetime.now()
            first_day_current = today.replace(day=1, hour=0, minute=0, second=0)
            last_day_prev = first_day_current - timedelta(days=1)
            first_day_prev = last_day_prev.replace(day=1)
            transactions = transactions.filter(date__gte=first_day_prev, date__lte=last_day_prev)
        elif period == 'last-year':
            today = datetime.now()
            first_day_current_year = today.replace(month=1, day=1, hour=0, minute=0, second=0)
            last_day_prev_year = first_day_current_year - timedelta(days=1)
            first_day_prev_year = last_day_prev_year.replace(month=1, day=1)
            transactions = transactions.filter(date__gte=first_day_prev_year, date__lte=last_day_prev_year)
        elif period == 'all-time':
            pass
        elif period == 'per-day':
            pass

        if category and category != 'all':
            transactions = transactions.filter(category__name=category)

        groups = []
        categories = Category.objects.filter(user=request.user)

        for cat in categories:
            cat_transactions = transactions.filter(category=cat)
            total_expense = cat_transactions.filter(kind='expense').aggregate(total=Sum('amount'))['total'] or 0
            total_deposit = cat_transactions.filter(kind='income').aggregate(total=Sum('amount'))['total'] or 0

            if total_expense > 0 or total_deposit > 0:
                groups.append({
                    'category__name': cat.name,
                    'total_expense': float(total_expense),
                    'total_deposit': float(total_deposit),
                    'items': [
                        {
                            'id': t.id,
                            'desc': t.desc,
                            'amount': float(t.amount),
                            'date': t.date.strftime('%Y-%m-%d'),
                            'account': t.account.name,
                            'kind': t.kind,
                            'category': t.category.name
                        }
                        for t in cat_transactions[:10]
                    ]
                })

        grand_total_expense = sum(g['total_expense'] for g in groups)
        grand_total_deposit = sum(g['total_deposit'] for g in groups)

        return Response({
            'groups': groups,
            'grand_total_expense': grand_total_expense,
            'grand_total_deposit': grand_total_deposit
        })

    @action(detail=False, methods=['get'])
    def categories(self, request):
        categories = Category.objects.filter(user=request.user)

        data = [
            {
                'id': category.id,
                'name': category.name,
                'color': category.color,
            }
            for category in categories
        ]

        return Response(data)

    @action(detail=False, methods=['get'], url_path='category-expenses')
    def category_expenses(self, request):
        period = request.query_params.get('period', 'current-month')
        category = request.query_params.get('category', '')

        transactions = Transaction.objects.filter(user=request.user, kind='expense')

        if period == 'current-month':
            start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0)
            transactions = transactions.filter(date__gte=start_date)
        elif period == 'last-month':
            today = datetime.now()
            first_day_current = today.replace(day=1, hour=0, minute=0, second=0)
            last_day_prev = first_day_current - timedelta(days=1)
            first_day_prev = last_day_prev.replace(day=1)
            transactions = transactions.filter(date__gte=first_day_prev, date__lte=last_day_prev)
        elif period == 'last-year':
            today = datetime.now()
            first_day_current_year = today.replace(month=1, day=1, hour=0, minute=0, second=0)
            last_day_prev_year = first_day_current_year - timedelta(days=1)
            first_day_prev_year = last_day_prev_year.replace(month=1, day=1)
            transactions = transactions.filter(date__gte=first_day_prev_year, date__lte=last_day_prev_year)
        elif period == 'all-time':
            pass
        elif period == 'per-day':
            pass

        if category and category != 'all':
            transactions = transactions.filter(category__name=category)

        categories = Category.objects.filter(user=request.user)
        series = []
        labels = []
        colors = []

        for cat in categories:
            total = transactions.filter(category=cat).aggregate(total=Sum('amount'))['total'] or 0
            if total > 0:
                series.append(float(total))
                labels.append(cat.name)
                colors.append(cat.color)

        return Response({
            'series': series,
            'labels': labels,
            'colors': colors
        })

    @action(detail=False, methods=['get'], url_path='daily-expenses')
    def daily_expenses(self, request):
        period = request.query_params.get('period', 'current-month')
        category = request.query_params.get('category', '')

        transactions = Transaction.objects.filter(user=request.user, kind='expense')

        if period == 'current-month':
            start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0)
            transactions = transactions.filter(date__gte=start_date)
        elif period == 'last-month':
            today = datetime.now()
            first_day_current = today.replace(day=1, hour=0, minute=0, second=0)
            last_day_prev = first_day_current - timedelta(days=1)
            first_day_prev = last_day_prev.replace(day=1)
            transactions = transactions.filter(date__gte=first_day_prev, date__lte=last_day_prev)
        elif period == 'last-year':
            today = datetime.now()
            first_day_current_year = today.replace(month=1, day=1, hour=0, minute=0, second=0)
            last_day_prev_year = first_day_current_year - timedelta(days=1)
            first_day_prev_year = last_day_prev_year.replace(month=1, day=1)
            transactions = transactions.filter(date__gte=first_day_prev_year, date__lte=last_day_prev_year)
        elif period == 'all-time':
            pass
        elif period == 'per-day':
            pass

        if category and category != 'all':
            transactions = transactions.filter(category__name=category)

        daily_data = transactions.annotate(
            day=TruncDay('date')
        ).values('day').annotate(
            total=Sum('amount')
        ).order_by('day')

        data = []
        categories = []

        for item in daily_data:
            data.append(float(item['total']))
            categories.append(item['day'].strftime('%b %d'))

        return Response({
            'data': data,
            'categories': categories
        })

    @action(detail=False, methods=['get'])
    def latest(self, request):
        transactions = Transaction.objects.filter(user=request.user).order_by('-date', '-id')[:10]
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def years(self, request):
        years = Transaction.objects.filter(user=request.user).dates('date', 'year', order='DESC')
        return Response([str(y.year) for y in years])

    @action(detail=False, methods=['get'], url_path='category-deposits')
    def category_deposits(self, request):
        period = request.query_params.get('period', 'current-month')
        category = request.query_params.get('category', '')

        transactions = Transaction.objects.filter(user=request.user, kind='income')

        if period == 'current-month':
            start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0)
            transactions = transactions.filter(date__gte=start_date)
        elif period == 'last-month':
            today = datetime.now()
            first_day_current = today.replace(day=1, hour=0, minute=0, second=0)
            last_day_prev = first_day_current - timedelta(days=1)
            first_day_prev = last_day_prev.replace(day=1)
            transactions = transactions.filter(date__gte=first_day_prev, date__lte=last_day_prev)
        elif period == 'last-year':
            today = datetime.now()
            first_day_current_year = today.replace(month=1, day=1, hour=0, minute=0, second=0)
            last_day_prev_year = first_day_current_year - timedelta(days=1)
            first_day_prev_year = last_day_prev_year.replace(month=1, day=1)
            transactions = transactions.filter(date__gte=first_day_prev_year, date__lte=last_day_prev_year)
        elif period == 'all-time':
            pass
        elif period == 'per-day':
            pass

        if category and category != 'all':
            transactions = transactions.filter(category__name=category)

        categories = Category.objects.filter(user=request.user)
        series = []
        labels = []
        colors = []

        for cat in categories:
            total = transactions.filter(category=cat).aggregate(total=Sum('amount'))['total'] or 0
            if total > 0:
                series.append(float(total))
                labels.append(cat.name)
                colors.append(cat.color)

        return Response({
            'series': series,
            'labels': labels,
            'colors': colors
        })