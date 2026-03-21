# Budgeting Feature — Design Spec

**Date:** 2026-03-21
**Project:** finance_management_api (Django 6.0.3)
**Status:** Approved

---

## Overview

Add monthly envelope budgeting to the personal finance management API. Users allocate a spending limit per expense category per month. Actual spending is computed dynamically from existing `Transaction` records — no redundant stored state.

---

## Scope

- Monthly envelope budgets (one per category per scope)
- Custom period start day (aligns with salary cycle, e.g. 25th of month)
- Optional rollover of unspent surplus to the next period
- Optional account scope (global or restricted to one account)
- Overspend tracking via analytics — no alerts

Out of scope: income budgets, alerts/notifications, multi-currency, bank integrations.

---

## Data Model

New Django app: `budgets/`

### `Budget`

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUIDField | Primary key, auto-generated |
| `category` | FK → Category, `on_delete=PROTECT` | Expense categories only; PROTECT prevents deleting a category with an active budget |
| `account` | FK → Account, nullable, `on_delete=CASCADE` | `None` = global across all accounts; CASCADE so deleting an account removes its budgets |
| `amount_limit` | DecimalField(12, 2) | Always positive; `MinValueValidator(Decimal('0.01'))` enforced |
| `start_day` | PositiveSmallIntegerField | 1–28; day of month the budget period resets; range validated in serializer |
| `rollover` | BooleanField | Whether unspent surplus carries forward |
| `created_at` | DateTimeField | Auto |
| `updated_at` | DateTimeField | Auto |

**Constraints (via `Meta.constraints`):**

PostgreSQL treats `NULL != NULL`, so `unique_together` on a nullable field does not protect the global case. Use two conditional constraints:

```python
constraints = [
    models.UniqueConstraint(
        fields=['category', 'account'],
        condition=models.Q(account__isnull=False),
        name='unique_budget_category_account',
    ),
    models.UniqueConstraint(
        fields=['category'],
        condition=models.Q(account__isnull=True),
        name='unique_budget_category_global',
    ),
]
```

Serializer `validate()` must also enforce global uniqueness (to return HTTP 400 instead of 500 on IntegrityError).

**Coexistence policy:** A global budget and an account-scoped budget for the same category are permitted to coexist. They are independent records queried separately. No double-counting occurs.

**Default ordering:** `['category__name', 'created_at']`

---

## Business Logic

### Period Window

Pure utility function in `budgets/utils.py`:

```python
def current_period(start_day: int, reference_date: date = None) -> tuple[date, date]:
    today = reference_date or date.today()
    if today.day >= start_day:
        period_start = today.replace(day=start_day)
    else:
        prev = today - relativedelta(months=1)
        period_start = prev.replace(day=start_day)
    period_end = (period_start + relativedelta(months=1)) - timedelta(days=1)
    return period_start, period_end
```

### Last N Periods

```python
def last_n_periods(start_day: int, n: int, reference_date: date = None) -> list[tuple[date, date]]:
    """
    Returns a list of (period_start, period_end) tuples, oldest-first,
    for the last n periods ending with (and including) the current period.
    n must be >= 1.
    """
    today = reference_date or date.today()
    current_start, current_end = current_period(start_day, today)
    periods = []
    for i in range(n - 1, -1, -1):
        start = current_start - relativedelta(months=i)
        end = (start + relativedelta(months=1)) - timedelta(days=1)
        periods.append((start, end))
    return periods  # ascending chronological order
```

The current in-progress period is always included as the last (most recent) entry.

### Spending Computation

```python
def compute_spent(budget, period_start, period_end) -> Decimal:
    qs = Transaction.objects.filter(
        type='expense',
        category=budget.category,
        date__range=(period_start, period_end),
    )
    if budget.account is not None:
        qs = qs.filter(account=budget.account)
    total = qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    return abs(total)
```

**Note:** Transactions pre-dating the budget's creation but falling within the current period are included — intentional, for an accurate period picture.

**Note:** Null-category transactions are naturally excluded by `category=budget.category`. No extra guard needed.

### Rollover Logic (for `/history/` endpoint)

Walk through the last N periods oldest-first. History always uses the **current** `amount_limit` (no change-history tracking).

```python
effective_limit = budget.amount_limit
records = []
for period_start, period_end in last_n_periods(budget.start_day, n):
    spent = compute_spent(budget, period_start, period_end)
    remaining = effective_limit - spent  # negative = overspent
    surplus_carried = max(remaining, Decimal('0'))
    records.append({
        'period': {'start': period_start, 'end': period_end},
        'effective_limit': effective_limit,
        'spent': spent,
        'remaining': remaining,
    })
    effective_limit = budget.amount_limit + surplus_carried if budget.rollover else budget.amount_limit
```

If a budget was just created and has no transaction history, all `spent` values are `0.00`. The endpoint always returns exactly N records (never empty).

---

## API Endpoints

Base path: `/api/budgets/`

### CRUD

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/budgets/` | List all budgets with current period computed fields |
| POST | `/api/budgets/` | Create a budget |
| GET | `/api/budgets/{id}/` | Retrieve a budget with current period computed fields |
| PUT | `/api/budgets/{id}/` | Full update |
| PATCH | `/api/budgets/{id}/` | Partial update |
| DELETE | `/api/budgets/{id}/` | Delete a budget |

### Analytics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/budgets/{id}/history/` | Past periods. `?periods=N` (default 12, min 1, max 24; outside range → HTTP 400) |

The `history` endpoint is a DRF `@action(detail=True, methods=['get'])` on `BudgetViewSet`.

### Serializer Design

