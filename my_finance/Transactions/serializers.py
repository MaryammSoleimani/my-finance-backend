# backend/Transactions/serializers.py
from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'date', 'amount', 'desc', 'kind', 'account', 'account_name', 'category', 'category_name',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']