from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(
        source='account.name',
        read_only=True
    )

    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )

    amount_toman = serializers.SerializerMethodField()

    class Meta:
        model = Transaction

        fields = [
            'id',
            'date',
            'amount',
            'amount_toman',
            'desc',
            'kind',
            'account',
            'account_name',
            'category',
            'category_name',
            'created_at',
            'updated_at'
        ]

        read_only_fields = [
            'id',
            'amount_toman',
            'created_at',
            'updated_at'
        ]

    def get_amount_toman(self, obj):
        return float(obj.amount)