**Read vs Write for `account` and `category`:**
- On **write** (POST/PUT/PATCH): accept a UUID string (or `null` for `account`). Use `PrimaryKeyRelatedField`.
- On **read** (GET): return a nested object `{"id": "uuid", "name": "..."}` (plus `color`/`type` for category). Implemented via `to_representation()` override on `BudgetSerializer`.

**Computed fields** (`period`, `spent`, `remaining`, `utilization_pct`) are `SerializerMethodField`. `current_period()` and `compute_spent()` are called inside each `get_<field>` method.

**Performance:** The viewset queryset applies `select_related('category', 'account')` to avoid N+1 FK lookups on list responses.

**Expense-only enforcement:** `validate_category()` in `BudgetSerializer` checks `category.type == 'expense'` and raises `ValidationError("Only expense categories can have a budget.")` if not. Returns HTTP 400.

**`utilization_pct`:** `round(float(spent / budget.amount_limit) * 100, 1) if budget.amount_limit > 0 else 0.0` — returned as a Python float.

### Response Shape (list/detail)

```json
{
  "id": "uuid",
  "category": { "id": "uuid", "name": "Food", "color": "#hex", "type": "expense" },
  "account": null,
  "amount_limit": "3000.00",
  "start_day": 25,
  "rollover": false,
  "period": {
    "start": "2026-02-25",
    "end": "2026-03-24"
  },
  "spent": "1850.00",
  "remaining": "1150.00",
  "utilization_pct": 61.7
}
```

### History Response Shape

Periods returned **oldest-first** (ascending chronological). `remaining` can be negative (overspent). The `surplus_carried` field is intentionally absent from the response — it is an internal rollover calculation, not user-facing data.

```json
{
  "budget_id": "uuid",
  "periods_requested": 12,
  "history": [
    {
      "period": { "start": "2026-01-25", "end": "2026-02-24" },
      "effective_limit": "3000.00",
      "spent": "2500.00",
      "remaining": "500.00"
    },
    {
      "period": { "start": "2026-02-25", "end": "2026-03-24" },
      "effective_limit": "3500.00",
      "spent": "1850.00",
      "remaining": "1650.00"
    }
  ]
}
```

---

## App Structure

```
budgets/
  __init__.py
  apps.py
  admin.py
  models.py          ← Budget model with conditional UniqueConstraints
  serializers.py     ← BudgetSerializer (SerializerMethodField + to_representation)
  views.py           ← BudgetViewSet + @action history
  urls.py
  utils.py           ← current_period(), last_n_periods(), compute_spent()
  tests.py
  migrations/
    0001_initial.py
```

---

## Testing Plan

### Unit Tests — `budgets/tests.py`

**Period window (`current_period`):**

| Test | Description |
|------|-------------|
| `test_period_window_start_day_1` | `start_day=1`, today=Mar 10 → period is Mar 1–Mar 31 |
| `test_period_window_mid_month` | `start_day=25`, today=Mar 10 → period is Feb 25–Mar 24 |
| `test_period_window_on_start_day` | today equals start_day → period starts today |
| `test_period_window_january_edge` | `start_day=25`, today=Jan 10 → period is Dec 25–Jan 24 |

**Period list (`last_n_periods`):**

| Test | Description |
|------|-------------|
| `test_last_n_periods_count` | returns exactly N periods |
| `test_last_n_periods_ascending` | periods returned oldest-first |
| `test_last_n_periods_includes_current` | last entry matches `current_period()` |

**Spending:**

| Test | Description |
|------|-------------|
| `test_spent_global` | aggregates across all accounts |
| `test_spent_scoped_to_account` | only counts transactions for the linked account |
| `test_spent_excludes_income` | income transactions not counted |
| `test_spent_excludes_other_category` | transactions from other categories excluded |

**Rollover:**

| Test | Description |
|------|-------------|
| `test_rollover_surplus_carries_forward` | unspent amount adds to next month's effective limit |
| `test_rollover_overspend_no_debt` | overspending → `remaining` is negative, next limit unchanged |
| `test_no_rollover_fresh_each_period` | surplus ignored when `rollover=False` |
| `test_rollover_new_budget_no_history` | new budget: N records all with `spent=0` |

**Constraints & validation:**

| Test | Description |
|------|-------------|
| `test_unique_constraint_global` | two global budgets for same category → HTTP 400 |
| `test_unique_constraint_per_account` | two budgets for same category + same account → HTTP 400 |
| `test_global_and_scoped_coexist` | global + account-scoped for same category is allowed |
| `test_income_category_rejected` | income category → HTTP 400 |
| `test_amount_limit_zero_rejected` | `amount_limit=0` → HTTP 400 |
| `test_start_day_out_of_range` | `start_day=0` and `start_day=29` → HTTP 400 |

### Integration Tests (API)

- Full CRUD including `PATCH` partial update
- `GET /api/budgets/` ordering is by `category__name`
- `GET /api/budgets/{id}/history/` default 12 periods, oldest-first
- `GET /api/budgets/{id}/history/?periods=3` returns exactly 3 periods
- `GET /api/budgets/{id}/history/?periods=0` → HTTP 400
- `GET /api/budgets/{id}/history/?periods=25` → HTTP 400
- `account` field: UUID on write, nested object on read

---

## Conventions Followed

- UUID primary keys (matches all existing models)
- `DecimalField` for all monetary values; `utilization_pct` is float
- Computed fields via ORM aggregation (matches `Account.balance` pattern)
- Conditional `UniqueConstraint` in `Meta.constraints` (not `unique_together`)
- `@action(detail=True)` for history endpoint
- `SerializerMethodField` for computed response fields; `to_representation()` for nested read shape
- `select_related('category', 'account')` on list queryset to avoid N+1
- App-level `urls.py` included via `finance_management_api/urls.py`
- New app registered in `INSTALLED_APPS`
