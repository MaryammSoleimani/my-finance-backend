from rest_framework import serializers
from .models import Budget, BudgetTransaction
from categories.models import Category


class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    spent_amount = serializers.SerializerMethodField()
    percentage_used = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = ['id', 'name', 'amount', 'reset_period', 'category', 'category_name', 'category_color', 'spent_amount',
                  'percentage_used', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_spent_amount(self, obj):
        from django.db.models import Sum
        from Transactions.models import Transaction
        from datetime import datetime

        if obj.reset_period == 'monthly':
            start_date = datetime.now().replace(day=1)
        else:
            start_date = datetime.now().replace(month=1, day=1)

        total = Transaction.objects.filter(
            category=obj.category,
            kind='expense',
            date__gte=start_date
        ).aggregate(total=Sum('amount'))['total'] or 0

        return float(total)

    def get_percentage_used(self, obj):
        spent = self.get_spent_amount(obj)
        if obj.amount > 0:
            return round((spent / float(obj.amount)) * 100, 2)
        return 0