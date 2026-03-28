from datetime import date, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.db.models import Sum
from transactions.models import Transaction


def current_period(start_day: int, reference_date: date = None) -> tuple:
    """
    Returns (period_start, period_end) for the budget period containing reference_date.

    The period starts on `start_day` and lasts exactly 1 month (e.g., if start_day=25,
    the period is the 25th of one month through the 24th of the next).

    Args:
        start_day: Day of month (1-31) when the period begins.
        reference_date: Date within the period (defaults to today).

    Returns:
        Tuple of (period_start, period_end) as date objects.
    """
    today = reference_date or date.today()
    if today.day >= start_day:
        period_start = today.replace(day=start_day)
    else:
        prev = today - relativedelta(months=1)
        period_start = prev.replace(day=start_day)
    period_end = (period_start + relativedelta(months=1)) - timedelta(days=1)
    return period_start, period_end


def last_n_periods(start_day: int, n: int, reference_date: date = None) -> list:
    """
    Returns a list of (period_start, period_end) tuples, oldest-first,
    for the last n periods ending with (and including) the current period.

    Args:
        start_day: Day of month when each period begins.
        n: Number of periods to return (must be >= 1).
        reference_date: Reference date for current period (defaults to today).

    Returns:
        List of (start, end) date tuples, sorted ascending by start date.
    """
    today = reference_date or date.today()
    current_start, _ = current_period(start_day, today)
    periods = []
    for i in range(n - 1, -1, -1):
        start = current_start - relativedelta(months=i)
        end = (start + relativedelta(months=1)) - timedelta(days=1)
        periods.append((start, end))
    return periods


def compute_spent(budget, period_start: date, period_end: date) -> Decimal:
    """
    Computes total spending (expenses only) for a budget within a period.

    Respects budget scoping:
    - If budget.account is None, sum all expenses in the category.
    - If budget.account is set, sum only expenses from that account.

    Args:
        budget: A Budget instance.
        period_start: Start of the period (inclusive).
        period_end: End of the period (inclusive).

    Returns:
        Absolute value of total expenses (Decimal).
    """
    qs = Transaction.objects.filter(
        type='expense',
        category=budget.category,
        date__range=(period_start, period_end),
        account__user=budget.user,
    )
    if budget.account is not None:
        qs = qs.filter(account=budget.account)
    total = qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    return abs(total)
