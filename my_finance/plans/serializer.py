from rest_framework import serializers
from .models import Asset, CashFlow, Event
import jdatetime

class AssetSerializer(serializers.ModelSerializer):
    amount_toman = serializers.SerializerMethodField()
    created_at_shamsi = serializers.SerializerMethodField()
    updated_at_shamsi = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = ['id', 'name', 'amount', 'amount_toman', 'asset_type', 'growth_rate',
                  'annual_income_rate', 'liquidity_penalty', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_amount_toman(self, obj):
        return float(obj.amount)


class CashFlowSerializer(serializers.ModelSerializer):
    amount_toman = serializers.SerializerMethodField()

    class Meta:
        model = CashFlow
        fields = ['id', 'name', 'amount', 'amount_toman', 'flow_type', 'frequency',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_amount_toman(self, obj):
        return float(obj.amount)

class EventSerializer(serializers.ModelSerializer):
    cash_flow_name = serializers.CharField(source='cash_flow.name', read_only=True, default=None)
    amount_toman = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'name', 'event_type', 'month', 'cash_flow', 'cash_flow_name',
                  'amount', 'amount_toman', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_amount_toman(self, obj):
        return float(obj.amount)
