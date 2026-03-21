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
| `category` | FK → Category | Expense categories only |
| `account` | FK → Account, nullable | `None` = global across all accounts |
| `amount_limit` | DecimalField(12, 2) | Always positive; the envelope ceiling in MAD |
| `start_day` | PositiveSmallIntegerField | 1–28; day of month the budget period resets |
| `rollover` | BooleanField | Whether unspent surplus carries forward |
| `created_at` | DateTimeField | Auto |
| `updated_at` | DateTimeField | Auto |

**Constraints:**
- `unique_together = [('category', 'account')]` — one budget per category per scope
- `start_day` capped at 28 to avoid February edge cases
- Only expense-type categories are valid (enforced in serializer)

---

## Business Logic

### Period Window

Pure utility function in `budgets/utils.py`:

```
def current_period(start_day, reference_date=today):
    if reference_date.day >= start_day:
        period_start = date(reference_date.year, reference_date.month, start_day)
    else:
        period_start = date(previous_month.year, previous_month.month, start_day)

    period_end = (period_start + relativedelta(months=1)) - timedelta(days=1)
    return period_start, period_end
```

### Spending Computation

Computed via ORM aggregation — never stored:

```
queryset = Transaction.objects.filter(
    type='expense',
    category=budget.category,
    date__range=(period_start, period_end),
)
if budget.account is not None:
    queryset = queryset.filter(account=budget.account)

spent = abs(queryset.aggregate(total=Sum('amount'))['total'] or 0)
remaining = budget.amount_limit - spent
utilization_pct = round((spent / budget.amount_limit) * 100, 1) if budget.amount_limit else 0
```

### Rollover Logic (history endpoint)

Walk backwards through past periods. Rollover carries surplus (positive delta) only — overspending does not create debt:

```
effective_limit = amount_limit
for each past period (oldest to newest):
    record = { period, spent, effective_limit }
    if rollover:
        surplus = max(effective_limit - spent, 0)
        effective_limit = amount_limit + surplus
    else:
        effective_limit = amount_limit
```

---

## API Endpoints

Base path: `/api/budgets/`

### CRUD

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/budgets/` | List all budgets with current period computed fields |
| POST | `/api/budgets/` | Create a budget |
| GET | `/api/budgets/{id}/` | Retrieve a budget with current period computed fields |
| PUT | `/api/budgets/{id}/` | Update a budget |
| DELETE | `/api/budgets/{id}/` | Delete a budget |

### Analytics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/budgets/{id}/history/` | Past periods for one budget (spent vs effective limit) |

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

```json
{
  "budget_id": "uuid",
  "history": [
    {
      "period": { "start": "2026-01-25", "end": "2026-02-24" },
      "effective_limit": "3000.00",
      "spent": "2500.00",
      "surplus": "500.00"
    },
    {
      "period": { "start": "2026-02-25", "end": "2026-03-24" },
      "effective_limit": "3500.00",
      "spent": "1850.00",
      "surplus": "1650.00"
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
  models.py          ← Budget model
  serializers.py     ← BudgetSerializer with computed fields
  views.py           ← BudgetViewSet + history action
  urls.py
  utils.py           ← current_period(), compute_spent()
  tests.py
  migrations/
    0001_initial.py
```

---

## Testing Plan

### Unit Tests

| Test | Description |
|------|-------------|
| `test_period_window_mid_month` | `start_day=25`, today=Mar 10 → period is Feb 25–Mar 24 |
| `test_period_window_on_start_day` | today equals start day → period starts today |
| `test_period_window_january_edge` | `start_day=25`, today=Jan 10 → period is Dec 25–Jan 24 |
| `test_spent_global` | spending across all accounts aggregates correctly |
| `test_spent_scoped_to_account` | only counts transactions for the linked account |
| `test_rollover_surplus_carries_forward` | unspent amount adds to next month's effective limit |
| `test_rollover_overspend_no_debt` | overspending does not reduce next month's limit |
| `test_no_rollover_fresh_each_period` | surplus ignored when `rollover=False` |
| `test_unique_constraint_global` | two global budgets for same category → validation error |
| `test_unique_constraint_per_account` | two budgets for same category + same account → validation error |

### Integration Tests

- Full CRUD via API (create, list, retrieve, update, delete)
- `/history/` endpoint with seeded transactions spanning multiple periods
- Validation: expense-only category enforcement, `start_day` range (1–28)

---

## Conventions Followed

- UUID primary keys (matches all existing models)
- `DecimalField` for all monetary values (not float)
- Computed fields via ORM aggregation (matches `Account.balance` pattern)
- App-level `urls.py` included via `finance_management_api/urls.py`
- New app registered in `INSTALLED_APPS`
