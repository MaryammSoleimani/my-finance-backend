from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.db.models import Sum
from django.db.models.functions import TruncDay
from django.db import transaction as db_transaction

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import csv
import io
import jdatetime

from categories.models import Category
from Accounts.models import Account
from .category_classifier import classify_transaction, normalize_text, match_category
from .models import Transaction
from .serializers import TransactionSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # =========================================================
    # IMPORT BANK CSV
    # =========================================================

    @action(detail=False, methods=['post'], url_path='import-csv')
    def import_csv(self, request):
        uploaded_file = request.FILES.get('file')
        account_id = request.data.get('account')

        if not uploaded_file:
            return Response({'success': False, 'message': 'Please select a CSV file.'}, status=400)
        if not account_id:
            return Response({'success': False, 'message': 'Please select an account.'}, status=400)

        try:
            account = Account.objects.get(id=account_id, owner=request.user)
        except Account.DoesNotExist:
            return Response({'success': False, 'message': 'Selected account was not found.'}, status=400)

        try:
            rows = self._read_csv_rows(uploaded_file.read())
        except ValueError as error:
            return Response({'success': False, 'message': str(error)}, status=400)

        header_index, column_indexes = self._find_transaction_header(rows)
        if header_index is None:
            return Response({
                'success': False,
                'message': 'Invalid bank CSV format. Transaction header could not be found.',
            }, status=400)

        # ============================================
        # INITIALIZE VARIABLES
        # ============================================
        active_categories = list(Category.objects.filter(
            user=request.user, is_active=True,
        ))

        imported_count = 0
        skipped_count = 0
        error_count = 0
        unmatched_count = 0
        errors = []
        unmatched_transactions = []  # این لیست برای ذخیره موقت

        # ============================================
        # PROCESS ROWS
        # ============================================
        with db_transaction.atomic():
            for row_number, row in enumerate(rows[header_index + 1:], start=header_index + 2):
                try:
                    parsed = self._parse_csv_row(row, column_indexes)
                    if parsed is None:
                        skipped_count += 1
                        continue
                    transaction_date, description, amount, kind = parsed
                except ValueError as error:
                    error_count += 1
                    errors.append({'row': row_number, 'message': str(error)})
                    continue

                # ============================================
                # Match or Auto-Create Category
                # ============================================
                category, was_created = match_category(
                    description, kind, active_categories, request.user
                )

                # If category was created, add it to active_categories for future rows
                if was_created:
                    active_categories.append(category)

                # Duplicate check
                if Transaction.objects.filter(
                        user=request.user,
                        account=account,
                        date=transaction_date,
                        amount=amount,
                        kind=kind,
                        desc=description,
                ).exists():
                    skipped_count += 1
                    continue

                # ============================================
                # Store unmatched transactions for later
                # ============================================
                if category is None:
                    unmatched_transactions.append({
                        'row': row_number,
                        'date': transaction_date.strftime('%Y-%m-%d'),
                        'description': description,
                        'amount': float(amount),
                        'kind': kind,
                        'account_id': account.id,
                        'account_name': account.name,

                    })
                    unmatched_count += 1
                    continue

                # Create transaction
                imported_transaction = Transaction(
                    user=request.user,
                    date=transaction_date,
                    amount=amount,
                    desc=description,
                    kind=kind,
                    account=account,
                    category=category,
                    affects_financial_totals=False,
                )
                imported_transaction.save()
                imported_count += 1

        # ============================================
        # Return response with unmatched transactions
        # ============================================
        return Response({
            'success': True,
            'message': 'CSV import completed.',
            'imported': imported_count,
            'skipped': skipped_count,
            'errors_count': error_count,
            'errors': errors[:20],
            'unmatched_count': unmatched_count,
            'unmatched': unmatched_transactions[:20],
            'has_unmatched': len(unmatched_transactions) > 0,
        })
    @staticmethod
    def _read_csv_rows(file_content):
        for encoding in ('utf-8-sig', 'cp1256'):
            try:
                return list(csv.reader(io.StringIO(file_content.decode(encoding))))
            except UnicodeDecodeError:
                continue
        raise ValueError('Could not read CSV file: unsupported encoding.')

    @action(detail=False, methods=['post'], url_path='save-unmatched')
    def save_unmatched(self, request):
        """Save transactions that were previously unmatched with user-selected categories."""

        transactions_data = request.data.get('transactions', [])
        if not transactions_data:
            return Response({'success': False, 'message': 'No transactions provided.'}, status=400)

        saved_count = 0
        errors = []

        for tx_data in transactions_data:
            try:
                category_id = tx_data.get('category_id')
                account_id = tx_data.get('account_id')

                if not category_id:
                    errors.append({
                        'row': tx_data.get('row', 'unknown'),
                        'error': 'No category selected'
                    })
                    continue

                # Get category and account (with user validation)
                category = Category.objects.get(id=category_id, user=request.user, is_active=True)
                account = Account.objects.get(id=account_id, owner=request.user)

                # Parse date from string
                from datetime import datetime
                transaction_date = datetime.strptime(tx_data.get('date'), '%Y-%m-%d').date()

                # Create the transaction
                transaction = Transaction(
                    user=request.user,
                    date=transaction_date,
                    amount=Decimal(str(tx_data.get('amount'))),
                    desc=tx_data.get('description', ''),
                    kind=tx_data.get('kind', 'expense'),
                    account=account,
                    category=category,
                    affects_financial_totals=False,
                )
                transaction.save()
                saved_count += 1

            except Category.DoesNotExist:
                errors.append({
                    'row': tx_data.get('row', 'unknown'),
                    'error': 'Category not found or not active'
                })
            except Account.DoesNotExist:
                errors.append({
                    'row': tx_data.get('row', 'unknown'),
                    'error': 'Account not found'
                })
            except Exception as e:
                errors.append({
                    'row': tx_data.get('row', 'unknown'),
                    'error': str(e)
                })

        return Response({
            'success': True,
            'saved': saved_count,
            'errors': errors,
            'total': len(transactions_data)
        })

    @staticmethod
    def _find_transaction_header(rows):
        required = ('تاریخ تراکنش', 'شرح تراکنش', 'مبلغ واریز', 'مبلغ برداشت')
        normalized_required = tuple(normalize_text(name) for name in required)
        for index, row in enumerate(rows):
            headers = [normalize_text(cell) for cell in row]
            if all(name in headers for name in normalized_required):
                return index, {name: headers.index(name) for name in normalized_required}
        return None, None

    @staticmethod
    def _parse_csv_row(row, column_indexes):
        if len(row) <= max(column_indexes.values()):
            return None
        raw_date = row[column_indexes[normalize_text('تاریخ تراکنش')]].strip()
        raw_description = row[column_indexes[normalize_text('شرح تراکنش')]].strip()
        if not raw_date and not raw_description:
            return None
        deposit = TransactionViewSet._parse_amount(row[column_indexes[normalize_text('مبلغ واریز')]])
        withdrawal = TransactionViewSet._parse_amount(row[column_indexes[normalize_text('مبلغ برداشت')]])
        if deposit > 0:
            amount, kind = deposit, 'income'
        elif withdrawal > 0:
            amount, kind = withdrawal, 'expense'
        else:
            return None
        try:
            year, month, day = (int(part) for part in normalize_text(raw_date).replace('-', '/').split('/'))
            transaction_date = jdatetime.date(year, month, day).togregorian()
        except (TypeError, ValueError, OverflowError):
            raise ValueError(f'Invalid date: {raw_date}')
        description = normalize_text(raw_description)[:255] or 'Imported bank transaction'
        return transaction_date, description, amount, kind

    @staticmethod
    def _parse_amount(value):
        normalized = normalize_text(value).replace(',', '').replace('٬', '').replace(' ', '')
        if not normalized:
            return Decimal('0')
        try:
            return Decimal(normalized)
        except InvalidOperation:
            raise ValueError(f'Invalid amount: {value}')

    # =========================================================
    # GROUPED
    # =========================================================

    @action(detail=False, methods=['get'])
    def grouped(self, request):

        period = request.query_params.get(
            'period',
            'current-month'
        )

        category = request.query_params.get(
            'category',
            ''
        )

        transactions = Transaction.objects.filter(
            user=request.user
        )

        if period == 'current-month':

            start_date = datetime.now().replace(
                day=1,
                hour=0,
                minute=0,
                second=0
            )

            transactions = transactions.filter(
                date__gte=start_date
            )

        elif period == 'last-month':

            today = datetime.now()

            first_day_current = today.replace(
                day=1,
                hour=0,
                minute=0,
                second=0
            )

            last_day_prev = (
                first_day_current - timedelta(days=1)
            )

            first_day_prev = last_day_prev.replace(
                day=1
            )

            transactions = transactions.filter(
                date__gte=first_day_prev,
                date__lte=last_day_prev
            )

        elif period == 'last-year':

            today = datetime.now()

            first_day_current_year = today.replace(
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0
            )

            last_day_prev_year = (
                first_day_current_year - timedelta(days=1)
            )

            first_day_prev_year = (
                last_day_prev_year.replace(month=1, day=1)
            )

            transactions = transactions.filter(
                date__gte=first_day_prev_year,
                date__lte=last_day_prev_year
            )

        elif period == 'all-time':
            pass

        elif period == 'per-day':
            pass

        if category and category != 'all':

            transactions = transactions.filter(
                category__name=category
            )

        groups = []

        categories = Category.objects.filter(
            user=request.user
        )

        for cat in categories:

            cat_transactions = transactions.filter(
                category=cat
            )

            total_expense = (
                cat_transactions
                .filter(kind='expense')
                .aggregate(total=Sum('amount'))['total']
                or 0
            )

            total_deposit = (
                cat_transactions
                .filter(kind='income')
                .aggregate(total=Sum('amount'))['total']
                or 0
            )

            if total_expense > 0 or total_deposit > 0:

                groups.append(
                    {
                        'category__name': cat.name,
                        'total_expense': float(
                            total_expense
                        ),
                        'total_deposit': float(
                            total_deposit
                        ),
                        'items': [
                            {
                                'id': t.id,
                                'desc': t.desc,
                                'amount': float(t.amount),
                                'amount_toman': float(t.amount),
                                'date': t.date.strftime(
                                    '%Y-%m-%d'
                                ),
                                'account': t.account.name,
                                'kind': t.kind,
                                'category': t.category.name
                            }
                            for t in cat_transactions[:10]
                        ]
                    }
                )

        grand_total_expense = sum(
            g['total_expense']
            for g in groups
        )

        grand_total_deposit = sum(
            g['total_deposit']
            for g in groups
        )

        return Response(
            {
                'groups': groups,
                'grand_total_expense': grand_total_expense,
                'grand_total_deposit': grand_total_deposit
            }
        )

    # =========================================================
    # CATEGORIES
    # =========================================================

    @action(detail=False, methods=['get'])
    def categories(self, request):

        categories = Category.objects.filter(
            user=request.user
        )

        data = [
            {
                'id': category.id,
                'name': category.name,
                'color': category.color
            }
            for category in categories
        ]

        return Response(data)

    # =========================================================
    # CATEGORY EXPENSES
    # =========================================================

    @action(
        detail=False,
        methods=['get'],
        url_path='category-expenses'
    )
    def category_expenses(self, request):

        period = request.query_params.get(
            'period',
            'current-month'
        )

        category = request.query_params.get(
            'category',
            ''
        )

        transactions = Transaction.objects.filter(
            user=request.user,
            kind='expense'
        )

        if period == 'current-month':

            start_date = datetime.now().replace(
                day=1,
                hour=0,
                minute=0,
                second=0
            )

            transactions = transactions.filter(
                date__gte=start_date
            )

        elif period == 'last-month':

            today = datetime.now()

            first_day_current = today.replace(
                day=1,
                hour=0,
                minute=0,
                second=0
            )

            last_day_prev = (
                first_day_current - timedelta(days=1)
            )

            first_day_prev = last_day_prev.replace(
                day=1
            )

            transactions = transactions.filter(
                date__gte=first_day_prev,
                date__lte=last_day_prev
            )

        elif period == 'last-year':

            today = datetime.now()

            first_day_current_year = today.replace(
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0
            )

            last_day_prev_year = (
                first_day_current_year - timedelta(days=1)
            )

            first_day_prev_year = (
                last_day_prev_year.replace(
                    month=1,
                    day=1
                )
            )

            transactions = transactions.filter(
                date__gte=first_day_prev_year,
                date__lte=last_day_prev_year
            )

        if category and category != 'all':

            transactions = transactions.filter(
                category__name=category
            )

        categories = Category.objects.filter(
            user=request.user
        )

        series = []
        labels = []
        colors = []

        for cat in categories:

            total = (
                transactions
                .filter(category=cat)
                .aggregate(total=Sum('amount'))['total']
                or 0
            )

            if total > 0:

                series.append(float(total))
                labels.append(cat.name)
                colors.append(cat.color)

        return Response(
            {
                'series': series,
                'labels': labels,
                'colors': colors
            }
        )

    # =========================================================
    # DAILY EXPENSES
    # =========================================================

    @action(
        detail=False,
        methods=['get'],
        url_path='daily-expenses'
    )
    def daily_expenses(self, request):

        period = request.query_params.get(
            'period',
            'current-month'
        )

        category = request.query_params.get(
            'category',
            ''
        )

        transactions = Transaction.objects.filter(
            user=request.user,
            kind='expense'
        )

        if period == 'current-month':

            start_date = datetime.now().replace(
                day=1,
                hour=0,
                minute=0,
                second=0
            )

            transactions = transactions.filter(
                date__gte=start_date
            )

        elif period == 'last-month':

            today = datetime.now()

            first_day_current = today.replace(
                day=1,
                hour=0,
                minute=0,
                second=0
            )

            last_day_prev = (
                first_day_current - timedelta(days=1)
            )

            first_day_prev = last_day_prev.replace(
                day=1
            )

            transactions = transactions.filter(
                date__gte=first_day_prev,
                date__lte=last_day_prev
            )

        elif period == 'last-year':

            today = datetime.now()

            first_day_current_year = today.replace(
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0
            )

            last_day_prev_year = (
                first_day_current_year - timedelta(days=1)
            )

            first_day_prev_year = (
                last_day_prev_year.replace(
                    month=1,
                    day=1
                )
            )

            transactions = transactions.filter(
                date__gte=first_day_prev_year,
                date__lte=last_day_prev_year
            )

        if category and category != 'all':

            transactions = transactions.filter(
                category__name=category
            )

        daily_data = (
            transactions
            .annotate(day=TruncDay('date'))
            .values('day')
            .annotate(total=Sum('amount'))
            .order_by('day')
        )

        data = []
        categories = []

        for item in daily_data:

            data.append(float(item['total']))

            categories.append(
                item['day'].strftime('%b %d')
            )

        return Response(
            {
                'data': data,
                'categories': categories
            }
        )

    # =========================================================
    # DAILY DEPOSITS
    # =========================================================

    @action(
        detail=False,
        methods=['get'],
        url_path='daily-deposits'
    )
    def daily_deposits(self, request):

        period = request.query_params.get(
            'period',
            'current-month'
        )

        category = request.query_params.get(
            'category',
            ''
        )

        transactions = Transaction.objects.filter(
            user=request.user,
            kind='income'
        )

        if period == 'current-month':

            start_date = datetime.now().replace(
                day=1,
                hour=0,
                minute=0,
                second=0
            )

            transactions = transactions.filter(
                date__gte=start_date
            )

        elif period == 'last-month':

            today = datetime.now()

            first_day_current = today.replace(
                day=1,
                hour=0,
                minute=0,
                second=0
            )

            last_day_prev = (
                first_day_current - timedelta(days=1)
            )

            first_day_prev = last_day_prev.replace(
                day=1
            )

            transactions = transactions.filter(
                date__gte=first_day_prev,
                date__lte=last_day_prev
            )

        elif period == 'last-year':

            today = datetime.now()

            first_day_current_year = today.replace(
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0
            )

            last_day_prev_year = (
                first_day_current_year - timedelta(days=1)
            )

            first_day_prev_year = (
                last_day_prev_year.replace(
                    month=1,
                    day=1
                )
            )

            transactions = transactions.filter(
                date__gte=first_day_prev_year,
                date__lte=last_day_prev_year
            )

        if category and category != 'all':

            transactions = transactions.filter(
                category__name=category
            )

        daily_data = (
            transactions
            .annotate(day=TruncDay('date'))
            .values('day')
            .annotate(total=Sum('amount'))
            .order_by('day')
        )

        data = []
        categories = []

        for item in daily_data:

            data.append(float(item['total']))

            categories.append(
                item['day'].strftime('%b %d')
            )

        return Response(
            {
                'data': data,
                'categories': categories
            }
        )

    # =========================================================
    # LATEST
    # =========================================================

    @action(detail=False, methods=['get'])
    def latest(self, request):

        transactions = (
            Transaction.objects
            .filter(user=request.user)
            .order_by('-date', '-id')[:10]
        )

        serializer = self.get_serializer(
            transactions,
            many=True
        )

        return Response(serializer.data)

    # =========================================================
    # YEARS
    # =========================================================

    @action(detail=False, methods=['get'])
    def years(self, request):

        years = (
            Transaction.objects
            .filter(user=request.user)
            .dates(
                'date',
                'year',
                order='DESC'
            )
        )

        return Response(
            [str(y.year) for y in years]
        )

    # =========================================================
    # CATEGORY DEPOSITS
    # =========================================================

    @action(
        detail=False,
        methods=['get'],
        url_path='category-deposits'
    )
    def category_deposits(self, request):

        period = request.query_params.get(
            'period',
            'current-month'
        )

        category = request.query_params.get(
            'category',
            ''
        )

        transactions = Transaction.objects.filter(
            user=request.user,
            kind='income'
        )

        if period == 'current-month':

            start_date = datetime.now().replace(
                day=1,
                hour=0,
                minute=0,
                second=0
            )

            transactions = transactions.filter(
                date__gte=start_date
            )

        elif period == 'last-month':

            today = datetime.now()

            first_day_current = today.replace(
                day=1,
                hour=0,
                minute=0,
                second=0
            )

            last_day_prev = (
                first_day_current - timedelta(days=1)
            )

            first_day_prev = last_day_prev.replace(
                day=1
            )

            transactions = transactions.filter(
                date__gte=first_day_prev,
                date__lte=last_day_prev
            )

        elif period == 'last-year':

            today = datetime.now()

            first_day_current_year = today.replace(
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0
            )

            last_day_prev_year = (
                first_day_current_year - timedelta(days=1)
            )

            first_day_prev_year = (
                last_day_prev_year.replace(
                    month=1,
                    day=1
                )
            )

            transactions = transactions.filter(
                date__gte=first_day_prev_year,
                date__lte=last_day_prev_year
            )

        if category and category != 'all':

            transactions = transactions.filter(
                category__name=category
            )

        categories = Category.objects.filter(
            user=request.user
        )

        series = []
        labels = []
        colors = []

        for cat in categories:

            total = (
                transactions
                .filter(category=cat)
                .aggregate(total=Sum('amount'))['total']
                or 0
            )

            if total > 0:

                series.append(float(total))
                labels.append(cat.name)
                colors.append(cat.color)

        return Response(
            {
                'series': series,
                'labels': labels,
                'colors': colors
            }
        )
