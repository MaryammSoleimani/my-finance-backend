from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Sum
from .models import Budget
from Transactions.models import Transaction

@api_view(['GET'])
def get_budget_status(request):
    from django.utils import timezone
    now = timezone.now()
    month = request.query_params.get('month', now.month)
    year = request.query_params.get('year', now.year)

    budgets = Budget.objects.filter(month=month, year=year)
    results = []

    for b in budgets:
        spent = Transaction.objects.filter(
            category=b.category,
            kind='expense',
            date__month=month,
            date__year=year
        ).aggregate(total=Sum('amount'))['total'] or 0

        percent = (float(spent) / float(b.amount)) * 100 if b.amount > 0 else 0

        results.append({
            'category': b.category.name,
            'budget': float(b.amount),
            'spent': float(spent),
            'percent': round(percent, 1),
            'color': 'green' if percent <= 100 else 'red'
        })
    return Response(results)