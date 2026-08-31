from datetime import date, timedelta
from decimal import Decimal
from .models import Asset, CashFlow, Event


class SimulationEngine:
    def __init__(self, user, start_date=None, end_date=None):
        self.user = user
        self.start_date = start_date or date.today()
        self.end_date = end_date or (self.start_date + timedelta(days=365 * 5))

    def calculate_summary(self):
        assets = Asset.objects.filter(user=self.user)
        cash_flows = CashFlow.objects.filter(user=self.user)

        total_assets = sum(a.amount for a in assets)
        total_liabilities = sum(cf.amount for cf in cash_flows if cf.flow_type == 'out')

        net_worth = total_assets - total_liabilities
        plan_outcome = 'success' if net_worth > 0 else 'failed'

        return {
            'final_total_assets': float(total_assets),
            'final_liquid_assets': float(total_assets),
            'plan_outcome': plan_outcome,
            'net_worth': float(net_worth)
        }

    def calculate_timeline(self):
        assets = Asset.objects.filter(user=self.user)
        cash_flows = CashFlow.objects.filter(user=self.user)
        events = Event.objects.filter(user=self.user)

        months = []
        current_date = self.start_date

        while current_date <= self.end_date:
            months.append(current_date.strftime('%b %Y'))
            current_date = self._add_months(current_date, 1)

        liquid_data = []
        illiquid_data = []

        for month_index, month in enumerate(months):
            monthly_in = sum(cf.amount for cf in cash_flows if cf.flow_type == 'in')
            monthly_out = sum(cf.amount for cf in cash_flows if cf.flow_type == 'out')

            # اعمال رویدادها
            for event in events:
                if event.month == (month_index + 1):
                    if event.event_type == 'income_change':
                        monthly_in += event.amount
                    elif event.event_type == 'expense_change':
                        monthly_out += event.amount
                    elif event.event_type == 'asset_transfer':

                        pass

            total_liquid = 0
            total_illiquid = 0

            for asset in assets:
                monthly_growth = asset.growth_rate / 100 / 12
                asset_value = asset.amount * (1 + monthly_growth) ** (month_index + 1)

                monthly_income = asset.annual_income_rate / 100 / 12 * asset.amount
                asset_value += monthly_income * (month_index + 1)

                if asset.asset_type == 'liquid':
                    total_liquid += asset_value
                else:
                    total_illiquid += asset_value

            net_cash_flow = monthly_in - monthly_out
            total_liquid += net_cash_flow * (month_index + 1)

            liquid_data.append(round(total_liquid, 2))
            illiquid_data.append(round(total_illiquid, 2))

        return {
            'liquid': liquid_data,
            'illiquid': illiquid_data,
            'dates': months
        }

    def calculate_steps(self):
        assets = Asset.objects.filter(user=self.user)
        cash_flows = CashFlow.objects.filter(user=self.user)
        events = Event.objects.filter(user=self.user)

        steps = []
        current_date = self.start_date
        month_index = 1

        while current_date <= self.end_date:
            # محاسبه ورودی‌ها و خروجی‌ها
            monthly_in = sum(cf.amount for cf in cash_flows if cf.flow_type == 'in')
            monthly_out = sum(cf.amount for cf in cash_flows if cf.flow_type == 'out')

            # اعمال رویدادها
            for event in events:
                if event.month == month_index:
                    if event.event_type == 'income_change':
                        monthly_in += event.amount
                    elif event.event_type == 'expense_change':
                        monthly_out += event.amount

            net = monthly_in - monthly_out

            total_liquid = 0
            total_illiquid = 0

            for asset in assets:
                monthly_growth = asset.growth_rate / 100 / 12
                asset_value = asset.amount * (1 + monthly_growth) ** month_index

                monthly_income = asset.annual_income_rate / 100 / 12 * asset.amount
                asset_value += monthly_income * month_index

                if asset.asset_type == 'liquid':
                    total_liquid += asset_value
                else:
                    total_illiquid += asset_value

            total_liquid += net * month_index

            total_assets = total_liquid + total_illiquid

            steps.append({
                'month': current_date.strftime('%b %Y'),
                'liquid': round(total_liquid, 2),
                'illiquid': round(total_illiquid, 2),
                'total_assets': round(total_assets, 2),
                'out': round(monthly_out, 2),
                'in': round(monthly_in, 2),
                'net': round(net, 2)
            })

            current_date = self._add_months(current_date, 1)
            month_index += 1

        return steps

    def _add_months(self, source_date, months):
        month = source_date.month - 1 + months
        year = source_date.year + month // 12
        month = month % 12 + 1

        import calendar
        last_day = calendar.monthrange(year, month)[1]
        day = min(source_date.day, last_day)

        return date(year, month, day)