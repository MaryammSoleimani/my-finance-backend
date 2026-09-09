from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from Accounts.models import Account
from Transactions.models import Transaction
from Transactions.views import TransactionViewSet
from budget.models import Budget
from categories.models import Category


class CsvImportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('importer')
        self.other_user = User.objects.create_user('other')
        self.account = Account.objects.create(
            owner=self.user, name='Bank', balance=Decimal('1000'),
        )
        self.transport = Category.objects.create(user=self.user, name='حمل و نقل')
        self.shopping = Category.objects.create(user=self.user, name='خرید')
        self.income = Category.objects.create(user=self.user, name='درآمد')
        self.inactive = Category.objects.create(user=self.user, name='درمان', is_active=False)
        self.foreign = Category.objects.create(user=self.other_user, name='درمان')
        self.budget = Budget.objects.create(
            user=self.user, name='Transport', category=self.transport,
            amount=Decimal('5000'), spent_amount=Decimal('100'),
        )
        self.factory = APIRequestFactory()

    def _import(self, content):
        upload = BytesIO(content)
        upload.name = 'statement.csv'
        request = self.factory.post('/transactions/import-csv/', {
            'file': upload, 'account': str(self.account.id),
        }, format='multipart')
        force_authenticate(request, user=self.user)
        return TransactionViewSet.as_view({'post': 'import_csv'})(request)

    def test_import_detects_metadata_normalizes_values_and_preserves_balances(self):
        csv_content = (
            'اطلاعات حساب\n'
            'نسخه,1\n'
            'تاريخ تراكنش,شرح تراكنش,مبلغ واريز,مبلغ برداشت\n'
            '۱۴۰۵/۰۶/۱۴,خريد کالا و خدمات اسنپ,,۱۲٬۵۰۰\n'
            '۱۴۰۵/۰۶/۱۵,واریز حقوق,۲۰٬۰۰۰,\n'
        ).encode('utf-8-sig')

        response = self._import(csv_content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['imported'], 2)
        self.assertEqual(Transaction.objects.count(), 2)
        expense = Transaction.objects.get(kind='expense')
        income = Transaction.objects.get(kind='income')
        self.assertEqual(expense.amount, Decimal('1250'))
        self.assertEqual(expense.date.isoformat(), '2026-09-05')
        self.assertEqual(expense.category, self.transport)
        self.assertEqual(income.category, self.income)
        self.account.refresh_from_db()
        self.budget.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1000'))
        self.assertEqual(self.budget.spent_amount, Decimal('100'))
        expense.delete()
        self.account.refresh_from_db()
        self.budget.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('1000'))
        self.assertEqual(self.budget.spent_amount, Decimal('100'))

    def test_import_skips_duplicates_and_reports_unmatched_without_creating_categories(self):
        content = (
            'تاريخ تراكنش,شرح تراكنش,مبلغ واريز,مبلغ برداشت\n'
            '1405/06/14,merchant unknown,,1000\n'
            '1405/06/15,خريد ديجي كالا,,1000\n'
        ).encode('cp1256')
        first = self._import(content)
        second = self._import(content)

        self.assertEqual(first.data['imported'], 1)
        self.assertEqual(first.data['unmatched_count'], 1)
        self.assertEqual(second.data['imported'], 0)
        self.assertEqual(second.data['skipped'], 1)
        self.assertEqual(Category.objects.filter(user=self.user).count(), 4)
