from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from datetime import datetime
from decimal import Decimal
from .models import Budget, BudgetTransaction
from .serializers import BudgetSerializer
from Transactions.models import Transaction


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """دریافت خلاصه بودجه"""
        budgets = Budget.objects.filter(user=request.user)
        period = request.query_params.get('period', 'monthly')


        total_budget = sum(Decimal(str(b.amount)) for b in budgets)
        total_spent = Decimal('0')

        for budget in budgets:
            if period == 'monthly':
                start_date = datetime.now().replace(day=1)
            else:
                start_date = datetime.now().replace(month=1, day=1)

            spent = Transaction.objects.filter(
                category=budget.category,
                kind='expense',
                date__gte=start_date
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            total_spent += Decimal(str(spent))

        total_budget = float(total_budget)
        total_spent = float(total_spent)

        return Response({
            'total_budget': total_budget,
            'total_spent': total_spent,
            'remaining': total_budget - total_spent,
            'percentage_used': round((total_spent / total_budget) * 100, 2) if total_budget > 0 else 0,
            'budgets': BudgetSerializer(budgets, many=True).data
        })