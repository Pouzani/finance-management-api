# User Ownership & Data Scoping — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scope all financial data (accounts, goals, budgets, transactions, analytics) to the authenticated user so no user can read or modify another user's data.

**Architecture:** Add a `user` FK to `Account`, `Goal`, and `Budget` models. `Transaction` ownership is derived via `account__user`. A `UserOwnedMixin` in `core/mixins.py` centralises the `get_queryset` filter and `perform_create` ownership injection for the three owned viewsets. Migrations delete all existing rows before adding the non-nullable FK (clean-slate strategy).

**Tech Stack:** Django 6.0.3, Django REST Framework, `rest_framework_simplejwt`, `django_filters`, SQLite (dev) / PostgreSQL (prod).

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Create | `core/__init__.py` | Makes `core` a Python package |
| Create | `core/mixins.py` | `UserOwnedMixin` for owned viewsets |
| Modify | `accounts/models.py` | Add `user` FK |
| Modify | `goals/models.py` | Add `user` FK |
| Modify | `budgets/models.py` | Add `user` FK + update unique constraints |
| Create | `accounts/migrations/0002_account_add_user.py` | RunPython delete + AddField |
| Create | `goals/migrations/0002_goal_add_user.py` | RunPython delete + AddField |
| Create | `budgets/migrations/0002_budget_add_user.py` | RunPython delete + AddField + constraint swap |
| Modify | `accounts/views.py` | Inherit `UserOwnedMixin` |
| Modify | `goals/views.py` | Inherit `UserOwnedMixin` |
| Modify | `budgets/views.py` | Inherit `UserOwnedMixin` |
| Modify | `budgets/serializers.py` | Scope account queryset + scope validate to user |
| Modify | `transactions/views.py` | Filter queryset via `account__user` |
| Modify | `analytics/views.py` | Filter transactions via `account__user` |
| Modify | `transactions/management/commands/seed_data.py` | Add `--user` argument |
| Modify | `accounts/tests.py` | Add auth + user FK to all helpers |
| Modify | `goals/tests.py` | Add auth + user FK to all helpers |
| Modify | `budgets/tests.py` | Add auth + user FK to all helpers |
| Modify | `transactions/tests.py` | Add auth + user FK to all helpers |
| Modify | `analytics/tests.py` | Add auth + user FK to all helpers |

---

## Task 1: Create `UserOwnedMixin`

**Files:**
- Create: `core/__init__.py`
- Create: `core/mixins.py`

- [ ] **Step 1: Create `core/__init__.py`**

```bash
touch /path/to/finance-management-api/core/__init__.py
```

Create an empty file at `core/__init__.py`. No content needed.

- [ ] **Step 2: Write the failing placeholder test**

We will test the mixin indirectly through the viewsets in later tasks. For now, create `core/mixins.py` with the mixin implementation directly (it is too simple to need a standalone unit test — behaviour is fully covered by the viewset tests in tasks 5–7).

- [ ] **Step 3: Implement `core/mixins.py`**

```python
class UserOwnedMixin:
    """
    Mixin for ModelViewSet subclasses that filters querysets to the
    authenticated user and injects the user on create.
    """
    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
```

- [ ] **Step 4: Commit**

```bash
git add core/__init__.py core/mixins.py
git commit -m "feat: add UserOwnedMixin to core"
```

---

## Task 2: Add `user` FK to `Account` + migration

**Files:**
- Modify: `accounts/models.py`
- Create: `accounts/migrations/0002_account_add_user.py`

- [ ] **Step 1: Write a failing test for the new field**

In `accounts/tests.py`, add a test to `AccountModelTest` (before implementing) to confirm `Account` has a `user` attribute:

```python
def test_account_has_user_field(self):
    from django.contrib.auth.models import User
    from accounts.models import Account
    user = User.objects.create_user(username='u1', password='pass')
    account = Account.objects.create(name='Test', user=user)
    self.assertEqual(account.user, user)
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
python manage.py test accounts.tests.AccountModelTest.test_account_has_user_field
```

Expected: `TypeError: Account() got an unexpected keyword argument 'user'`

- [ ] **Step 3: Update `accounts/models.py`**

```python
import uuid
from django.conf import settings
from django.db import models


class Account(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='accounts',
    )
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
```

- [ ] **Step 4: Create `accounts/migrations/0002_account_add_user.py`**

```python
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def delete_all_accounts(apps, schema_editor):
    Account = apps.get_model('accounts', 'Account')
    Account.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(delete_all_accounts, migrations.RunPython.noop),
        migrations.AddField(
            model_name='account',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='accounts',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
```

- [ ] **Step 5: Apply the migration**

```bash
python manage.py migrate accounts
```

Expected: `Applying accounts.0002_account_add_user... OK`

- [ ] **Step 6: Run the test to confirm it passes**

```bash
python manage.py test accounts.tests.AccountModelTest.test_account_has_user_field
```

Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add accounts/models.py accounts/migrations/0002_account_add_user.py
git commit -m "feat: add user FK to Account model"
```

---

## Task 3: Add `user` FK to `Goal` + migration

**Files:**
- Modify: `goals/models.py`
- Create: `goals/migrations/0002_goal_add_user.py`

- [ ] **Step 1: Write a failing test**

In `goals/tests.py`, add to `GoalModelTest`:

```python
def test_goal_has_user_field(self):
    from django.contrib.auth.models import User
    from goals.models import Goal
    user = User.objects.create_user(username='u1', password='pass')
    goal = Goal.objects.create(
        label='Test', current='0', target='1000',
        icon='star', color='#fff', user=user,
    )
    self.assertEqual(goal.user, user)
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
python manage.py test goals.tests.GoalModelTest.test_goal_has_user_field
```

Expected: `TypeError: Goal() got an unexpected keyword argument 'user'`

- [ ] **Step 3: Update `goals/models.py`**

```python
import uuid
from django.conf import settings
from django.db import models


class Goal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='goals',
    )
    label = models.CharField(max_length=500)
    current = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    target = models.DecimalField(max_digits=12, decimal_places=2)
    icon = models.CharField(max_length=100)
    color = models.CharField(max_length=30)

    class Meta:
        ordering = ['label']

    def __str__(self):
        return self.label
