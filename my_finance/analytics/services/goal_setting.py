from decimal import Decimal
from Accounts.models import Account


class SmartGoalCalculator:

    def __init__(self, user, goal_amount, months):
        self.user = user
        self.goal_amount = Decimal(str(goal_amount))
        self.months = int(months)

        self.accounts = Account.objects.filter(owner=user)

    def calculate(self):

        # =========================================================
        # 1. Validate input
        # =========================================================

        if self.goal_amount <= 0:
            raise ValueError("Goal amount must be greater than zero.")

        if self.months <= 0:
            raise ValueError("Timeframe must be greater than zero.")

        # =========================================================
        # 2. Required monthly saving
        # =========================================================

        required_monthly_savings = (
            self.goal_amount / Decimal(self.months)
        )

        # =========================================================
        # 3. Total assets
        # =========================================================

        total_assets = sum(
            (
                account.balance
                for account in self.accounts
                if not account.is_debt
            ),
            Decimal("0")
        )

        # =========================================================
        # 4. Required saving compared with total assets
        # =========================================================

        if total_assets > 0:
            asset_ratio = (
                required_monthly_savings / total_assets
            ) * Decimal("100")
        else:
            asset_ratio = Decimal("100")

        # =========================================================
        # 5. Feasibility
        # =========================================================

        if total_assets <= 0:
            risk_level = "high"
            risk_status = "danger"

        elif asset_ratio <= Decimal("5"):
            risk_level = "low"
            risk_status = "good"

        elif asset_ratio <= Decimal("15"):
            risk_level = "reasonable"
            risk_status = "ok"

        elif asset_ratio <= Decimal("30"):
            risk_level = "challenging"
            risk_status = "warning"

        else:
            risk_level = "high"
            risk_status = "danger"

        # =========================================================
        # 6. User-friendly recommendation
        # =========================================================

        monthly_text = f"${required_monthly_savings:,.2f}"
        goal_text = f"${self.goal_amount:,.2f}"

        if risk_level == "low":

            recommendation = (
                f"You need to save {monthly_text} per month "
                f"to reach your {goal_text} goal in {self.months} months. "
                f"This goal looks achievable and should not put significant "
                f"pressure on your current financial position."
            )

        elif risk_level == "reasonable":

            recommendation = (
                f"You need to save {monthly_text} per month "
                f"to reach your {goal_text} goal in {self.months} months. "
                f"This goal looks achievable, but you will need to maintain "
                f"consistent monthly savings."
            )

        elif risk_level == "challenging":

            recommendation = (
                f"You need to save {monthly_text} per month "
                f"to reach your {goal_text} goal in {self.months} months. "
                f"This goal may be challenging compared with your current "
                f"financial position. Consider extending the timeframe."
            )

        else:

            recommendation = (
                f"You need to save {monthly_text} per month "
                f"to reach your {goal_text} goal in {self.months} months. "
                f"This target may be difficult compared with your current "
                f"financial position. Consider reducing the goal amount "
                f"or extending the timeframe."
            )

        # =========================================================
        # 7. Return result
        # =========================================================

        return {
            "goal_amount": float(self.goal_amount),
            "months": self.months,
            "required_monthly_savings": round(
                float(required_monthly_savings), 2
            ),
            "total_assets": round(
                float(total_assets), 2
            ),
            "asset_ratio": round(
                float(asset_ratio), 2
            ),
            "risk_level": risk_level,
            "risk_status": risk_status,
            "recommendation": recommendation,
        }