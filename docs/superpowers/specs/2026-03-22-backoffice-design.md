# Backoffice — Django Admin Configuration

**Date:** 2026-03-22
**Status:** Approved

## Overview

Configure Django's built-in admin panel (`/admin`) with enhanced model registration across all five domain models. The goal is a fully navigable, searchable, filterable admin for day-to-day data management without any custom frontend work.

## Scope

All five domain models registered with enhanced admin classes:

- `accounts.Account`
- `categories.Category`
- `transactions.Transaction`
- `goals.Goal`
- `budgets.Budget`

Django's built-in `auth.User` admin is left as-is (already registered by Django).

---

## Per-Model Admin Design

### `AccountAdmin`

| Setting | Value |
|---|---|
| `list_display` | `name`, `balance` (computed), `transaction_count` (computed), `created_at` |
| `search_fields` | `name` |
| `readonly_fields` | `id`, `created_at`, `balance`, `transaction_count` |
| Inline | `TransactionInline` — last 10 transactions, read-only tabular inline |

`balance` is computed via `Sum('transactions__amount')` annotation (mirrors the API serializer logic).
`transaction_count` is computed via `Count('transactions')` annotation.

---

### `CategoryAdmin`

| Setting | Value |
|---|---|
| `list_display` | `name`, `type`, `color_preview` (computed), `transaction_count` (computed) |
| `search_fields` | `name` |
| `list_filter` | `type` |
| `readonly_fields` | `id`, `color_preview`, `transaction_count` |

Note: `Category` has no `created_at` or `updated_at` fields — no timestamp readonly fields apply here.

`color_preview` renders a small HTML `<span>` with `background-color` set to the stored color value, displayed using `mark_safe`.
`transaction_count` uses `Count('transactions')` annotation.

---

### `TransactionAdmin`

| Setting | Value |
|---|---|
| `list_display` | `label`, `amount`, `type`, `account`, `category`, `date` |
| `search_fields` | `label` |
| `list_filter` | `type`, `category` (RelatedOnlyFieldListFilter), `account` (RelatedOnlyFieldListFilter) |
| `date_hierarchy` | `date` |
| `ordering` | `-date` |
| `readonly_fields` | `id`, `created_at`, `updated_at` |

Use `RelatedOnlyFieldListFilter` for the `category` and `account` FK filters so the sidebar only lists values that actually appear in existing transactions (prevents showing every category/account regardless of use):

```python
list_filter = [
    'type',
    ('category', admin.RelatedOnlyFieldListFilter),
    ('account', admin.RelatedOnlyFieldListFilter),
]
```

---

### `GoalAdmin`

| Setting | Value |
|---|---|
| `list_display` | `label`, `current`, `target`, `progress_pct` (computed), `icon`, `color_preview` (computed) |
| `search_fields` | `label` |
| `readonly_fields` | `id`, `progress_pct`, `color_preview` |

`icon` is an editable `CharField` — it appears in `list_display` for visibility but remains editable on the detail page (no readonly constraint needed).

`progress_pct` = `(current / target) × 100`, rounded to 1 decimal place. Returns `"0%"` if target is zero.

---

### `BudgetAdmin`

| Setting | Value |
|---|---|
| `list_display` | `__str__`, `category`, `account_display` (computed), `amount_limit`, `start_day`, `rollover` |
| `list_filter` | `rollover`, `account`, `category` |
| `readonly_fields` | `id`, `created_at`, `updated_at` |

`account_display` shows the account name or `"global"` when `account` is null.

---

## `TransactionInline`

Used inside `AccountAdmin` to show recent transactions:

- Type: `TabularInline`
- Model: `Transaction`
- `extra = 0` (no blank rows)
- All fields `readonly` (view-only inside the account page)
- Override `get_queryset()` to limit to the 10 most recent transactions ordered by `-date`. The `max_num` attribute does **not** control how many existing rows are shown — `get_queryset()` must be overridden:

```python
def get_queryset(self, request):
    return super().get_queryset(request).order_by('-date')[:10]
```

---

## Implementation Notes

- Each app's `admin.py` is edited in-place — no new files created.
- Computed columns use `@admin.display` decorator with `short_description` and `ordering` where applicable.
- Annotations (balance, transaction_count) are added via `get_queryset()` override so Django can sort by them in the list view.
- `color_preview` is used in both `CategoryAdmin` and `GoalAdmin`. Both use `mark_safe` to render a colored swatch. The `color` field on both models is a free-form `CharField(max_length=30)` — values arrive via the API and could theoretically contain arbitrary strings. Before calling `mark_safe`, validate that the value matches a safe CSS color pattern (hex `#rrggbb`, named color, or `rgb()`). Use a simple regex or strip to a whitelist before rendering:
  ```python
  import re
  def color_preview(self, obj):
      color = obj.color
      if not re.match(r'^#[0-9a-fA-F]{3,6}$|^[a-zA-Z]+$|^rgb\([\d\s,]+\)$', color):
          color = '#cccccc'  # fallback
      return mark_safe(f'<span style="...background:{color}..."></span>')
  ```

---

## Files Changed

| File | Change |
|---|---|
| `accounts/admin.py` | `AccountAdmin` with inline and computed balance |
| `categories/admin.py` | `CategoryAdmin` with color preview |
| `transactions/admin.py` | `TransactionAdmin` with date hierarchy |
| `goals/admin.py` | `GoalAdmin` with progress percentage |
| `budgets/admin.py` | `BudgetAdmin` with scope display |

No migrations required. No new models. No changes to `settings.py` or `urls.py` (Django admin is already wired up).
