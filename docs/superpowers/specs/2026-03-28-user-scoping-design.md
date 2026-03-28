# User Ownership & Data Scoping

**Date:** 2026-03-28
**Status:** Approved
**Scope:** `accounts`, `goals`, `budgets`, `transactions`, `analytics`, `categories`

---

## Problem

All data models (`Account`, `Transaction`, `Goal`, `Budget`, `Category`) are unscoped. Any authenticated user can read and modify any other user's data. Authentication is enforced (JWT, `IsAuthenticated` globally) but ownership is not.

---

## Decisions

| Question | Decision |
|---|---|
| Are categories user-specific or global? | Global — shared across all users |
| What happens to existing data? | Deleted (clean slate) |
| `seed_data` command behavior | Requires `--user <username>` argument |

---

## Architecture

### Data Model Changes

Three models gain a `user` FK. `Transaction` and `Category` are untouched at the model level.

| Model | Change |
|---|---|
| `Account` | `user = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name='accounts')` |
| `Goal` | `user = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name='goals')` |
| `Budget` | `user = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name='budgets')` |
| `Transaction` | No model change — ownership derived via `account__user` |
| `Category` | No change — global/shared |

### View Layer — `UserOwnedMixin`

A new `core/mixins.py` module provides a reusable mixin for all user-owned viewsets:

```python
class UserOwnedMixin:
    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
```

- `AccountViewSet`, `GoalViewSet`, `BudgetViewSet` inherit `UserOwnedMixin`
- `TransactionViewSet` does **not** use the mixin — it filters via `account__user=self.request.user` since Transaction has no direct `user` FK
- `TransactionFilter` restricts the `account` filter to accounts owned by the current user — the `account` filter field uses `queryset=Account.objects.filter(user=request.user)` via a custom `filterset_class` override
- `CategoryViewSet` is unchanged — returns all categories for all authenticated users

### Analytics

`MonthlyFlowView` and `CategorySplitView` in the `analytics` app currently query all transactions. Both views must filter by `account__user=request.user`.

### Budget Unique Constraints

The existing constraints are scoped per user to allow two different users to have a budget for the same category:

| Old constraint | New constraint |
|---|---|
| `(category, account)` when account is not null | `(user, category, account)` when account is not null |
| `(category)` when account is null | `(user, category)` when account is null |

---

## Migrations

One migration per affected app (`accounts`, `goals`, `budgets`). Each migration:
1. `RunPython` — deletes all existing rows (clean slate)
2. `AddField` — adds the non-nullable `user` FK

`budgets` migration additionally updates the unique constraints.

---

## `seed_data` Command

Gains a required `--user <username>` argument:
- Resolves user via `User.objects.get(username=...)`
- Raises `CommandError` if username not found
- Passes the resolved user when creating every `Account`, `Goal`, and `Budget`
- Transactions are created under user-owned accounts — no extra argument needed

Usage: `python manage.py seed_data --user admin`

---

## Affected Files

| File | Change |
|---|---|
| `accounts/models.py` | Add `user` FK |
| `goals/models.py` | Add `user` FK |
| `budgets/models.py` | Add `user` FK + update unique constraints |
| `core/mixins.py` | New — `UserOwnedMixin` |
| `accounts/views.py` | Inherit `UserOwnedMixin` |
| `goals/views.py` | Inherit `UserOwnedMixin` |
| `budgets/views.py` | Inherit `UserOwnedMixin` |
| `transactions/views.py` | Filter via `account__user=request.user` |
| `analytics/views.py` | Filter via `account__user=request.user` |
| `transactions/management/commands/seed_data.py` | Add `--user` argument |
| `accounts/migrations/000X_add_user_fk.py` | New migration |
| `goals/migrations/000X_add_user_fk.py` | New migration |
| `budgets/migrations/000X_add_user_fk_update_constraints.py` | New migration |

---

## Out of Scope

- No changes to the authentication app
- No changes to serializers (user field is not exposed in API responses)
- No changes to URL routing
- No admin panel changes
