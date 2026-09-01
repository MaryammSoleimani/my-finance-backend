from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .services.gemini_service import GeminiService
from Accounts.models import Account
from Transactions.models import Transaction


class AssistantView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_message = request.data.get('message')
        if not user_message:
            return Response({'error': 'Message is required'}, status=400)

        # جمع‌آوری داده‌های کاربر
        user_data = self._get_user_data(request.user)

        # دریافت پاسخ از Gemini
        try:
            service = GeminiService()
            response = service.get_response(user_message, user_data)
            return Response({'response': response})
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    def _get_user_data(self, user):
        """جمع‌آوری داده‌های مالی کاربر"""
        accounts = Account.objects.filter(owner=user)
        transactions = Transaction.objects.filter(user=user)

        total_assets = sum(a.balance for a in accounts if not a.is_debt)
        total_liabilities = sum(a.balance for a in accounts if a.is_debt)

        monthly_income = sum(t.amount for t in transactions.filter(kind='income')) / 3
        monthly_expenses = sum(t.amount for t in transactions.filter(kind='expense')) / 3

        return {
            'total_assets': float(total_assets),
            'total_liabilities': float(total_liabilities),
            'net_worth': float(total_assets - total_liabilities),
            'monthly_income': float(monthly_income),
            'monthly_expenses': float(monthly_expenses)
        }