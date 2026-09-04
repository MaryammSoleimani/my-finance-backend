from decimal import Decimal
from datetime import date, timedelta

from django.db.models import Sum
from django.utils import timezone

from Accounts.models import Account
from Transactions.models import Transaction


class HealthScoreCalculator:

    # =========================================================
    # Configuration
    # =========================================================

    HISTORY_MONTHS = 3

    MAX_DEBT_SCORE = 25
    MAX_SAVINGS_SCORE = 25
    MAX_EMERGENCY_SCORE = 20
    MAX_GROWTH_SCORE = 15
    MAX_STABILITY_SCORE = 15

    # =========================================================
    # Initialization
    # =========================================================

    def __init__(self, user):
        self.user = user

        self.accounts = Account.objects.filter(
            owner=user
        )

        self.transactions = Transaction.objects.filter(
            user=user
        )

        self.today = timezone.localdate()

    # =========================================================
    # Main Calculator
    # =========================================================

    def calculate(self):

        # -----------------------------------------------------
        # Check whether enough data exists
        # -----------------------------------------------------

        total_transactions = self.transactions.count()

        if total_transactions == 0:
            return self._insufficient_data_response(
                "Add some income and expense transactions to calculate your financial health."
            )

        first_transaction = (
            self.transactions
            .order_by("date")
            .values_list("date", flat=True)
            .first()
        )

        if not first_transaction:
            return self._insufficient_data_response(
                "Not enough transaction data."
            )

        days_of_data = (self.today - first_transaction).days

        # We prefer at least 30 days of data.
        if days_of_data < 30:
            return self._insufficient_data_response(
                "At least 30 days of transaction history are needed to calculate a reliable score."
            )

        # -----------------------------------------------------
        # Calculate each component
        # -----------------------------------------------------

        debt = self._calculate_debt_health()
        savings = self._calculate_savings_rate()
        emergency = self._calculate_emergency_fund()
        growth = self._calculate_net_worth_growth()
        stability = self._calculate_spending_stability()

        # -----------------------------------------------------
        # Total score
        # -----------------------------------------------------

        score = (
            debt["score"]
            + savings["score"]
            + emergency["score"]
            + growth["score"]
            + stability["score"]
        )

        score = max(0, min(round(score), 100))

        # -----------------------------------------------------
        # Grade
        # -----------------------------------------------------

        grade, message = self._get_grade(score)

        # -----------------------------------------------------
        # Recommendations
        # -----------------------------------------------------

        recommendations = self._generate_recommendations(
            debt,
            savings,
            emergency,
            growth,
            stability
        )

        # -----------------------------------------------------
        # Final response
        # -----------------------------------------------------

        return {
            "score": score,
            "grade": grade,
            "message": message,
            "color": self.get_color(score),

            "details": {
                "debt": debt,
                "savings": savings,
                "emergency_fund": emergency,
                "growth": growth,
                "spending_stability": stability,
            },

            "recommendations": recommendations,

            "data_period": {
                "months": self.HISTORY_MONTHS,
                "description": "Based on your recent financial activity"
            }
        }

    # =========================================================
    # 1. Debt Health
    # =========================================================

    def _calculate_debt_health(self):

        total_assets = (
            self.accounts
            .filter(is_debt=False)
            .aggregate(total=Sum("balance"))["total"]
            or Decimal("0")
        )

        total_liabilities = (
            self.accounts
            .filter(is_debt=True)
            .aggregate(total=Sum("balance"))["total"]
            or Decimal("0")
        )

        total_assets = Decimal(str(total_assets))
        total_liabilities = Decimal(str(total_liabilities))

        # No debt
        if total_liabilities <= 0:

            return {
                "score": self.MAX_DEBT_SCORE,
                "max_score": self.MAX_DEBT_SCORE,
                "status": "good",
                "label": "No Debt",
                "debt_ratio": 0,
            }

        # Cannot calculate ratio without assets
        if total_assets <= 0:

            return {
                "score": 0,
                "max_score": self.MAX_DEBT_SCORE,
                "status": "danger",
                "label": "High Financial Risk",
                "debt_ratio": None,
            }

        debt_ratio = total_liabilities / total_assets

        # -----------------------------------------
        # Scoring
        # -----------------------------------------

        if debt_ratio <= Decimal("0.10"):
            score = 25
            status = "good"
            label = "Very Low Debt"

        elif debt_ratio <= Decimal("0.20"):
            score = 22
            status = "good"
            label = "Low Debt"

        elif debt_ratio <= Decimal("0.35"):
            score = 18
            status = "ok"
            label = "Moderate Debt"

        elif debt_ratio <= Decimal("0.50"):
            score = 12
            status = "warning"
            label = "High Debt"

        elif debt_ratio <= Decimal("0.70"):
            score = 5
            status = "warning"
            label = "Very High Debt"

        else:
            score = 0
            status = "danger"
            label = "Critical Debt Level"

        return {
            "score": score,
            "max_score": self.MAX_DEBT_SCORE,
            "status": status,
            "label": label,
            "debt_ratio": round(float(debt_ratio * 100), 2),
            "total_assets": float(total_assets),
            "total_liabilities": float(total_liabilities),
        }

    # =========================================================
    # 2. Savings Rate
    # =========================================================

    def _calculate_savings_rate(self):

        monthly_data = self._get_monthly_income_expenses()

        if not monthly_data:
            return {
                "score": 0,
                "max_score": self.MAX_SAVINGS_SCORE,
                "status": "danger",
                "label": "No Income Data",
                "savings_rate": None,
            }

        total_income = sum(
            item["income"] for item in monthly_data
        )

        total_expenses = sum(
            item["expenses"] for item in monthly_data
        )

        if total_income <= 0:

            return {
                "score": 0,
                "max_score": self.MAX_SAVINGS_SCORE,
                "status": "danger",
                "label": "No Income Data",
                "savings_rate": None,
            }

        total_savings = total_income - total_expenses

        savings_rate = total_savings / total_income

        # -----------------------------------------
        # Scoring
        # -----------------------------------------

        if savings_rate >= Decimal("0.30"):
            score = 25
            status = "good"
            label = "Excellent Savings"

        elif savings_rate >= Decimal("0.20"):
            score = 20
            status = "good"
            label = "Strong Savings"

        elif savings_rate >= Decimal("0.10"):
            score = 12
            status = "ok"
            label = "Moderate Savings"

        elif savings_rate > Decimal("0"):
            score = 6
            status = "warning"
            label = "Low Savings"

        else:
            score = 0
            status = "danger"
            label = "No Savings"

        return {
            "score": score,
            "max_score": self.MAX_SAVINGS_SCORE,
            "status": status,
            "label": label,
            "savings_rate": round(float(savings_rate * 100), 2),
            "average_monthly_income": round(
                float(total_income / len(monthly_data)), 2
            ),
            "average_monthly_expenses": round(
                float(total_expenses / len(monthly_data)), 2
            ),
            "average_monthly_savings": round(
                float(total_savings / len(monthly_data)), 2
            ),
        }

    # =========================================================
    # 3. Emergency Fund
    # =========================================================

    def _calculate_emergency_fund(self):

        liquid_assets = (
            self.accounts
            .filter(
                is_debt=False,
                type__in=["account"]
            )
            .aggregate(total=Sum("balance"))["total"]
            or Decimal("0")
        )

        liquid_assets = Decimal(str(liquid_assets))

        monthly_data = self._get_monthly_income_expenses()

        if not monthly_data:

            return {
                "score": 0,
                "max_score": self.MAX_EMERGENCY_SCORE,
                "status": "danger",
                "label": "No Expense Data",
                "months_covered": None,
            }

        total_expenses = sum(
            item["expenses"] for item in monthly_data
        )

        average_monthly_expenses = (
            total_expenses / len(monthly_data)
        )

        if average_monthly_expenses <= 0:

            return {
                "score": self.MAX_EMERGENCY_SCORE,
                "max_score": self.MAX_EMERGENCY_SCORE,
                "status": "good",
                "label": "No Regular Expenses",
                "months_covered": None,
            }

        months_covered = (
            liquid_assets / average_monthly_expenses
        )

        # -----------------------------------------
        # Scoring
        # -----------------------------------------

        if months_covered >= Decimal("6"):
            score = 20
            status = "good"
            label = "6+ Months Covered"

        elif months_covered >= Decimal("3"):
            score = 15
            status = "good"
            label = "3-6 Months Covered"

        elif months_covered >= Decimal("1"):
            score = 10
            status = "warning"
            label = "1-3 Months Covered"

        elif months_covered > Decimal("0"):
            score = 3
            status = "danger"
            label = "Less Than 1 Month"

        else:
            score = 0
            status = "danger"
            label = "No Emergency Fund"

        return {
            "score": score,
            "max_score": self.MAX_EMERGENCY_SCORE,
            "status": status,
            "label": label,
            "months_covered": round(
                float(months_covered), 2
            ),
            "liquid_assets": float(liquid_assets),
            "average_monthly_expenses": round(
                float(average_monthly_expenses), 2
            ),
        }

    # =========================================================
    # 4. Net Worth Growth
    # =========================================================

    def _calculate_net_worth_growth(self):

        current_net_worth = self._get_current_net_worth()

        historical_net_worth = self._estimate_historical_net_worth(
            months_ago=3
        )

        if historical_net_worth is None:

            return {
                "score": 8,
                "max_score": self.MAX_GROWTH_SCORE,
                "status": "ok",
                "label": "Building History",
                "growth_rate": None,
            }

        if historical_net_worth <= 0:

            if current_net_worth > 0:
                growth_rate = Decimal("1")
            else:
                growth_rate = Decimal("0")

        else:
            growth_rate = (
                current_net_worth - historical_net_worth
            ) / historical_net_worth

        # -----------------------------------------
        # Scoring
        # -----------------------------------------

        if growth_rate >= Decimal("0.10"):
            score = 15
            status = "good"
            label = "Strong Growth"

        elif growth_rate >= Decimal("0.05"):
            score = 12
            status = "good"
            label = "Positive Growth"

        elif growth_rate >= Decimal("0"):
            score = 8
            status = "ok"
            label = "Stable"

        elif growth_rate >= Decimal("-0.10"):
            score = 3
            status = "warning"
            label = "Declining"

        else:
            score = 0
            status = "danger"
            label = "Significant Decline"

        return {
            "score": score,
            "max_score": self.MAX_GROWTH_SCORE,
            "status": status,
            "label": label,
            "growth_rate": round(
                float(growth_rate * 100), 2
            ),
            "current_net_worth": float(current_net_worth),
            "previous_net_worth": float(historical_net_worth),
        }

    # =========================================================
    # 5. Spending Stability
    # =========================================================

    def _calculate_spending_stability(self):

        monthly_data = self._get_monthly_income_expenses()

        if len(monthly_data) < 2:

            return {
                "score": 8,
                "max_score": self.MAX_STABILITY_SCORE,
                "status": "ok",
                "label": "Building History",
                "expense_variation": None,
            }

        expenses = [
            item["expenses"]
            for item in monthly_data
        ]

        average_expenses = (
            sum(expenses) / len(expenses)
        )

        if average_expenses <= 0:

            return {
                "score": self.MAX_STABILITY_SCORE,
                "max_score": self.MAX_STABILITY_SCORE,
                "status": "good",
                "label": "No Significant Expenses",
                "expense_variation": 0,
            }

        differences = [
            abs(expense - average_expenses)
            for expense in expenses
        ]

        average_difference = (
            sum(differences) / len(differences)
        )

        variation = (
            average_difference / average_expenses
        )

        # -----------------------------------------
        # Scoring
        # -----------------------------------------

        if variation <= Decimal("0.10"):
            score = 15
            status = "good"
            label = "Very Stable Spending"

        elif variation <= Decimal("0.20"):
            score = 12
            status = "good"
            label = "Stable Spending"

        elif variation <= Decimal("0.35"):
            score = 8
            status = "ok"
            label = "Moderate Variation"

        elif variation <= Decimal("0.50"):
            score = 4
            status = "warning"
            label = "Unstable Spending"

        else:
            score = 0
            status = "danger"
            label = "Highly Unstable Spending"

        return {
            "score": score,
            "max_score": self.MAX_STABILITY_SCORE,
            "status": status,
            "label": label,
            "expense_variation": round(
                float(variation * 100), 2
            ),
            "average_monthly_expenses": round(
                float(average_expenses), 2
            ),
        }

    # =========================================================
    # Monthly Financial Data
    # =========================================================

    def _get_monthly_income_expenses(self):

        result = []

        # Start from first day of current month
        current_month = self.today.replace(day=1)

        for i in range(self.HISTORY_MONTHS):

            month_start = self._subtract_months(
                current_month,
                i
            )

            next_month = self._add_month(
                month_start
            )

            transactions = self.transactions.filter(
                date__gte=month_start,
                date__lt=next_month
            )

            income = (
                transactions
                .filter(kind="income")
                .aggregate(total=Sum("amount"))["total"]
                or Decimal("0")
            )

            expenses = (
                transactions
                .filter(kind="expense")
                .aggregate(total=Sum("amount"))["total"]
                or Decimal("0")
            )

            result.append({
                "month": month_start.strftime("%Y-%m"),
                "income": Decimal(str(income)),
                "expenses": Decimal(str(expenses)),
            })

        # Oldest → newest
        result.reverse()

        return result

    # =========================================================
    # Current Net Worth
    # =========================================================

    def _get_current_net_worth(self):

        assets = (
            self.accounts
            .filter(is_debt=False)
            .aggregate(total=Sum("balance"))["total"]
            or Decimal("0")
        )

        liabilities = (
            self.accounts
            .filter(is_debt=True)
            .aggregate(total=Sum("balance"))["total"]
            or Decimal("0")
        )

        return (
            Decimal(str(assets))
            - Decimal(str(liabilities))
        )

    # =========================================================
    # Historical Net Worth
    # =========================================================

    def _estimate_historical_net_worth(self, months_ago=3):

        target_date = self._subtract_months(
            self.today,
            months_ago
        )

        historical_net_worth = Decimal("0")

        for account in self.accounts:

            current_balance = Decimal(
                str(account.balance)
            )

            # Transactions after target date
            future_transactions = (
                Transaction.objects
                .filter(
                    user=self.user,
                    account=account,
                    date__gt=target_date
                )
            )

            future_income = (
                future_transactions
                .filter(kind="income")
                .aggregate(total=Sum("amount"))["total"]
                or Decimal("0")
            )

            future_expenses = (
                future_transactions
                .filter(kind="expense")
                .aggregate(total=Sum("amount"))["total"]
                or Decimal("0")
            )

            future_income = Decimal(
                str(future_income)
            )

            future_expenses = Decimal(
                str(future_expenses)
            )

            # Reverse transactions to estimate old balance
            historical_balance = (
                current_balance
                - future_income
                + future_expenses
            )

            if account.is_debt:
                historical_net_worth -= historical_balance
            else:
                historical_net_worth += historical_balance

        return historical_net_worth

    # =========================================================
    # Recommendations
    # =========================================================

    def _generate_recommendations(
        self,
        debt,
        savings,
        emergency,
        growth,
        stability
    ):

        recommendations = []

        # Debt
        if debt["status"] in ["warning", "danger"]:

            recommendations.append(
                "Try to reduce your debt relative to your total assets."
            )

        # Savings
        if savings["status"] in ["warning", "danger"]:

            recommendations.append(
                "Try to increase your savings rate by reducing unnecessary expenses."
            )

        elif savings.get("savings_rate") is not None:

            if savings["savings_rate"] < 20:

                recommendations.append(
                    "Aim for a savings rate of at least 20% of your income."
                )

        # Emergency fund
        months = emergency.get("months_covered")

        if months is not None:

            if months < 3:

                recommendations.append(
                    "Build your emergency fund toward at least 3 months of expenses."
                )

            elif months < 6:

                recommendations.append(
                    "Consider increasing your emergency fund toward 6 months of expenses."
                )

        # Growth
        if growth["status"] == "danger":

            recommendations.append(
                "Your net worth is declining. Review your spending and debt levels."
            )

        elif growth["status"] == "warning":

            recommendations.append(
                "Your net worth has declined recently. Try to increase monthly savings."
            )

        # Spending
        if stability["status"] in ["warning", "danger"]:

            recommendations.append(
                "Your spending varies significantly between months. Creating a monthly budget may help."
            )

        # Fallback
        if not recommendations:

            recommendations.append(
                "Your finances look healthy. Keep maintaining your current habits."
            )

        return recommendations

    # =========================================================
    # Grade
    # =========================================================

    def _get_grade(self, score):

        if score >= 90:
            return "A", "Excellent financial health"

        elif score >= 75:
            return "B", "Good financial health"

        elif score >= 60:
            return "C", "Fair financial health"

        elif score >= 40:
            return "D", "Needs improvement"

        return "F", "Financial health needs attention"

    # =========================================================
    # Color
    # =========================================================

    def get_color(self, score):

        if score >= 90:
            return "#10b981"

        elif score >= 75:
            return "#3b82f6"

        elif score >= 60:
            return "#f59e0b"

        elif score >= 40:
            return "#f97316"

        return "#ef4444"

    # =========================================================
    # Insufficient Data
    # =========================================================

    def _insufficient_data_response(self, message):

        return {
            "score": None,
            "grade": None,
            "message": message,
            "status": "insufficient_data",
            "color": "#71717a",
            "details": {},
            "recommendations": [
                "Add more income and expense transactions to get a reliable Financial Health Score."
            ]
        }

    # =========================================================
    # Date Helpers
    # =========================================================

    def _subtract_months(self, value, months):

        year = value.year
        month = value.month - months

        while month <= 0:
            month += 12
            year -= 1

        return value.replace(
            year=year,
            month=month,
            day=1
        )

    def _add_month(self, value):

        if value.month == 12:

            return value.replace(
                year=value.year + 1,
                month=1,
                day=1
            )

        return value.replace(
            month=value.month + 1,
            day=1
        )