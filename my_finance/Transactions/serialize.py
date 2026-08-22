from rest_framework import serializers
from .models import Transaction
from Category.models import Category

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class TransactionSerializer(serializers.ModelSerializer):
    # برای اینکه نام دسته‌بندی را به جای ID ببینیم
    category_name = serializers.ReadOnlyField(source='category.name')
    # برای اینکه نام اکانت را ببینیم
    account_name = serializers.ReadOnlyField(source='account.name')

    class Meta:
        model = Transaction
        fields = [
            'id', 'date', 'amount', 'desc',
            'kind', 'account', 'account_name',
            'category', 'category_name'
        ]