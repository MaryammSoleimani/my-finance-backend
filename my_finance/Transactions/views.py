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

    @action(
        detail=False,
        methods=['post'],
        url_path='import-csv'
    )
    def import_csv(self, request):

        uploaded_file = request.FILES.get('file')

        if not uploaded_file:
            return Response(
                {
                    'success': False,
                    'message': 'Please select a CSV file.'
                },
                status=400
            )

        account_id = request.data.get('account')
        expense_category_id = request.data.get('expense_category')
        income_category_id = request.data.get('income_category')

        if not account_id:
            return Response(
                {
                    'success': False,
                    'message': 'Please select an account.'
                },
                status=400
            )

        # -----------------------------------------------------
        # Get user's account
        # -----------------------------------------------------

        try:
            account = Account.objects.get(
                id=account_id,
                owner=request.user
            )
        except Account.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'message': 'Selected account was not found.'
                },
                status=400
            )

        # -----------------------------------------------------
        # Get categories
        # -----------------------------------------------------

        expense_category = None
        income_category = None

        if expense_category_id:
            try:
                expense_category = Category.objects.get(
                    id=expense_category_id,
                    user=request.user
                )
            except Category.DoesNotExist:
                return Response(
                    {
                        'success': False,
                        'message': 'Selected expense category was not found.'
                    },
                    status=400
                )

        if income_category_id:
            try:
                income_category = Category.objects.get(
                    id=income_category_id,
                    user=request.user
                )
            except Category.DoesNotExist:
                return Response(
                    {
                        'success': False,
                        'message': 'Selected income category was not found.'
                    },
                    status=400
                )

        # -----------------------------------------------------
        # Read CSV
        # -----------------------------------------------------

        try:
            file_content = uploaded_file.read()

            try:
                decoded_file = file_content.decode('utf-8-sig')
            except UnicodeDecodeError:
                try:
                    decoded_file = file_content.decode('cp1256')
                except UnicodeDecodeError:
                    decoded_file = file_content.decode('utf-8')

            csv_file = io.StringIO(decoded_file)

            rows = list(csv.reader(csv_file))

        except Exception as e:
            return Response(
                {
                    'success': False,
                    'message': f'Could not read CSV file: {str(e)}'
                },
                status=400
            )

        if not rows:
            return Response(
                {
                    'success': False,
                    'message': 'The CSV file is empty.'
                },
                status=400
            )

        # -----------------------------------------------------
        # Find actual transaction header row
        #
        # Karafarin CSV contains several information rows
        # before the actual table header.
        # -----------------------------------------------------

        header_index = None

        for index, row in enumerate(rows):

            normalized_row = [
                str(cell).strip()
                for cell in row
            ]

            if (
                'تاریخ تراکنش' in normalized_row
                and 'شرح تراکنش' in normalized_row
                and 'مبلغ واریز' in normalized_row
                and 'مبلغ برداشت' in normalized_row
            ):
                header_index = index
                break

        if header_index is None:
            return Response(
                {
                    'success': False,
                    'message': (
                        'Invalid bank CSV format. '
                        'Transaction header could not be found.'
                    )
                },
                status=400
            )

        headers = [
            str(h).strip()
            for h in rows[header_index]
        ]

        # -----------------------------------------------------
        # Helper: find column index
        # -----------------------------------------------------

        def get_column_index(column_name):
            try:
                return headers.index(column_name)
            except ValueError:
                return None

        date_index = get_column_index('تاریخ تراکنش')
        desc_index = get_column_index('شرح تراکنش')
        deposit_index = get_column_index('مبلغ واریز')
        withdrawal_index = get_column_index('مبلغ برداشت')

        if (
            date_index is None
            or desc_index is None
            or deposit_index is None
            or withdrawal_index is None
        ):
            return Response(
                {
                    'success': False,
                    'message': 'Required transaction columns are missing.'
                },
                status=400
            )

        # -----------------------------------------------------
        # Helpers
        # -----------------------------------------------------

        def normalize_digits(value):
            """
            Convert Persian / Arabic digits to English digits.
            """

            if value is None:
                return ''

            value = str(value)

            translation_table = str.maketrans(
                '۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩',
                '01234567890123456789'
            )

            return value.translate(translation_table)

        def parse_amount(value):
            """
            Bank CSV amounts are Rial and may contain commas.

            Example:
                500,000,000
            """

            if value is None:
                return Decimal('0')

            value = normalize_digits(value)
            value = value.strip()

            if not value:
                return Decimal('0')

            value = value.replace(',', '')
            value = value.replace('٬', '')
            value = value.replace(' ', '')

            try:
                rial_amount = Decimal(value)

                # Bank CSV = Rial
                # Application = Toman
                toman_amount = rial_amount / Decimal('10')

                return toman_amount

            except InvalidOperation:
                return Decimal('0')

        def parse_jalali_date(value):
            """
            Convert:
                1405/06/14

            to:
                Gregorian date
            """

            if not value:
                return None

            value = normalize_digits(value).strip()

            try:
                year, month, day = [
                    int(x)
                    for x in value.split('/')
                ]

                jalali_date = jdatetime.date(
                    year,
                    month,
                    day
                )

                return jalali_date.togregorian()

            except Exception:
                return None

        # -----------------------------------------------------
        # Import transactions
        # -----------------------------------------------------

        imported_count = 0
        skipped_count = 0
        error_count = 0

        errors = []

        data_rows = rows[header_index + 1:]

        # -----------------------------------------------------
        # Use DB transaction so import remains consistent.
        # -----------------------------------------------------

        with db_transaction.atomic():

            for csv_row_number, row in enumerate(
                data_rows,
                start=header_index + 2
            ):

                try:

                    # Avoid malformed rows
                    if len(row) <= max(
                        date_index,
                        desc_index,
                        deposit_index,
                        withdrawal_index
                    ):
                        skipped_count += 1
                        continue

                    raw_date = row[date_index].strip()
                    raw_desc = row[desc_index].strip()

                    raw_deposit = row[deposit_index].strip()
                    raw_withdrawal = row[withdrawal_index].strip()

                    # Ignore completely empty rows
                    if not raw_date and not raw_desc:
                        continue

                    # -------------------------------------------------
                    # Determine transaction kind
                    # -------------------------------------------------

                    deposit_amount = parse_amount(raw_deposit)
                    withdrawal_amount = parse_amount(raw_withdrawal)

                    if deposit_amount > 0:

                        amount = deposit_amount
                        kind = 'income'

                    elif withdrawal_amount > 0:

                        amount = withdrawal_amount
                        kind = 'expense'

                    else:
                        skipped_count += 1
                        continue

                    # -------------------------------------------------
                    # Date
                    # -------------------------------------------------

                    transaction_date = parse_jalali_date(raw_date)

                    if transaction_date is None:
                        error_count += 1

                        errors.append(
                            {
                                'row': csv_row_number,
                                'message': (
                                    f'Invalid date: {raw_date}'
                                )
                            }
                        )

                        continue

                    # -------------------------------------------------
                    # Description
                    # -------------------------------------------------

                    description = raw_desc[:255]

                    if not description:
                        description = 'Imported bank transaction'

                    # -------------------------------------------------
                    # Category
                    # -------------------------------------------------

                    if kind == 'income':

                        category = income_category

                    else:

                        category = expense_category

                    # Category is required by Transaction model.
                    if category is None:

                        error_count += 1

                        errors.append(
                            {
                                'row': csv_row_number,
                                'message': (
                                    'No category selected for '
                                    f'{kind} transaction.'
                                )
                            }
                        )

                        continue

                    # -------------------------------------------------
                    # Duplicate detection
                    #
                    # We intentionally do NOT use bank transaction ID
                    # because the Karafarin CSV can contain multiple
                    # rows with the same transaction ID.
                    # -------------------------------------------------

                    duplicate_exists = Transaction.objects.filter(
                        user=request.user,
                        account=account,
                        date=transaction_date,
                        amount=amount,
                        kind=kind,
                        desc=description
                    ).exists()

                    if duplicate_exists:

                        skipped_count += 1
                        continue

                    # -------------------------------------------------
                    # Create transaction
                    #
                    # Existing post_save signals will automatically:
                    # - update account balance
                    # - update budget
                    # - create budget notifications
                    # -------------------------------------------------

                    Transaction.objects.create(
                        user=request.user,
                        date=transaction_date,
                        amount=amount,
                        desc=description,
                        kind=kind,
                        account=account,
                        category=category
                    )

                    imported_count += 1

                except Exception as e:

                    error_count += 1

                    errors.append(
                        {
                            'row': csv_row_number,
                            'message': str(e)
                        }
                    )

        # ---------------------------------------------------------
        # Response
        # ---------------------------------------------------------

        return Response(
            {
                'success': True,
                'message': 'CSV import completed.',
                'imported': imported_count,
                'skipped': skipped_count,
                'errors_count': error_count,
                'errors': errors[:20]
            }
        )

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