```

- [ ] **Step 4: Create `goals/migrations/0002_goal_add_user.py`**

```python
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def delete_all_goals(apps, schema_editor):
    Goal = apps.get_model('goals', 'Goal')
    Goal.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('goals', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(delete_all_goals, migrations.RunPython.noop),
        migrations.AddField(
            model_name='goal',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='goals',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
```

- [ ] **Step 5: Apply the migration**

```bash
python manage.py migrate goals
```

Expected: `Applying goals.0002_goal_add_user... OK`

- [ ] **Step 6: Run the test**

```bash
python manage.py test goals.tests.GoalModelTest.test_goal_has_user_field
```

Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add goals/models.py goals/migrations/0002_goal_add_user.py
git commit -m "feat: add user FK to Goal model"
```

---

## Task 4: Add `user` FK to `Budget` + update constraints + migration

**Files:**
- Modify: `budgets/models.py`
- Create: `budgets/migrations/0002_budget_add_user.py`

- [ ] **Step 1: Write a failing test**

In `budgets/tests.py`, add to `BudgetModelTest`:

```python
def test_budget_has_user_field(self):
    from django.contrib.auth.models import User
    user = User.objects.create_user(username='u1', password='pass')
    budget = Budget.objects.create(
        category=self.category,
        amount_limit='500.00',
        start_day=1,
        rollover=False,
        user=user,
    )
    self.assertEqual(budget.user, user)
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
python manage.py test budgets.tests.BudgetModelTest.test_budget_has_user_field
```

Expected: `TypeError: Budget() got an unexpected keyword argument 'user'`

- [ ] **Step 3: Update `budgets/models.py`**

```python
import uuid
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Budget(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='budgets',
    )
    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.PROTECT,
        related_name='budgets',
    )
    account = models.ForeignKey(
        'accounts.Account',
        on_delete=models.CASCADE,
        related_name='budgets',
        null=True,
        blank=True,
    )
    amount_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    start_day = models.PositiveSmallIntegerField()
    rollover = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category__name', 'created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'category', 'account'],
                condition=models.Q(account__isnull=False),
                name='unique_budget_user_category_account',
            ),
            models.UniqueConstraint(
                fields=['user', 'category'],
                condition=models.Q(account__isnull=True),
                name='unique_budget_user_category_global',
            ),
        ]

    def __str__(self):
        scope = f' [{self.account.name}]' if self.account_id else ' [global]'
        return f'{self.category.name}{scope} — {self.amount_limit} MAD'
```

- [ ] **Step 4: Create `budgets/migrations/0002_budget_add_user.py`**

```python
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def delete_all_budgets(apps, schema_editor):
    Budget = apps.get_model('budgets', 'Budget')
    Budget.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('budgets', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(delete_all_budgets, migrations.RunPython.noop),
        migrations.AddField(
            model_name='budget',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='budgets',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RemoveConstraint(
            model_name='budget',
            name='unique_budget_category_account',
        ),
        migrations.RemoveConstraint(
            model_name='budget',
            name='unique_budget_category_global',
        ),
        migrations.AddConstraint(
            model_name='budget',
            constraint=models.UniqueConstraint(
                condition=models.Q(account__isnull=False),
                fields=['user', 'category', 'account'],
                name='unique_budget_user_category_account',
            ),
        ),
        migrations.AddConstraint(
            model_name='budget',
            constraint=models.UniqueConstraint(
                condition=models.Q(account__isnull=True),
                fields=['user', 'category'],
                name='unique_budget_user_category_global',
            ),
        ),
    ]
```

- [ ] **Step 5: Apply the migration**

```bash
python manage.py migrate budgets
```

Expected: `Applying budgets.0002_budget_add_user... OK`

- [ ] **Step 6: Run the test**

```bash
python manage.py test budgets.tests.BudgetModelTest.test_budget_has_user_field
```

Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add budgets/models.py budgets/migrations/0002_budget_add_user.py
git commit -m "feat: add user FK to Budget model, update unique constraints"
```

---

## Task 5: Apply `UserOwnedMixin` to `AccountViewSet` + update account tests

**Files:**
- Modify: `accounts/views.py`
- Modify: `accounts/tests.py`

- [ ] **Step 1: Write failing tests for user isolation in `accounts/tests.py`**

Replace the entire `AccountAPITest` class and update `AccountModelTest` and `AccountAdminTest` helpers:

```python
import uuid
from decimal import Decimal
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory
from rest_framework.test import APIClient
from rest_framework import status

from accounts.admin import AccountAdmin


def make_user(username='testuser'):
    return User.objects.create_user(username=username, password='testpass123')


class AccountModelTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_account_has_uuid_pk(self):
        from accounts.models import Account
        account = Account.objects.create(name="CIH Principale", user=self.user)
        self.assertIsInstance(account.id, uuid.UUID)

    def test_account_str(self):
        from accounts.models import Account
        account = Account.objects.create(name="Wafacash", user=self.user)
        self.assertEqual(str(account), "Wafacash")

    def test_account_created_at_set(self):
        from accounts.models import Account
        account = Account.objects.create(name="Attijari", user=self.user)
        self.assertIsNotNone(account.created_at)

    def test_account_has_user_field(self):
        from accounts.models import Account
        account = Account.objects.create(name='Test', user=self.user)
        self.assertEqual(account.user, self.user)

    def test_balance_zero_with_no_transactions(self):
        from accounts.models import Account
        from django.db.models import Sum, Value, DecimalField
        from django.db.models.functions import Coalesce
        account = Account.objects.create(name="Empty Account", user=self.user)
        annotated = Account.objects.annotate(
            balance=Coalesce(Sum('transactions__amount'), Value(0), output_field=DecimalField())
        ).get(pk=account.pk)
        self.assertEqual(annotated.balance, 0)

    def test_balance_computed_from_transactions(self):
        from accounts.models import Account
        from categories.models import Category
        from transactions.models import Transaction
        from django.db.models import Sum, Value, DecimalField
        from django.db.models.functions import Coalesce
        account = Account.objects.create(name="CIH", user=self.user)
        category = Category.objects.create(name="Salaire", color="#00FF00", type="income")
        Transaction.objects.create(
            label="Salary", amount=Decimal("5000.00"),
            date="2024-01-15", type="income", account=account, category=category
        )
        Transaction.objects.create(
            label="Rent", amount=Decimal("-1500.00"),
            date="2024-01-16", type="expense", account=account, category=category
        )
        annotated = Account.objects.annotate(
            balance=Coalesce(Sum('transactions__amount'), Value(0), output_field=DecimalField())
        ).get(pk=account.pk)
        self.assertEqual(annotated.balance, Decimal("3500.00"))


class AccountAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.url = '/api/accounts/'

    def _make_account(self, name="CIH", user=None):
        from accounts.models import Account
        return Account.objects.create(name=name, user=user or self.user)

    def test_unauthenticated_request_returns_401(self):
        unauth_client = APIClient()
        response = unauth_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_accounts(self):
        self._make_account("CIH")
        self._make_account("Wafacash")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_user_only_sees_own_accounts(self):
        other_user = make_user('other')
        self._make_account("My Account")
        self._make_account("Other Account", user=other_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'My Account')

    def test_create_account(self):
        response = self.client.post(self.url, {'name': 'CIH Principale'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'CIH Principale')
        self.assertIn('balance', response.data)

    def test_create_account_assigns_current_user(self):
        from accounts.models import Account
        self.client.post(self.url, {'name': 'New Account'}, format='json')
        account = Account.objects.get(name='New Account')
        self.assertEqual(account.user, self.user)

    def test_create_account_requires_name(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_account(self):
        account = self._make_account("Old Name")
        response = self.client.put(f'/api/accounts/{account.pk}/', {'name': 'New Name'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        account.refresh_from_db()
        self.assertEqual(account.name, 'New Name')

    def test_cannot_update_other_users_account(self):
        other_user = make_user('other')
        account = self._make_account("Other Account", user=other_user)
        response = self.client.put(f'/api/accounts/{account.pk}/', {'name': 'Hacked'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_account(self):
        account = self._make_account("To Delete")
        response = self.client.delete(f'/api/accounts/{account.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        from accounts.models import Account
        self.assertFalse(Account.objects.filter(pk=account.pk).exists())

    def test_cannot_delete_other_users_account(self):
        other_user = make_user('other')
        account = self._make_account("Other", user=other_user)
        response = self.client.delete(f'/api/accounts/{account.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AccountAdminTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin', password='password', email='admin@test.com'
        )
        self.client.force_login(self.superuser)

    def _make_account_with_transactions(self):
        from accounts.models import Account
        from categories.models import Category
        from transactions.models import Transaction
        account = Account.objects.create(name="CIH", user=self.superuser)
        cat = Category.objects.create(name="Salaire", color="#00FF00", type="income")
        Transaction.objects.create(
            label="Salary", amount=Decimal("5000.00"),
            date="2024-01-15", type="income", account=account, category=cat
        )
        Transaction.objects.create(
            label="Rent", amount=Decimal("-1500.00"),
            date="2024-01-16", type="expense", account=account, category=cat
        )
        return account

    def test_account_list_page_loads(self):
        self._make_account_with_transactions()
        response = self.client.get('/admin/accounts/account/')
        self.assertEqual(response.status_code, 200)

    def test_account_change_page_loads(self):
        account = self._make_account_with_transactions()
        response = self.client.get(f'/admin/accounts/account/{account.pk}/change/')
        self.assertEqual(response.status_code, 200)

    def test_balance_display_method(self):
        account = self._make_account_with_transactions()
        ma = AccountAdmin(model=account.__class__, admin_site=AdminSite())
        request = RequestFactory().get('/admin/accounts/account/')
        request.user = self.superuser
        qs = ma.get_queryset(request)
        annotated = qs.get(pk=account.pk)
        self.assertEqual(ma.balance(annotated), Decimal("3500.00"))

    def test_transaction_count_display_method(self):
        account = self._make_account_with_transactions()
        ma = AccountAdmin(model=account.__class__, admin_site=AdminSite())
        request = RequestFactory().get('/admin/accounts/account/')
        request.user = self.superuser
        qs = ma.get_queryset(request)
        annotated = qs.get(pk=account.pk)
        self.assertEqual(ma.transaction_count(annotated), 2)
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
python manage.py test accounts
```

Expected: Multiple failures — `401` instead of `200` on API tests (no auth), `TypeError` on model tests (no user arg).

- [ ] **Step 3: Update `accounts/views.py`**

```python
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from rest_framework.viewsets import ModelViewSet
from core.mixins import UserOwnedMixin
from accounts.models import Account
from accounts.serializers import AccountSerializer


class AccountViewSet(UserOwnedMixin, ModelViewSet):
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).annotate(
            balance=Coalesce(Sum('transactions__amount'), Value(0), output_field=DecimalField())
        ).order_by('name')
```

Note: `AccountViewSet` overrides `get_queryset` entirely (it needs the annotation), so instead of relying on `UserOwnedMixin.get_queryset`, we add `filter(user=self.request.user)` directly. `UserOwnedMixin` is still inherited for `perform_create`.

- [ ] **Step 4: Run the tests**

```bash
python manage.py test accounts
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add accounts/views.py accounts/tests.py
git commit -m "feat: scope AccountViewSet to authenticated user"
```

---

## Task 6: Apply `UserOwnedMixin` to `GoalViewSet` + update goal tests

**Files:**
- Modify: `goals/views.py`
- Modify: `goals/tests.py`

- [ ] **Step 1: Update `goals/tests.py`**

```python
import uuid
from decimal import Decimal
from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status


def make_user(username='testuser'):
    return User.objects.create_user(username=username, password='testpass123')


def make_goal(user, label='Vacances', current='500', target='5000'):
    from goals.models import Goal
    return Goal.objects.create(
        label=label, current=Decimal(current), target=Decimal(target),
        icon='plane', color='#3357FF', user=user,
    )


class GoalModelTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_goal_has_uuid_pk(self):
        from goals.models import Goal
        goal = Goal.objects.create(
            label="Fonds d'urgence", current=Decimal("2000"), target=Decimal("10000"),
            icon="shield", color="#FF5733", user=self.user,
        )
        self.assertIsInstance(goal.id, uuid.UUID)

    def test_goal_str(self):
        from goals.models import Goal
        goal = Goal.objects.create(
            label="Vacances", current=Decimal("500"), target=Decimal("5000"),
            icon="plane", color="#3357FF", user=self.user,
        )
        self.assertEqual(str(goal), "Vacances")

    def test_goal_has_user_field(self):
        from goals.models import Goal
        goal = Goal.objects.create(
            label='Test', current='0', target='1000',
            icon='star', color='#fff', user=self.user,
        )
        self.assertEqual(goal.user, self.user)


class GoalAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.url = '/api/goals/'

    def _goal_payload(self, **overrides):
        data = {
            'label': "Fonds d'urgence",
            'current': '2000.00',
            'target': '10000.00',
            'icon': 'shield',
            'color': '#FF5733',
        }
        data.update(overrides)
        return data

    def test_unauthenticated_request_returns_401(self):
        unauth_client = APIClient()
        response = unauth_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_goals(self):
        make_goal(self.user)
        make_goal(self.user, label='Goal 2')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_user_only_sees_own_goals(self):
        other_user = make_user('other')
        make_goal(self.user, label='My Goal')
        make_goal(other_user, label='Other Goal')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['label'], 'My Goal')

    def test_create_goal(self):
        response = self.client.post(self.url, self._goal_payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['label'], "Fonds d'urgence")

    def test_create_goal_assigns_current_user(self):
        from goals.models import Goal
        self.client.post(self.url, self._goal_payload(), format='json')
        goal = Goal.objects.get(label="Fonds d'urgence")
        self.assertEqual(goal.user, self.user)

    def test_create_goal_requires_fields(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_goal(self):
        goal = make_goal(self.user)
        payload = self._goal_payload(label="Updated Goal")
        response = self.client.put(f'/api/goals/{goal.pk}/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        goal.refresh_from_db()
        self.assertEqual(goal.label, 'Updated Goal')

    def test_cannot_update_other_users_goal(self):
        other_user = make_user('other')
        goal = make_goal(other_user)
        response = self.client.put(f'/api/goals/{goal.pk}/', self._goal_payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_goal(self):
        goal = make_goal(self.user)
        response = self.client.delete(f'/api/goals/{goal.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        from goals.models import Goal
        self.assertFalse(Goal.objects.filter(pk=goal.pk).exists())

    def test_cannot_delete_other_users_goal(self):
        other_user = make_user('other')
        goal = make_goal(other_user)
        response = self.client.delete(f'/api/goals/{goal.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class GoalAdminTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin', password='password', email='admin@test.com'
        )
        self.client.force_login(self.superuser)

    def _make_goal(self, current='250.00', target='1000.00', color='#3498db'):
        from goals.models import Goal
        return Goal.objects.create(
            label="Emergency Fund",
            current=Decimal(current),
            target=Decimal(target),
            icon="shield",
            color=color,
            user=self.superuser,
        )

    def test_goal_list_page_loads(self):
        self._make_goal()
        response = self.client.get('/admin/goals/goal/')
        self.assertEqual(response.status_code, 200)

    def test_progress_pct_calculated_correctly(self):
        from goals.admin import GoalAdmin
        from goals.models import Goal
        goal = self._make_goal(current='250.00', target='1000.00')
        ma = GoalAdmin(model=Goal, admin_site=AdminSite())
        self.assertEqual(ma.progress_pct(goal), '25.0%')

    def test_progress_pct_zero_when_target_is_zero(self):
        from goals.admin import GoalAdmin
        from goals.models import Goal
        ma = GoalAdmin(model=Goal, admin_site=AdminSite())
        goal = Goal(
            label="Zero Target", current=Decimal("0"), target=Decimal("0"),
            icon="x", color="#fff", user=self.superuser,
        )
        result = ma.progress_pct(goal)
        self.assertEqual(result, '0%')

    def test_color_preview_sanitizes_invalid_color(self):
        from goals.admin import GoalAdmin
        from goals.models import Goal
        goal = self._make_goal(color='"><script>xss</script>')
        ma = GoalAdmin(model=Goal, admin_site=AdminSite())
        result = str(ma.color_preview(goal))
        self.assertNotIn('<script>', result)
        self.assertIn('#cccccc', result)

    def test_color_preview_renders_valid_color(self):
        from goals.admin import GoalAdmin
        from goals.models import Goal
        goal = self._make_goal(color='#3498db')
        ma = GoalAdmin(model=Goal, admin_site=AdminSite())
        result = str(ma.color_preview(goal))
        self.assertIn('#3498db', result)
        self.assertIn('<span', result)
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
python manage.py test goals
```

Expected: Multiple failures.

- [ ] **Step 3: Update `goals/views.py`**

```python
from rest_framework.viewsets import ModelViewSet
from core.mixins import UserOwnedMixin
from goals.models import Goal
from goals.serializers import GoalSerializer


class GoalViewSet(UserOwnedMixin, ModelViewSet):
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
```

- [ ] **Step 4: Run the tests**

```bash
python manage.py test goals
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add goals/views.py goals/tests.py
git commit -m "feat: scope GoalViewSet to authenticated user"
```

---

## Task 7: Apply `UserOwnedMixin` to `BudgetViewSet` + update `BudgetSerializer` + update budget tests

**Files:**
- Modify: `budgets/views.py`
- Modify: `budgets/serializers.py`
- Modify: `budgets/tests.py`

- [ ] **Step 1: Update `budgets/tests.py`**

Replace the test helpers and API test classes. The utility tests (`CurrentPeriodTest`, `LastNPeriodsTest`, `ComputeSpentTest`) and admin tests need user FK on accounts. The API tests need authentication.

```python
import uuid
from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from accounts.models import Account
from categories.models import Category
from budgets.models import Budget
from budgets.utils import current_period, last_n_periods, compute_spent
from transactions.models import Transaction


def make_user(username='testuser'):
    return User.objects.create_user(username=username, password='testpass123')


class BudgetModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.account = Account.objects.create(name='CIH Bank', user=self.user)
        self.category = Category.objects.create(
            name='Food', color='#ff0000', type='expense'
        )
        self.income_category = Category.objects.create(
            name='Salary', color='#00ff00', type='income'
        )

    def test_budget_creation(self):
        budget = Budget.objects.create(
            category=self.category,
            amount_limit=Decimal('3000.00'),
            start_day=25,
            rollover=False,
            user=self.user,
        )
        self.assertIsInstance(budget.id, uuid.UUID)
        self.assertEqual(budget.amount_limit, Decimal('3000.00'))
        self.assertIsNone(budget.account)

    def test_budget_has_user_field(self):
        budget = Budget.objects.create(
            category=self.category,
            amount_limit='500.00',
            start_day=1,
            rollover=False,
            user=self.user,
        )
        self.assertEqual(budget.user, self.user)

    def test_budget_str(self):
        budget = Budget.objects.create(
            category=self.category,
            amount_limit=Decimal('3000.00'),
            start_day=25,
            rollover=False,
            user=self.user,
        )
        self.assertIn('Food', str(budget))


class CurrentPeriodTest(TestCase):
    def test_period_window_start_day_1(self):
        start, end = current_period(1, reference_date=date(2026, 3, 10))
        self.assertEqual(start, date(2026, 3, 1))
        self.assertEqual(end, date(2026, 3, 31))

    def test_period_window_mid_month(self):
        start, end = current_period(25, reference_date=date(2026, 3, 10))
        self.assertEqual(start, date(2026, 2, 25))
        self.assertEqual(end, date(2026, 3, 24))

    def test_period_window_on_start_day(self):
        start, end = current_period(25, reference_date=date(2026, 3, 25))
        self.assertEqual(start, date(2026, 3, 25))
        self.assertEqual(end, date(2026, 4, 24))

    def test_period_window_january_edge(self):
        start, end = current_period(25, reference_date=date(2026, 1, 10))
        self.assertEqual(start, date(2025, 12, 25))
        self.assertEqual(end, date(2026, 1, 24))


class LastNPeriodsTest(TestCase):
    def test_last_n_periods_count(self):
        periods = last_n_periods(25, 3, reference_date=date(2026, 3, 10))
        self.assertEqual(len(periods), 3)

    def test_last_n_periods_ascending(self):
        periods = last_n_periods(25, 3, reference_date=date(2026, 3, 10))
        starts = [p[0] for p in periods]
        self.assertEqual(starts, sorted(starts))

    def test_last_n_periods_includes_current(self):
        ref = date(2026, 3, 10)
        periods = last_n_periods(25, 3, reference_date=ref)
        current_start, current_end = current_period(25, reference_date=ref)
        self.assertEqual(periods[-1], (current_start, current_end))


class ComputeSpentTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.account_a = Account.objects.create(name='CIH Bank', user=self.user)
        self.account_b = Account.objects.create(name='Cash', user=self.user)
        self.food_cat = Category.objects.create(
            name='Food', color='#ff0000', type='expense'
        )
        self.other_cat = Category.objects.create(
            name='Transport', color='#0000ff', type='expense'
        )
        self.period_start = date(2026, 2, 25)
        self.period_end = date(2026, 3, 24)
        Transaction.objects.create(
            label='Groceries', amount=Decimal('-500.00'),
            date=date(2026, 3, 1), type='expense',
            account=self.account_a, category=self.food_cat
        )
        Transaction.objects.create(
            label='Market', amount=Decimal('-300.00'),
            date=date(2026, 3, 5), type='expense',
            account=self.account_b, category=self.food_cat
        )
        Transaction.objects.create(
            label='Salary', amount=Decimal('8000.00'),
            date=date(2026, 3, 1), type='income',
            account=self.account_a, category=self.food_cat
        )
        Transaction.objects.create(
            label='Bus', amount=Decimal('-50.00'),
            date=date(2026, 3, 2), type='expense',
            account=self.account_a, category=self.other_cat
        )

    def _make_budget(self, account=None):
        return Budget(
            category=self.food_cat,
            account=account,
            amount_limit=Decimal('3000.00'),
            start_day=25,
            rollover=False,
            user=self.user,
        )

    def test_spent_global(self):
        budget = self._make_budget(account=None)
        spent = compute_spent(budget, self.period_start, self.period_end)
        self.assertEqual(spent, Decimal('800.00'))

    def test_spent_scoped_to_account(self):
        budget = self._make_budget(account=self.account_a)
        spent = compute_spent(budget, self.period_start, self.period_end)
        self.assertEqual(spent, Decimal('500.00'))

    def test_spent_excludes_income(self):
        budget = self._make_budget(account=None)
        spent = compute_spent(budget, self.period_start, self.period_end)
        self.assertEqual(spent, Decimal('800.00'))

    def test_spent_excludes_other_category(self):
        budget = self._make_budget(account=None)
        spent = compute_spent(budget, self.period_start, self.period_end)
        self.assertEqual(spent, Decimal('800.00'))


class BudgetValidationTest(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.account = Account.objects.create(name='CIH Bank', user=self.user)
        self.expense_cat = Category.objects.create(
            name='Food', color='#ff0000', type='expense'
        )
        self.income_cat = Category.objects.create(
            name='Salary', color='#00ff00', type='income'
        )
        self.url = '/api/budgets/'

    def test_unauthenticated_request_returns_401(self):
        from rest_framework.test import APIClient
        unauth = APIClient()
        res = unauth.get(self.url)
        self.assertEqual(res.status_code, 401)

    def test_income_category_rejected(self):
        res = self.client.post(self.url, {
            'category': str(self.income_cat.id),
            'amount_limit': '3000.00',
            'start_day': 25,
            'rollover': False,
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_amount_limit_zero_rejected(self):
        res = self.client.post(self.url, {
            'category': str(self.expense_cat.id),
            'amount_limit': '0.00',
            'start_day': 25,
            'rollover': False,
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_start_day_too_low_rejected(self):
        res = self.client.post(self.url, {
            'category': str(self.expense_cat.id),
            'amount_limit': '3000.00',
            'start_day': 0,
            'rollover': False,
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_start_day_too_high_rejected(self):
        res = self.client.post(self.url, {
            'category': str(self.expense_cat.id),
            'amount_limit': '3000.00',
            'start_day': 29,
            'rollover': False,
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_unique_constraint_global(self):
        r1 = self.client.post(self.url, {
            'category': str(self.expense_cat.id),
            'amount_limit': '3000.00', 'start_day': 25, 'rollover': False,
        }, format='json')
        self.assertEqual(r1.status_code, 201)
        res = self.client.post(self.url, {
            'category': str(self.expense_cat.id),
            'amount_limit': '2000.00', 'start_day': 1, 'rollover': True,
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_different_users_can_have_same_global_budget(self):
        """Two different users may each create a global budget for the same category."""
        other_user = make_user('other')
        other_client = APIClient()
        other_client.force_authenticate(user=other_user)
        r1 = self.client.post(self.url, {
            'category': str(self.expense_cat.id),
            'amount_limit': '3000.00', 'start_day': 25, 'rollover': False,
        }, format='json')
        self.assertEqual(r1.status_code, 201)
        r2 = other_client.post(self.url, {
            'category': str(self.expense_cat.id),
            'amount_limit': '2000.00', 'start_day': 1, 'rollover': False,
        }, format='json')
        self.assertEqual(r2.status_code, 201)

    def test_unique_constraint_per_account(self):
        self.client.post(self.url, {
            'category': str(self.expense_cat.id),
            'account': str(self.account.id),
            'amount_limit': '3000.00', 'start_day': 25, 'rollover': False,
        }, format='json')
        res = self.client.post(self.url, {
            'category': str(self.expense_cat.id),
            'account': str(self.account.id),
            'amount_limit': '2000.00', 'start_day': 1, 'rollover': True,
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_global_and_scoped_coexist(self):
        r1 = self.client.post(self.url, {
            'category': str(self.expense_cat.id),
            'amount_limit': '3000.00', 'start_day': 25, 'rollover': False,
        }, format='json')
        self.assertEqual(r1.status_code, 201)
        r2 = self.client.post(self.url, {
            'category': str(self.expense_cat.id),
            'account': str(self.account.id),
            'amount_limit': '1500.00', 'start_day': 25, 'rollover': False,
        }, format='json')
        self.assertEqual(r2.status_code, 201)


class BudgetCRUDTest(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.account = Account.objects.create(name='CIH Bank', user=self.user)
        self.category = Category.objects.create(
            name='Food', color='#ff0000', type='expense'
        )
        self.url = '/api/budgets/'

    def _create_budget(self, **kwargs):
        defaults = {
            'category': str(self.category.id),
            'amount_limit': '3000.00',
            'start_day': 25,
            'rollover': False,
        }
        defaults.update(kwargs)
        return self.client.post(self.url, defaults, format='json')

    def test_create_budget(self):
        res = self._create_budget()
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn('id', data)
        self.assertIn('period', data)
        self.assertIn('spent', data)
        self.assertIn('remaining', data)
        self.assertIn('utilization_pct', data)
        self.assertIsInstance(data['category'], dict)
        self.assertEqual(data['category']['name'], 'Food')
        self.assertIsNone(data['account'])

    def test_create_budget_assigns_current_user(self):
        res = self._create_budget()
        self.assertEqual(res.status_code, 201)
        budget = Budget.objects.get(id=res.json()['id'])
        self.assertEqual(budget.user, self.user)

    def test_create_budget_scoped_to_account(self):
        res = self._create_budget(account=str(self.account.id))
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['account']['name'], 'CIH Bank')

    def test_cannot_use_other_users_account(self):
        other_user = make_user('other')
        other_account = Account.objects.create(name='Other Bank', user=other_user)
        res = self._create_budget(account=str(other_account.id))
        self.assertEqual(res.status_code, 400)

    def test_list_budgets(self):
        self._create_budget()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()['results']), 1)

    def test_user_only_sees_own_budgets(self):
        other_user = make_user('other')
        other_account = Account.objects.create(name='Other Bank', user=other_user)
        other_cat = Category.objects.create(name='Other', color='#000', type='expense')
        Budget.objects.create(
            category=other_cat, amount_limit='100', start_day=1,
            rollover=False, user=other_user,
        )
        self._create_budget()
        res = self.client.get(self.url)
        self.assertEqual(len(res.json()['results']), 1)

    def test_retrieve_budget(self):
        created = self._create_budget().json()
        res = self.client.get(f"{self.url}{created['id']}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['id'], created['id'])

    def test_cannot_retrieve_other_users_budget(self):
        other_user = make_user('other')
        other_cat = Category.objects.create(name='Other', color='#000', type='expense')
        other_budget = Budget.objects.create(
            category=other_cat, amount_limit='100', start_day=1,
            rollover=False, user=other_user,
        )
        res = self.client.get(f"{self.url}{other_budget.id}/")
        self.assertEqual(res.status_code, 404)

    def test_update_budget_put(self):
        created = self._create_budget().json()
        res = self.client.put(f"{self.url}{created['id']}/", {
            'category': str(self.category.id),
            'amount_limit': '4000.00',
            'start_day': 1,
            'rollover': True,
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['amount_limit'], '4000.00')

    def test_update_budget_patch(self):
        created = self._create_budget().json()
        res = self.client.patch(f"{self.url}{created['id']}/", {
            'rollover': True,
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()['rollover'])

    def test_delete_budget(self):
        created = self._create_budget().json()
        res = self.client.delete(f"{self.url}{created['id']}/")
        self.assertEqual(res.status_code, 204)
        self.assertEqual(self.client.get(self.url).json()['count'], 0)

    def test_list_ordering_by_category_name(self):
        cat_z = Category.objects.create(name='Zara', color='#000', type='expense')
        cat_a = Category.objects.create(name='Abonnement', color='#111', type='expense')
        self.client.post(self.url, {
            'category': str(cat_z.id), 'amount_limit': '100', 'start_day': 1, 'rollover': False
        }, format='json')
        self.client.post(self.url, {
            'category': str(cat_a.id), 'amount_limit': '200', 'start_day': 1, 'rollover': False
        }, format='json')
        res = self.client.get(self.url)
        names = [r['category']['name'] for r in res.json()['results']]
        self.assertEqual(names, sorted(names))


class BudgetHistoryTest(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.account = Account.objects.create(name='CIH Bank', user=self.user)
        self.category = Category.objects.create(
            name='Food', color='#ff0000', type='expense'
        )
        self.budget = Budget.objects.create(
            category=self.category,
            amount_limit=Decimal('3000.00'),
            start_day=1,
            rollover=False,
            user=self.user,
        )
        self.url = f'/api/budgets/{self.budget.id}/history/'

    def test_history_default_12_periods(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['periods_requested'], 12)
        self.assertEqual(len(data['history']), 12)

    def test_history_custom_periods(self):
        res = self.client.get(f'{self.url}?periods=3')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()['history']), 3)

    def test_history_periods_too_low(self):
        res = self.client.get(f'{self.url}?periods=0')
        self.assertEqual(res.status_code, 400)

    def test_history_periods_too_high(self):
        res = self.client.get(f'{self.url}?periods=25')
        self.assertEqual(res.status_code, 400)

    def test_history_ascending_order(self):
        res = self.client.get(f'{self.url}?periods=3')
        starts = [p['period']['start'] for p in res.json()['history']]
        self.assertEqual(starts, sorted(starts))

    def test_history_new_budget_all_zero(self):
        res = self.client.get(f'{self.url}?periods=3')
        for record in res.json()['history']:
            self.assertEqual(record['spent'], '0.00')

    def test_history_rollover_carries_surplus(self):
        budget = Budget.objects.create(
            category=self.category,
            account=self.account,
            amount_limit=Decimal('3000.00'),
            start_day=1,
            rollover=True,
            user=self.user,
        )
        periods = last_n_periods(1, 3)
        oldest_start, oldest_end = periods[0]
        Transaction.objects.create(
            label='Groceries', amount=Decimal('-2500.00'),
            date=oldest_start.replace(day=5), type='expense',
            account=self.account, category=self.category,
        )
        res = self.client.get(f'/api/budgets/{budget.id}/history/?periods=3')
        history = res.json()['history']
        oldest = history[0]
        second = history[1]
        self.assertEqual(oldest['spent'], '2500.00')
        self.assertEqual(Decimal(second['effective_limit']), Decimal('3500.00'))

    def test_history_rollover_overspend_no_debt(self):
        budget = Budget.objects.create(
            category=self.category,
            account=self.account,
            amount_limit=Decimal('3000.00'),
            start_day=1,
            rollover=True,
            user=self.user,
        )
        periods = last_n_periods(1, 3)
        oldest_start, _ = periods[0]
        Transaction.objects.create(
            label='Overspend', amount=Decimal('-4000.00'),
            date=oldest_start.replace(day=5), type='expense',
            account=self.account, category=self.category,
        )
        res = self.client.get(f'/api/budgets/{budget.id}/history/?periods=3')
        history = res.json()['history']
        oldest = history[0]
        second = history[1]
        self.assertLess(Decimal(oldest['remaining']), Decimal('0'))
        self.assertEqual(Decimal(second['effective_limit']), Decimal('3000.00'))

    def test_history_no_rollover_fresh_each_period(self):
        res = self.client.get(f'{self.url}?periods=3')
        for record in res.json()['history']:
            self.assertEqual(
                Decimal(record['effective_limit']),
                self.budget.amount_limit
            )

    def test_history_response_has_required_fields(self):
        res = self.client.get(self.url)
        record = res.json()['history'][0]
        self.assertIn('period', record)
        self.assertIn('effective_limit', record)
        self.assertIn('spent', record)
        self.assertIn('remaining', record)
        self.assertIn('start', record['period'])
        self.assertIn('end', record['period'])


class BudgetAdminTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin', password='password', email='admin@test.com'
        )
        self.client.force_login(self.superuser)

    def _make_budget(self, with_account=False):
        from budgets.models import Budget
        from categories.models import Category
        from accounts.models import Account
        from decimal import Decimal
        cat = Category.objects.create(name="Alimentation", color="#FF5733", type="expense")
        account = Account.objects.create(name="CIH", user=self.superuser) if with_account else None
        return Budget.objects.create(
            category=cat,
            account=account,
            amount_limit=Decimal("500.00"),
            start_day=1,
            rollover=False,
            user=self.superuser,
        )

    def test_budget_list_page_loads(self):
        self._make_budget()
        response = self.client.get('/admin/budgets/budget/')
        self.assertEqual(response.status_code, 200)

    def test_account_display_shows_global_when_no_account(self):
        from budgets.admin import BudgetAdmin
        from budgets.models import Budget
        budget = self._make_budget(with_account=False)
        ma = BudgetAdmin(model=Budget, admin_site=AdminSite())
        self.assertEqual(ma.account_display(budget), 'global')

    def test_account_display_shows_account_name(self):
        from budgets.admin import BudgetAdmin
        from budgets.models import Budget
        budget = self._make_budget(with_account=True)
        ma = BudgetAdmin(model=Budget, admin_site=AdminSite())
        self.assertEqual(ma.account_display(budget), 'CIH')
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
python manage.py test budgets
```

Expected: Multiple failures.

- [ ] **Step 3: Update `budgets/views.py`**

```python
from decimal import Decimal
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from core.mixins import UserOwnedMixin
from budgets.models import Budget
from budgets.serializers import BudgetSerializer
from budgets.utils import last_n_periods, compute_spent


class BudgetViewSet(UserOwnedMixin, ModelViewSet):
    serializer_class = BudgetSerializer

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user).select_related('category', 'account')

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        budget = self.get_object()

        try:
            n = int(request.query_params.get('periods', 12))
        except ValueError:
            return Response(
                {'error': 'periods must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (1 <= n <= 24):
            return Response(
                {'error': 'periods must be between 1 and 24.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        periods = last_n_periods(budget.start_day, n)
        effective_limit = budget.amount_limit
        records = []

        for period_start, period_end in periods:
            spent = compute_spent(budget, period_start, period_end)
            remaining = effective_limit - spent
            surplus_carried = max(remaining, Decimal('0'))
            records.append({
                'period': {
                    'start': period_start.isoformat(),
                    'end': period_end.isoformat(),
                },
                'effective_limit': f'{effective_limit:.2f}',
                'spent': f'{spent:.2f}',
                'remaining': f'{remaining:.2f}',
            })
            effective_limit = (
                budget.amount_limit + surplus_carried
                if budget.rollover
                else budget.amount_limit
            )

        return Response({
            'budget_id': str(budget.id),
            'periods_requested': n,
            'history': records,
        })
```

- [ ] **Step 4: Update `budgets/serializers.py`**

Two changes: scope `account` queryset to the current user; scope the duplicate-check in `validate` to the current user.

```python
from rest_framework import serializers
from accounts.models import Account
from categories.models import Category
from budgets.models import Budget
from budgets.utils import current_period, compute_spent


class BudgetSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(type='expense')
    )
    account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.none(),  # overridden in get_fields
        required=False,
        allow_null=True,
        default=None,
    )

    period = serializers.SerializerMethodField()
    spent = serializers.SerializerMethodField()
    remaining = serializers.SerializerMethodField()
    utilization_pct = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            'id', 'category', 'account',
            'amount_limit', 'start_day', 'rollover',
            'period', 'spent', 'remaining', 'utilization_pct',
        ]
        read_only_fields = ['id', 'period', 'spent', 'remaining', 'utilization_pct']

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            fields['account'].queryset = Account.objects.filter(user=request.user)
        return fields

    def validate_category(self, value):
        if value.type != 'expense':
            raise serializers.ValidationError(
                'Only expense categories can have a budget.'
            )
        return value

    def validate_start_day(self, value):
        if not (1 <= value <= 28):
            raise serializers.ValidationError(
                'start_day must be between 1 and 28.'
            )
        return value

    def validate(self, data):
        category = data.get('category', getattr(self.instance, 'category', None))
        account = data.get('account', getattr(self.instance, 'account', None))
        instance_id = self.instance.id if self.instance else None
        user = self.context['request'].user

        if account is None:
            qs = Budget.objects.filter(user=user, category=category, account__isnull=True)
        else:
            qs = Budget.objects.filter(user=user, category=category, account=account)
        if instance_id:
            qs = qs.exclude(id=instance_id)
        if qs.exists():
            scope = 'account-scoped' if account else 'global'
            raise serializers.ValidationError(
                f'A {scope} budget for this category already exists.'
            )
        return data

    def _get_metrics(self, obj):
        cache_key = '_budget_serializer_metrics'
        if not hasattr(obj, cache_key):
            start, end = current_period(obj.start_day)
            spent = compute_spent(obj, start, end)
            setattr(obj, cache_key, {'start': start, 'end': end, 'spent': spent})
        return getattr(obj, cache_key)

    def get_period(self, obj):
        m = self._get_metrics(obj)
        return {'start': m['start'].isoformat(), 'end': m['end'].isoformat()}

    def get_spent(self, obj):
        m = self._get_metrics(obj)
        return str(m['spent'])

    def get_remaining(self, obj):
        m = self._get_metrics(obj)
        return str(obj.amount_limit - m['spent'])

    def get_utilization_pct(self, obj):
        if obj.amount_limit <= 0:
            return 0.0
        m = self._get_metrics(obj)
        return round(float(m['spent'] / obj.amount_limit) * 100, 1)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['category'] = {
            'id': str(instance.category.id),
            'name': instance.category.name,
            'color': instance.category.color,
            'type': instance.category.type,
        }
        if instance.account:
            data['account'] = {
                'id': str(instance.account.id),
                'name': instance.account.name,
            }
        else:
            data['account'] = None
        return data
```

- [ ] **Step 5: Run the tests**

```bash
python manage.py test budgets
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add budgets/views.py budgets/serializers.py budgets/tests.py
git commit -m "feat: scope BudgetViewSet to authenticated user, scope account queryset in serializer"
```

---

## Task 8: Scope `TransactionViewSet` + update transaction tests

**Files:**
- Modify: `transactions/views.py`
- Modify: `transactions/tests.py`

- [ ] **Step 1: Update `transactions/tests.py`**

Update helpers to include `user`, add auth to API tests, and add isolation tests:

```python
import uuid
from decimal import Decimal
from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status


def make_user(username='testuser'):
    return User.objects.create_user(username=username, password='testpass123')


def make_account(user, name="CIH"):
    from accounts.models import Account
    return Account.objects.create(name=name, user=user)


def make_category(name="Logement", type="expense"):
    from categories.models import Category
    return Category.objects.create(name=name, color="#FF5733", type=type)


class TransactionModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.account = make_account(self.user)
        self.category = make_category()

    def test_transaction_has_uuid_pk(self):
        from transactions.models import Transaction
        t = Transaction.objects.create(
            label="Loyer", amount=Decimal("-1500.00"),
            date="2024-01-01", type="expense",
            account=self.account, category=self.category
        )
        self.assertIsInstance(t.id, uuid.UUID)

    def test_transaction_str(self):
        from transactions.models import Transaction
        t = Transaction.objects.create(
            label="Loyer", amount=Decimal("-1500.00"),
            date="2024-01-01", type="expense",
            account=self.account, category=self.category
        )
        self.assertIn("Loyer", str(t))

    def test_transaction_timestamps(self):
        from transactions.models import Transaction
        t = Transaction.objects.create(
            label="Test", amount=Decimal("-100.00"),
            date="2024-01-01", type="expense",
            account=self.account, category=self.category
        )
        self.assertIsNotNone(t.created_at)
        self.assertIsNotNone(t.updated_at)

    def test_transaction_ordering_by_date_desc(self):
        from transactions.models import Transaction
        Transaction.objects.create(
            label="Old", amount=Decimal("-100.00"), date="2024-01-01",
            type="expense", account=self.account, category=self.category
        )
        Transaction.objects.create(
            label="New", amount=Decimal("-200.00"), date="2024-02-01",
            type="expense", account=self.account, category=self.category
        )
        first = Transaction.objects.first()
        self.assertEqual(first.label, "New")


class TransactionAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.url = '/api/transactions/'
        self.account = make_account(self.user)
        self.category = make_category()

    def _transaction_payload(self, **overrides):
        data = {
            'label': 'Loyer',
            'amount': '-1500.00',
            'date': '2024-01-15',
            'type': 'expense',
            'account': str(self.account.pk),
            'category': str(self.category.pk),
        }
        data.update(overrides)
        return data

    def _create_transaction(self, **kwargs):
        from transactions.models import Transaction
        defaults = dict(
            label="Test", amount=Decimal("-100.00"), date="2024-01-15",
            type="expense", account=self.account, category=self.category
        )
        defaults.update(kwargs)
        return Transaction.objects.create(**defaults)

    def test_unauthenticated_request_returns_401(self):
        unauth_client = APIClient()
        response = unauth_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_transactions(self):
        self._create_transaction(label="T1")
        self._create_transaction(label="T2")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_user_only_sees_own_transactions(self):
        other_user = make_user('other')
        other_account = make_account(other_user, "Other Bank")
        from transactions.models import Transaction
        Transaction.objects.create(
            label="My T", amount=Decimal("-100"), date="2024-01-15",
            type="expense", account=self.account, category=self.category
        )
        Transaction.objects.create(
            label="Other T", amount=Decimal("-200"), date="2024-01-15",
            type="expense", account=other_account, category=self.category
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['label'], 'My T')

    def test_create_transaction(self):
        response = self.client.post(self.url, self._transaction_payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['label'], 'Loyer')
        self.assertIn('category_detail', response.data)
        self.assertIn('account_name', response.data)

    def test_create_transaction_validates_type_amount_consistency(self):
        payload = self._transaction_payload(type='expense', amount='1500.00')
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        payload2 = self._transaction_payload(type='income', amount='-500.00')
        response2 = self.client.post(self.url, payload2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_transaction_requires_fields(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_transaction(self):
        t = self._create_transaction()
        response = self.client.put(
            f'/api/transactions/{t.pk}/',
            self._transaction_payload(label='Updated'),
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        t.refresh_from_db()
        self.assertEqual(t.label, 'Updated')

    def test_cannot_update_other_users_transaction(self):
        other_user = make_user('other')
        other_account = make_account(other_user, "Other Bank")
        from transactions.models import Transaction
        other_t = Transaction.objects.create(
            label="Other", amount=Decimal("-100"), date="2024-01-15",
            type="expense", account=other_account, category=self.category
        )
        response = self.client.put(
            f'/api/transactions/{other_t.pk}/',
            self._transaction_payload(label='Hacked'),
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_transaction(self):
        t = self._create_transaction()
        response = self.client.delete(f'/api/transactions/{t.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_filter_by_type(self):
        self._create_transaction(label="Income T", amount=Decimal("5000"), type="income")
        self._create_transaction(label="Expense T", amount=Decimal("-500"), type="expense")
        response = self.client.get(self.url, {'type': 'income'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['label'], 'Income T')

    def test_filter_by_date_range(self):
        self._create_transaction(label="Jan", date="2024-01-15")
        self._create_transaction(label="Mar", date="2024-03-15")
        response = self.client.get(self.url, {'start_date': '2024-03-01', 'end_date': '2024-03-31'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_search_by_label(self):
        self._create_transaction(label="Loyer janvier")
        self._create_transaction(label="Salaire")
        response = self.client.get(self.url, {'search': 'Loyer'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_ordering_by_amount(self):
        self._create_transaction(label="Small", amount=Decimal("-100"))
        self._create_transaction(label="Big", amount=Decimal("-1000"))
        response = self.client.get(self.url, {'ordering': 'amount'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['label'], 'Big')


class TransactionAdminTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin', password='password', email='admin@test.com'
        )
        self.client.force_login(self.superuser)

    def _make_transaction(self):
        from accounts.models import Account
        from categories.models import Category
        from transactions.models import Transaction
        account = Account.objects.create(name="CIH", user=self.superuser)
        cat = Category.objects.create(name="Salaire", color="#00FF00", type="income")
        return Transaction.objects.create(
            label="Salary", amount=Decimal("5000.00"),
            date="2024-01-15", type="income", account=account, category=cat
        )

    def test_transaction_list_page_loads(self):
        self._make_transaction()
        response = self.client.get('/admin/transactions/transaction/')
        self.assertEqual(response.status_code, 200)

    def test_transaction_change_page_loads(self):
        tx = self._make_transaction()
        response = self.client.get(f'/admin/transactions/transaction/{tx.pk}/change/')
        self.assertEqual(response.status_code, 200)

    def test_list_filter_includes_type_and_fk_filters(self):
        from transactions.admin import TransactionAdmin
        from transactions.models import Transaction
        ma = TransactionAdmin(model=Transaction, admin_site=AdminSite())
        filter_fields = [
            f if isinstance(f, str) else f[0]
            for f in ma.list_filter
        ]
        self.assertIn('type', filter_fields)
        self.assertIn('category', filter_fields)
        self.assertIn('account', filter_fields)

    def test_date_hierarchy_set(self):
        from transactions.admin import TransactionAdmin
        from transactions.models import Transaction
        ma = TransactionAdmin(model=Transaction, admin_site=AdminSite())
        self.assertEqual(ma.date_hierarchy, 'date')
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
python manage.py test transactions
```

Expected: Multiple failures — model helpers missing user arg, API tests without auth getting 401.

- [ ] **Step 3: Update `transactions/views.py`**

```python
import django_filters
from rest_framework.viewsets import ModelViewSet
from transactions.models import Transaction
from transactions.serializers import TransactionSerializer


class TransactionFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    category = django_filters.UUIDFilter(field_name='category__id')
    account = django_filters.UUIDFilter(field_name='account__id')
    type = django_filters.ChoiceFilter(choices=Transaction.TYPE_CHOICES)

    class Meta:
        model = Transaction
        fields = ['start_date', 'end_date', 'category', 'account', 'type']


class TransactionViewSet(ModelViewSet):
    serializer_class = TransactionSerializer
    filterset_class = TransactionFilter
    search_fields = ['label']
    ordering_fields = ['date', 'amount']
    ordering = ['-date']

    def get_queryset(self):
        return (
            Transaction.objects
            .filter(account__user=self.request.user)
            .select_related('account', 'category')
        )
```

- [ ] **Step 4: Run the tests**

```bash
python manage.py test transactions
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add transactions/views.py transactions/tests.py
git commit -m "feat: scope TransactionViewSet to authenticated user via account__user"
```

---

## Task 9: Scope analytics views + update analytics tests

**Files:**
- Modify: `analytics/views.py`
- Modify: `analytics/tests.py`

- [ ] **Step 1: Update `analytics/tests.py`**

```python
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status


def make_user(username='testuser'):
    return User.objects.create_user(username=username, password='testpass123')


def make_account(user, name='CIH'):
    from accounts.models import Account
    return Account.objects.create(name=name, user=user)


def make_category(name="Logement", type="expense"):
    from categories.models import Category
    return Category.objects.create(name=name, color="#FF5733", type=type)


def make_transaction(account, category, **kwargs):
    from transactions.models import Transaction
    defaults = dict(
        label="Test", amount=Decimal("-100"), date="2024-01-15",
        type="expense", account=account, category=category
    )
    defaults.update(kwargs)
    return Transaction.objects.create(**defaults)


class MonthlyFlowAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.account = make_account(self.user)
        self.income_cat = make_category("Salaire", "income")
        self.expense_cat = make_category("Logement", "expense")

    def test_unauthenticated_request_returns_401(self):
        unauth_client = APIClient()
        response = unauth_client.get('/api/analytics/monthly-flow/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_monthly_flow_returns_list(self):
        make_transaction(self.account, self.income_cat,
                         label="Salary", amount=Decimal("5000"), date="2024-01-10", type="income")
        make_transaction(self.account, self.expense_cat,
                         label="Loyer", amount=Decimal("-1500"), date="2024-01-20", type="expense")
        response = self.client.get('/api/analytics/monthly-flow/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertIn('month', item)
        self.assertIn('income', item)
        self.assertIn('expenses', item)

    def test_monthly_flow_correct_sums(self):
        make_transaction(self.account, self.income_cat,
                         label="Salary", amount=Decimal("5000"), date="2024-01-10", type="income")
        make_transaction(self.account, self.income_cat,
                         label="Bonus", amount=Decimal("1000"), date="2024-01-15", type="income")
        make_transaction(self.account, self.expense_cat,
                         label="Loyer", amount=Decimal("-1500"), date="2024-01-20", type="expense")
        response = self.client.get('/api/analytics/monthly-flow/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data[0]
        self.assertEqual(Decimal(str(item['income'])), Decimal("6000"))
        self.assertEqual(Decimal(str(item['expenses'])), Decimal("1500"))

    def test_monthly_flow_multiple_months(self):
        make_transaction(self.account, self.income_cat,
                         label="Jan Salary", amount=Decimal("5000"), date="2024-01-10", type="income")
        make_transaction(self.account, self.income_cat,
                         label="Feb Salary", amount=Decimal("5000"), date="2024-02-10", type="income")
        response = self.client.get('/api/analytics/monthly-flow/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_monthly_flow_excludes_other_users_data(self):
        other_user = make_user('other')
        other_account = make_account(other_user, 'Other Bank')
        make_transaction(self.account, self.income_cat,
                         label="My Salary", amount=Decimal("5000"), date="2024-01-10", type="income")
        make_transaction(other_account, self.income_cat,
                         label="Other Salary", amount=Decimal("9999"), date="2024-01-10", type="income")
        response = self.client.get('/api/analytics/monthly-flow/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(Decimal(str(response.data[0]['income'])), Decimal("5000"))


class CategorySplitAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.account = make_account(self.user)
        self.logement = make_category("Logement", "expense")
        self.alimentation = make_category("Alimentation", "expense")
        self.salaire = make_category("Salaire", "income")

    def test_unauthenticated_request_returns_401(self):
        unauth_client = APIClient()
        response = unauth_client.get('/api/analytics/category-split/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_category_split_returns_list(self):
        make_transaction(self.account, self.logement, amount=Decimal("-1500"), type="expense")
        make_transaction(self.account, self.alimentation, amount=Decimal("-500"), type="expense")
        response = self.client.get('/api/analytics/category-split/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_category_split_fields(self):
        make_transaction(self.account, self.logement, amount=Decimal("-1500"), type="expense")
        response = self.client.get('/api/analytics/category-split/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data[0]
        self.assertIn('name', item)
        self.assertIn('value', item)
        self.assertIn('color', item)

    def test_category_split_excludes_income(self):
        make_transaction(self.account, self.logement, amount=Decimal("-1500"), type="expense")
        make_transaction(self.account, self.salaire, amount=Decimal("5000"), type="income")
        response = self.client.get('/api/analytics/category-split/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item['name'] for item in response.data]
        self.assertIn('Logement', names)
        self.assertNotIn('Salaire', names)

    def test_category_split_correct_values(self):
        make_transaction(self.account, self.logement, amount=Decimal("-1500"), type="expense")
        make_transaction(self.account, self.logement, amount=Decimal("-500"), type="expense")
        make_transaction(self.account, self.alimentation, amount=Decimal("-300"), type="expense")
        response = self.client.get('/api/analytics/category-split/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        by_name = {item['name']: item for item in response.data}
        self.assertEqual(Decimal(str(by_name['Logement']['value'])), Decimal("2000"))
        self.assertEqual(Decimal(str(by_name['Alimentation']['value'])), Decimal("300"))

    def test_category_split_excludes_other_users_data(self):
        other_user = make_user('other')
        other_account = make_account(other_user, 'Other Bank')
        make_transaction(self.account, self.logement, amount=Decimal("-1500"), type="expense")
        make_transaction(other_account, self.logement, amount=Decimal("-9999"), type="expense")
        response = self.client.get('/api/analytics/category-split/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        by_name = {item['name']: item for item in response.data}
        self.assertEqual(Decimal(str(by_name['Logement']['value'])), Decimal("1500"))
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
python manage.py test analytics
```

Expected: Multiple failures — no auth on setUp, and analytics queries return all users' data.

- [ ] **Step 3: Update `analytics/views.py`**

```python
from decimal import Decimal
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce, TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from transactions.models import Transaction


class MonthlyFlowView(APIView):
    def get(self, request):
        qs = (
            Transaction.objects
            .filter(account__user=request.user)
            .annotate(month=TruncMonth('date'))
            .values('month', 'type')
            .annotate(total=Coalesce(Sum('amount'), Value(0), output_field=DecimalField()))
            .order_by('month')
        )

        flow_by_month = {}
        for row in qs:
            month_str = row['month'].strftime('%Y-%m')
            if month_str not in flow_by_month:
                flow_by_month[month_str] = {'month': month_str, 'income': Decimal('0'), 'expenses': Decimal('0')}
            if row['type'] == 'income':
                flow_by_month[month_str]['income'] += row['total']
            else:
                flow_by_month[month_str]['expenses'] += abs(row['total'])

        result = sorted(flow_by_month.values(), key=lambda x: x['month'])
        return Response(result)


class CategorySplitView(APIView):
    def get(self, request):
        qs = (
            Transaction.objects
            .filter(account__user=request.user, type='expense')
            .values('category__name', 'category__color')
            .annotate(total=Coalesce(Sum('amount'), Value(0), output_field=DecimalField()))
            .order_by('category__name')
        )

        result = [
            {
                'name': row['category__name'],
                'value': abs(row['total']),
                'color': row['category__color'],
            }
            for row in qs
            if row['category__name'] is not None
        ]
        return Response(result)
```

- [ ] **Step 4: Run the tests**

```bash
python manage.py test analytics
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add analytics/views.py analytics/tests.py
git commit -m "feat: scope analytics views to authenticated user"
```

---

## Task 10: Update `seed_data` command to require `--user`

**Files:**
- Modify: `transactions/management/commands/seed_data.py`

- [ ] **Step 1: Update `seed_data.py`**

```python
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction
from accounts.models import Account
from categories.models import Category
from goals.models import Goal
from transactions.models import Transaction


ACCOUNTS = [
    {"name": "CIH Principale"},
    {"name": "Wafacash"},
    {"name": "Attijari Épargne"},
    {"name": "Cash"},
]

CATEGORIES = [
    {"name": "Salaire", "color": "#22c55e", "type": "income"},
    {"name": "Freelance", "color": "#10b981", "type": "income"},
    {"name": "Remboursement", "color": "#6ee7b7", "type": "income"},
    {"name": "Logement", "color": "#ef4444", "type": "expense"},
    {"name": "Alimentation", "color": "#f97316", "type": "expense"},
    {"name": "Transport", "color": "#eab308", "type": "expense"},
    {"name": "Santé", "color": "#3b82f6", "type": "expense"},
    {"name": "Loisirs", "color": "#8b5cf6", "type": "expense"},
    {"name": "Abonnements", "color": "#ec4899", "type": "expense"},
    {"name": "Éducation", "color": "#06b6d4", "type": "expense"},
]

GOALS = [
    {"label": "Fonds d'urgence", "current": Decimal("3500"), "target": Decimal("10000"), "icon": "shield", "color": "#ef4444"},
    {"label": "Vacances Été 2025", "current": Decimal("1200"), "target": Decimal("5000"), "icon": "plane", "color": "#3b82f6"},
    {"label": "Nouvelle voiture", "current": Decimal("8000"), "target": Decimal("80000"), "icon": "car", "color": "#22c55e"},
    {"label": "Formation en ligne", "current": Decimal("200"), "target": Decimal("2000"), "icon": "book", "color": "#8b5cf6"},
]

TRANSACTIONS_TEMPLATE = [
    # January 2024
    {"label": "Salaire Janvier", "amount": Decimal("8500"), "date": "2024-01-05", "type": "income", "account": "CIH Principale", "category": "Salaire"},
    {"label": "Loyer Janvier", "amount": Decimal("-3200"), "date": "2024-01-07", "type": "expense", "account": "CIH Principale", "category": "Logement"},
    {"label": "Courses Carrefour", "amount": Decimal("-650"), "date": "2024-01-10", "type": "expense", "account": "Cash", "category": "Alimentation"},
    {"label": "Abonnement Maroc Telecom", "amount": Decimal("-120"), "date": "2024-01-12", "type": "expense", "account": "CIH Principale", "category": "Abonnements"},
    {"label": "Transport taxi", "amount": Decimal("-80"), "date": "2024-01-15", "type": "expense", "account": "Cash", "category": "Transport"},
    {"label": "Mission freelance", "amount": Decimal("2000"), "date": "2024-01-20", "type": "income", "account": "Wafacash", "category": "Freelance"},
    {"label": "Pharmacie", "amount": Decimal("-220"), "date": "2024-01-22", "type": "expense", "account": "Cash", "category": "Santé"},
    {"label": "Netflix + Spotify", "amount": Decimal("-95"), "date": "2024-01-25", "type": "expense", "account": "CIH Principale", "category": "Abonnements"},
    # February 2024
    {"label": "Salaire Février", "amount": Decimal("8500"), "date": "2024-02-05", "type": "income", "account": "CIH Principale", "category": "Salaire"},
    {"label": "Loyer Février", "amount": Decimal("-3200"), "date": "2024-02-07", "type": "expense", "account": "CIH Principale", "category": "Logement"},
    {"label": "Restaurant La Maison", "amount": Decimal("-350"), "date": "2024-02-14", "type": "expense", "account": "CIH Principale", "category": "Loisirs"},
    {"label": "Courses Marjane", "amount": Decimal("-580"), "date": "2024-02-16", "type": "expense", "account": "Cash", "category": "Alimentation"},
    {"label": "Bus CTM", "amount": Decimal("-150"), "date": "2024-02-18", "type": "expense", "account": "Cash", "category": "Transport"},
    {"label": "Cours en ligne Udemy", "amount": Decimal("-200"), "date": "2024-02-20", "type": "expense", "account": "CIH Principale", "category": "Éducation"},
    {"label": "Remboursement ami", "amount": Decimal("500"), "date": "2024-02-22", "type": "income", "account": "Wafacash", "category": "Remboursement"},
    # March 2024
    {"label": "Salaire Mars", "amount": Decimal("8500"), "date": "2024-03-05", "type": "income", "account": "CIH Principale", "category": "Salaire"},
    {"label": "Loyer Mars", "amount": Decimal("-3200"), "date": "2024-03-07", "type": "expense", "account": "CIH Principale", "category": "Logement"},
    {"label": "Courses Atacadão", "amount": Decimal("-720"), "date": "2024-03-10", "type": "expense", "account": "Cash", "category": "Alimentation"},
    {"label": "Plein d'essence", "amount": Decimal("-400"), "date": "2024-03-12", "type": "expense", "account": "CIH Principale", "category": "Transport"},
    {"label": "Mission freelance", "amount": Decimal("3500"), "date": "2024-03-15", "type": "income", "account": "Wafacash", "category": "Freelance"},
    {"label": "Cinema Mégarama", "amount": Decimal("-120"), "date": "2024-03-17", "type": "expense", "account": "Cash", "category": "Loisirs"},
    {"label": "Médecin généraliste", "amount": Decimal("-300"), "date": "2024-03-20", "type": "expense", "account": "CIH Principale", "category": "Santé"},
    {"label": "Abonnement Inwi", "amount": Decimal("-99"), "date": "2024-03-25", "type": "expense", "account": "CIH Principale", "category": "Abonnements"},
]


class Command(BaseCommand):
    help = 'Seed the database with initial finance data for a specific user (idempotent — clears first)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            required=True,
            help='Username of the user to seed data for (must already exist)',
        )

    @db_transaction.atomic
    def handle(self, *args, **options):
        username = options['user']
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist. Create it first with createsuperuser.")

        self.stdout.write(f'Seeding data for user: {username}')
        self.stdout.write('Clearing existing data...')
        Transaction.objects.filter(account__user=user).delete()
        Goal.objects.filter(user=user).delete()
        Account.objects.filter(user=user).delete()
        Category.objects.all().delete()

        self.stdout.write('Creating accounts...')
        accounts = {
            a['name']: Account.objects.create(name=a['name'], user=user)
            for a in ACCOUNTS
        }

        self.stdout.write('Creating categories...')
        categories = {c['name']: Category.objects.create(**c) for c in CATEGORIES}

        self.stdout.write('Creating goals...')
        for g in GOALS:
            Goal.objects.create(**g, user=user)

        self.stdout.write('Creating transactions...')
        for t in TRANSACTIONS_TEMPLATE:
            Transaction.objects.create(
                label=t['label'],
                amount=t['amount'],
                date=t['date'],
                type=t['type'],
                account=accounts[t['account']],
                category=categories[t['category']],
            )

        self.stdout.write(self.style.SUCCESS(
            f'\nSeed complete for {username}:\n'
            f'  {Account.objects.filter(user=user).count()} accounts\n'
            f'  {Category.objects.count()} categories\n'
            f'  {Goal.objects.filter(user=user).count()} goals\n'
            f'  {Transaction.objects.filter(account__user=user).count()} transactions'
        ))
```

- [ ] **Step 2: Run all tests**

```bash
python manage.py test
```

Expected: All tests pass.

- [ ] **Step 3: Verify the seed command works**

```bash
python manage.py createsuperuser --username admin --email admin@example.com
python manage.py seed_data --user admin
```

Expected output:
```
Seeding data for user: admin
Clearing existing data...
Creating accounts...
Creating categories...
Creating goals...
Creating transactions...

Seed complete for admin:
  4 accounts
  10 categories
  4 goals
  23 transactions
```

- [ ] **Step 4: Verify `--user` is required**

```bash
python manage.py seed_data
```

Expected: `Error: the following arguments are required: --user`

- [ ] **Step 5: Commit**

```bash
git add transactions/management/commands/seed_data.py
git commit -m "feat: require --user argument in seed_data command"
```

---

## Self-Review Notes

**Spec coverage:**
- ✅ `user` FK on Account, Goal, Budget
- ✅ Transaction scoped via `account__user`
- ✅ Category unchanged (global)
- ✅ `UserOwnedMixin` in `core/mixins.py`
- ✅ `AccountViewSet`, `GoalViewSet`, `BudgetViewSet` use mixin
- ✅ `BudgetSerializer` scopes `account` queryset to current user
- ✅ `BudgetSerializer.validate` scoped to current user
- ✅ Analytics views filter by `account__user`
- ✅ Migrations with RunPython clean-slate
- ✅ Budget unique constraints updated (`user` added)
- ✅ `seed_data` requires `--user`
- ✅ All tests updated with auth + user FK

**Placeholder scan:** None found.

**Type consistency:** `user` FK uses `settings.AUTH_USER_MODEL` in models, `self.request.user` in views/serializers — consistent throughout.
