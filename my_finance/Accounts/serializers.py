from rest_framework import serializers
from .models import Account
import jdatetime

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'name', 'balance', 'is_debt','type', 'color']
        read_only_fields = ['id']

        def get_balance_toman(self, obj):
            return float(obj.balance)