from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Category
from .serializers import CategorySerializer
from Transactions.models import Transaction
from budget.models import Budget
from django.db.models import Count


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def usage_count(self, request, pk=None):
        category = self.get_object()

        print("========== USAGE COUNT ==========")
        print("Request user:", request.user)
        print("Request user ID:", request.user.id)
        print("Category:", category.id, category.name)
        print("Category user ID:", category.user_id)

        transaction_count = Transaction.objects.filter(
            category=category,
            user=request.user
        ).count()

        budget_count = Budget.objects.filter(
            category=category,
            user=request.user
        ).count()

        print("Transaction count:", transaction_count)
        print("Budget count:", budget_count)
        print("=================================")

        return Response({
            'transaction_count': transaction_count,
            'budget_count': budget_count,
            'total_count': transaction_count + budget_count
        })