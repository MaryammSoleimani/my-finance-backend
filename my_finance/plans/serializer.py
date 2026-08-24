from rest_framework import serializers
from .models import Asset, CashFlow, Event


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['id', 'name', 'amount', 'asset_type', 'growth_rate', 'annual_income_rate', 'liquidity_penalty',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CashFlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashFlow
        fields = ['id', 'name', 'amount', 'flow_type', 'frequency', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class EventSerializer(serializers.ModelSerializer):
    cash_flow_name = serializers.CharField(source='cash_flow.name', read_only=True, default=None)

    class Meta:
        model = Event
        fields = ['id', 'name', 'event_type', 'month', 'cash_flow', 'cash_flow_name', 'amount', 'description',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']