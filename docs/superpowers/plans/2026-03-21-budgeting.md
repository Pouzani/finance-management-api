# Budgeting Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `budgets` Django app to the finance management API that supports monthly envelope budgeting with custom period start day, optional rollover, and optional account scope.

**Architecture:** A single `Budget` model stores the envelope definition. Spending is computed dynamically from `Transaction` records using ORM aggregation (no stored state), following the same pattern as `Account.balance`. A `utils.py` module contains pure period/spending functions that are unit-testable in isolation.

**Tech Stack:** Django 6.0.3, Django REST Framework 3.17, python-dateutil (new dependency for `relativedelta`)

---

## File Map

| File | Status | Responsibility |
|------|--------|----------------|
| `requirements.txt` | Modify | Add `python-dateutil` |
| `budgets/__init__.py` | Create | App package marker |
| `budgets/apps.py` | Create | App config (`BudgetsConfig`) |
| `budgets/models.py` | Create | `Budget` model with conditional UniqueConstraints |
| `budgets/utils.py` | Create | `current_period()`, `last_n_periods()`, `compute_spent()` |
| `budgets/serializers.py` | Create | `BudgetSerializer` with SerializerMethodField + to_representation |
| `budgets/views.py` | Create | `BudgetViewSet` with `history` @action |
| `budgets/urls.py` | Create | DRF router registration |
| `budgets/admin.py` | Create | Basic admin registration |
| `budgets/tests.py` | Create | All unit + integration tests |
| `budgets/migrations/0001_initial.py` | Generate | Auto-generated via makemigrations |
| `finance_management_api/settings.py` | Modify | Add `'budgets'` to INSTALLED_APPS |
| `finance_management_api/urls.py` | Modify | Add `path('api/', include('budgets.urls'))` |

---

## Task 1: Install dependency and scaffold the app

**Files:**
- Modify: `requirements.txt`
- Create: `budgets/__init__.py`, `budgets/apps.py`, `budgets/admin.py`
- Modify: `finance_management_api/settings.py`

- [ ] **Step 1: Install python-dateutil**

```bash
pip install python-dateutil==2.9.0
```

Expected output: `Successfully installed python-dateutil-2.9.0`

- [ ] **Step 2: Add to requirements.txt**

Add this line to `requirements.txt`:
```
python-dateutil==2.9.0
```

- [ ] **Step 3: Create the app package files**

Create `budgets/__init__.py` (empty file).

Create `budgets/apps.py`:
```python
from django.apps import AppConfig


class BudgetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'budgets'
```

Create `budgets/admin.py`:
```python
from django.contrib import admin
from budgets.models import Budget

admin.site.register(Budget)
```

- [ ] **Step 4: Register app in settings**

In `finance_management_api/settings.py`, add `'budgets'` to `INSTALLED_APPS` after `'analytics'`:
```python
INSTALLED_APPS = [
    ...
    'analytics',
    'budgets',
]
```

- [ ] **Step 5: Verify Django recognizes the app**

```bash
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

---

## Task 2: Budget model and migration

**Files:**
- Create: `budgets/models.py`
- Generate: `budgets/migrations/0001_initial.py`

- [ ] **Step 1: Write the failing test for model creation**

Create `budgets/tests.py` with:
```python
import uuid
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from accounts.models import Account
from categories.models import Category
from budgets.models import Budget


class BudgetModelTest(TestCase):
    def setUp(self):
        self.account = Account.objects.create(name='CIH Bank')
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
        )
        self.assertIsInstance(budget.id, uuid.UUID)
        self.assertEqual(budget.amount_limit, Decimal('3000.00'))
        self.assertIsNone(budget.account)

    def test_budget_str(self):
        budget = Budget.objects.create(
            category=self.category,
            amount_limit=Decimal('3000.00'),
            start_day=25,
            rollover=False,
        )
        self.assertIn('Food', str(budget))
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
python manage.py test budgets.tests.BudgetModelTest -v 2
```

Expected: error about `budgets.models` not existing or no table.

- [ ] **Step 3: Create the Budget model**

Create `budgets/models.py`:
```python
import uuid
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class Budget(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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

    def __str__(self):
        scope = f' [{self.account.name}]' if self.account_id else ' [global]'
        return f'{self.category.name}{scope} — {self.amount_limit} MAD'
```

- [ ] **Step 4: Create and apply migration**

```bash
python manage.py makemigrations budgets && python manage.py migrate
```

Expected: `Created migrations/0001_initial.py` and `Applying budgets.0001_initial... OK`

- [ ] **Step 5: Run tests to confirm they pass**

```bash
python manage.py test budgets.tests.BudgetModelTest -v 2
```

Expected: `OK` (2 tests pass)

- [ ] **Step 6: Commit**

```bash
git add requirements.txt budgets/ finance_management_api/settings.py
git commit -m "feat: add Budget model with conditional unique constraints"
```

---

## Task 3: Utility functions (pure, no Django state)

**Files:**
- Create: `budgets/utils.py`
- Modify: `budgets/tests.py` (add utility tests)

- [ ] **Step 1: Write failing tests for `current_period()`**

Add to `budgets/tests.py`:
```python
from datetime import date
from budgets.utils import current_period, last_n_periods, compute_spent


class CurrentPeriodTest(TestCase):
    def test_period_window_start_day_1(self):
        # start_day=1, today=Mar 10 → period is Mar 1–Mar 31
        start, end = current_period(1, reference_date=date(2026, 3, 10))
        self.assertEqual(start, date(2026, 3, 1))
        self.assertEqual(end, date(2026, 3, 31))

    def test_period_window_mid_month(self):
        # start_day=25, today=Mar 10 → period is Feb 25–Mar 24
        start, end = current_period(25, reference_date=date(2026, 3, 10))
        self.assertEqual(start, date(2026, 2, 25))
        self.assertEqual(end, date(2026, 3, 24))

    def test_period_window_on_start_day(self):
        # today equals start_day → period starts today
        start, end = current_period(25, reference_date=date(2026, 3, 25))
        self.assertEqual(start, date(2026, 3, 25))
        self.assertEqual(end, date(2026, 4, 24))

    def test_period_window_january_edge(self):
        # start_day=25, today=Jan 10 → period is Dec 25–Jan 24
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
```

- [ ] **Step 2: Run to confirm they fail**

```bash
python manage.py test budgets.tests.CurrentPeriodTest budgets.tests.LastNPeriodsTest -v 2
```

Expected: `ImportError` — utils.py doesn't exist yet.

- [ ] **Step 3: Create utils.py**

Create `budgets/utils.py`:
```python
from datetime import date, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.db.models import Sum
from transactions.models import Transaction


def current_period(start_day: int, reference_date: date = None) -> tuple:
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
    n must be >= 1.
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

- [ ] **Step 4: Run period tests to confirm they pass**

```bash
python manage.py test budgets.tests.CurrentPeriodTest budgets.tests.LastNPeriodsTest -v 2
```

Expected: `OK` (7 tests pass)

- [ ] **Step 5: Write failing tests for `compute_spent()`**

Add to `budgets/tests.py`:
```python
from transactions.models import Transaction


class ComputeSpentTest(TestCase):
    def setUp(self):
        self.account_a = Account.objects.create(name='CIH Bank')
        self.account_b = Account.objects.create(name='Cash')
        self.food_cat = Category.objects.create(
            name='Food', color='#ff0000', type='expense'
        )
        self.other_cat = Category.objects.create(
            name='Transport', color='#0000ff', type='expense'
        )
        self.period_start = date(2026, 2, 25)
        self.period_end = date(2026, 3, 24)
        # Expense in period, food, account_a
        Transaction.objects.create(
            label='Groceries', amount=Decimal('-500.00'),
            date=date(2026, 3, 1), type='expense',
            account=self.account_a, category=self.food_cat
        )
        # Expense in period, food, account_b
        Transaction.objects.create(
            label='Market', amount=Decimal('-300.00'),
            date=date(2026, 3, 5), type='expense',
            account=self.account_b, category=self.food_cat
        )
        # Income in period (should be excluded)
        Transaction.objects.create(
            label='Salary', amount=Decimal('8000.00'),
            date=date(2026, 3, 1), type='income',
            account=self.account_a, category=self.food_cat
        )
        # Expense in period, other category (should be excluded)
        Transaction.objects.create(
            label='Bus', amount=Decimal('-50.00'),
            date=date(2026, 3, 2), type='expense',
            account=self.account_a, category=self.other_cat
        )

    def _make_budget(self, account=None):
        from budgets.models import Budget
        return Budget(
            category=self.food_cat,
            account=account,
            amount_limit=Decimal('3000.00'),
            start_day=25,
            rollover=False,
        )

    def test_spent_global(self):
        budget = self._make_budget(account=None)
        spent = compute_spent(budget, self.period_start, self.period_end)
        self.assertEqual(spent, Decimal('800.00'))  # 500 + 300

    def test_spent_scoped_to_account(self):
        budget = self._make_budget(account=self.account_a)
        spent = compute_spent(budget, self.period_start, self.period_end)
        self.assertEqual(spent, Decimal('500.00'))

    def test_spent_excludes_income(self):
        budget = self._make_budget(account=None)
        spent = compute_spent(budget, self.period_start, self.period_end)
        # Income of 8000 must not be included; total must be exactly 800 (500+300)
        self.assertEqual(spent, Decimal('800.00'))

    def test_spent_excludes_other_category(self):
        budget = self._make_budget(account=None)
        spent = compute_spent(budget, self.period_start, self.period_end)
        # Bus (50) for other_cat must not be included
        self.assertEqual(spent, Decimal('800.00'))
```

- [ ] **Step 6: Run to confirm they pass**

```bash
python manage.py test budgets.tests.ComputeSpentTest -v 2
```

Expected: `OK` (4 tests pass)

- [ ] **Step 7: Commit**

```bash
git add budgets/utils.py budgets/tests.py
git commit -m "feat: add budget utility functions with full unit tests"
```

---

## Task 4: Serializer

**Files:**
- Create: `budgets/serializers.py`
- Modify: `budgets/tests.py` (add serializer/validation tests)

- [ ] **Step 1: Write failing validation tests**

Add to `budgets/tests.py`:
```python
from rest_framework.test import APITestCase
from django.urls import reverse


class BudgetValidationTest(APITestCase):
    def setUp(self):
        self.account = Account.objects.create(name='CIH Bank')
        self.expense_cat = Category.objects.create(
            name='Food', color='#ff0000', type='expense'
        )
        self.income_cat = Category.objects.create(
            name='Salary', color='#00ff00', type='income'
        )
        self.url = '/api/budgets/'

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
        self.client.post(self.url, {
            'category': str(self.expense_cat.id),
            'amount_limit': '3000.00', 'start_day': 25, 'rollover': False,
        }, format='json')
        res = self.client.post(self.url, {
            'category': str(self.expense_cat.id),
            'amount_limit': '2000.00', 'start_day': 1, 'rollover': True,
        }, format='json')
        self.assertEqual(res.status_code, 400)

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
        # Global budget
        r1 = self.client.post(self.url, {
            'category': str(self.expense_cat.id),
            'amount_limit': '3000.00', 'start_day': 25, 'rollover': False,
        }, format='json')
        self.assertEqual(r1.status_code, 201)
        # Account-scoped budget for same category — should be allowed
        r2 = self.client.post(self.url, {
            'category': str(self.expense_cat.id),
            'account': str(self.account.id),
            'amount_limit': '1500.00', 'start_day': 25, 'rollover': False,
        }, format='json')
        self.assertEqual(r2.status_code, 201)
```

- [ ] **Step 2: Run to confirm they fail (no urls/views yet)**

```bash
python manage.py test budgets.tests.BudgetValidationTest -v 2
```

Expected: errors about missing URL configuration.

- [ ] **Step 3: Create the serializer**

Create `budgets/serializers.py`:
```python
from decimal import Decimal
from rest_framework import serializers
from accounts.models import Account
from categories.models import Category
from budgets.models import Budget
from budgets.utils import current_period, compute_spent


class BudgetSerializer(serializers.ModelSerializer):
    # Write: accept UUID; Read: overridden in to_representation
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(type='expense')
    )
    account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(),
        required=False,
        allow_null=True,
    )

    # Computed read-only fields
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

        # Use account__isnull for the global case — PostgreSQL treats NULL != NULL,
        # so `filter(account=None)` would silently match nothing on Postgres.
        if account is None:
            qs = Budget.objects.filter(category=category, account__isnull=True)
        else:
            qs = Budget.objects.filter(category=category, account=account)
        if instance_id:
            qs = qs.exclude(id=instance_id)
        if qs.exists():
            scope = 'account-scoped' if account else 'global'
            raise serializers.ValidationError(
                f'A {scope} budget for this category already exists.'
            )
        return data

    def get_period(self, obj):
        start, end = current_period(obj.start_day)
        return {'start': start.isoformat(), 'end': end.isoformat()}

    def get_spent(self, obj):
        start, end = current_period(obj.start_day)
        return str(compute_spent(obj, start, end))

    def get_remaining(self, obj):
        start, end = current_period(obj.start_day)
        spent = compute_spent(obj, start, end)
        return str(obj.amount_limit - spent)

    def get_utilization_pct(self, obj):
        if obj.amount_limit <= 0:
            return 0.0
        start, end = current_period(obj.start_day)
        spent = compute_spent(obj, start, end)
        return round(float(spent / obj.amount_limit) * 100, 1)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Replace FK PKs with nested objects on read
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

- [ ] **Step 4: Create urls.py and views.py (minimal — just for validation tests)**

Create `budgets/urls.py`:
```python
from rest_framework.routers import DefaultRouter
from budgets.views import BudgetViewSet

router = DefaultRouter()
router.register('budgets', BudgetViewSet, basename='budget')

urlpatterns = router.urls
```

Create `budgets/views.py` (minimal stub — history action added in Task 5):
```python
from rest_framework.viewsets import ModelViewSet
from budgets.models import Budget
from budgets.serializers import BudgetSerializer


class BudgetViewSet(ModelViewSet):
    serializer_class = BudgetSerializer

    def get_queryset(self):
        return Budget.objects.select_related('category', 'account').all()
```

Wire up in `finance_management_api/urls.py` — add:
```python
path('api/', include('budgets.urls')),
```

- [ ] **Step 5: Run validation tests**

```bash
python manage.py test budgets.tests.BudgetValidationTest -v 2
```

Expected: `OK` (8 tests pass)

- [ ] **Step 6: Commit**

```bash
git add budgets/serializers.py budgets/views.py budgets/urls.py budgets/tests.py finance_management_api/urls.py
git commit -m "feat: add BudgetSerializer with validation and BudgetViewSet stub"
```

---

## Task 5: CRUD integration tests

**Files:**
- Modify: `budgets/tests.py` (add CRUD API tests)

- [ ] **Step 1: Write CRUD tests**

Add to `budgets/tests.py`:
```python
class BudgetCRUDTest(APITestCase):
    def setUp(self):
        self.account = Account.objects.create(name='CIH Bank')
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
        # category is nested on read
        self.assertIsInstance(data['category'], dict)
        self.assertEqual(data['category']['name'], 'Food')
        # account is null for global budget
        self.assertIsNone(data['account'])

    def test_create_budget_scoped_to_account(self):
        res = self._create_budget(account=str(self.account.id))
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['account']['name'], 'CIH Bank')

    def test_list_budgets(self):
        self._create_budget()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()['results']), 1)

    def test_retrieve_budget(self):
        created = self._create_budget().json()
        res = self.client.get(f"{self.url}{created['id']}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['id'], created['id'])

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
```

- [ ] **Step 2: Run CRUD tests**

```bash
python manage.py test budgets.tests.BudgetCRUDTest -v 2
```

Expected: `OK` (8 tests pass)

- [ ] **Step 3: Commit**

```bash
git add budgets/tests.py
git commit -m "test: add CRUD integration tests for budget API"
```

---

## Task 6: History endpoint

**Files:**
- Modify: `budgets/views.py` (add `@action history`)
- Modify: `budgets/tests.py` (add history + rollover tests)

- [ ] **Step 1: Write failing history tests**

Add to `budgets/tests.py`:
```python
class BudgetHistoryTest(APITestCase):
    def setUp(self):
        self.account = Account.objects.create(name='CIH Bank')
        self.category = Category.objects.create(
            name='Food', color='#ff0000', type='expense'
        )
        self.budget = Budget.objects.create(
            category=self.category,
            amount_limit=Decimal('3000.00'),
            start_day=1,
            rollover=False,
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
        from dateutil.relativedelta import relativedelta as rd
        budget = Budget.objects.create(
            category=self.category,
            account=self.account,
            amount_limit=Decimal('3000.00'),
            start_day=1,
            rollover=True,
        )
        # Place a transaction on the 5th of 2 months ago.
        # With start_day=1, the oldest of 3 periods is always the 1st of (current - 2 months).
        # Using a fixed reference of 2026-03-15 makes the test deterministic regardless of
        # when it runs. The 3 periods will be: Jan 1–31, Feb 1–28, Mar 1–31 2026.
        # We place spending in Jan to test surplus carry-forward to Feb.
        Transaction.objects.create(
            label='Groceries', amount=Decimal('-2500.00'),
            date=date(2026, 1, 5), type='expense',
            account=self.account, category=self.category,
        )
        # Use ?periods=3 — endpoint uses date.today() internally, so we verify
        # the oldest period's data against our known transaction date.
        # Since we cannot inject a reference date into the endpoint, we instead
        # create the transaction in the oldest of 3 periods relative to today,
        # computed here for comparison:
        from budgets.utils import last_n_periods
        from datetime import date as d
        periods = last_n_periods(1, 3)
        oldest_start, oldest_end = periods[0]
        second_start, _ = periods[1]
        # Put the transaction in the oldest period
        Transaction.objects.filter(label='Groceries').update(date=oldest_start.replace(day=5))

        res = self.client.get(f'/api/budgets/{budget.id}/history/?periods=3')
        history = res.json()['history']
        oldest = history[0]
        second = history[1]
        self.assertEqual(oldest['spent'], '2500.00')
        # surplus from oldest = 3000 - 2500 = 500; second effective_limit = 3000 + 500
        self.assertEqual(Decimal(second['effective_limit']), Decimal('3500.00'))

    def test_history_rollover_overspend_no_debt(self):
        """Overspending does not reduce the next period's effective_limit."""
        from budgets.utils import last_n_periods
        budget = Budget.objects.create(
            category=self.category,
            account=self.account,
            amount_limit=Decimal('3000.00'),
            start_day=1,
            rollover=True,
        )
        # Place a transaction that exceeds the limit in the oldest of 3 periods
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
        # remaining should be negative (overspent)
        self.assertLess(Decimal(oldest['remaining']), Decimal('0'))
        # next period effective_limit must NOT be reduced below amount_limit
        self.assertEqual(Decimal(second['effective_limit']), Decimal('3000.00'))

    def test_history_no_rollover_fresh_each_period(self):
        # rollover=False: even with surplus, next effective_limit stays at amount_limit
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
```

- [ ] **Step 2: Run to confirm they fail**

```bash
python manage.py test budgets.tests.BudgetHistoryTest -v 2
```

Expected: 404 errors — history action doesn't exist yet.

- [ ] **Step 3: Add history action to views.py**

Replace `budgets/views.py` with:
```python
from decimal import Decimal
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from budgets.models import Budget
from budgets.serializers import BudgetSerializer
from budgets.utils import last_n_periods, compute_spent


class BudgetViewSet(ModelViewSet):
    serializer_class = BudgetSerializer

    def get_queryset(self):
        return Budget.objects.select_related('category', 'account').all()

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
                'effective_limit': str(effective_limit),
                'spent': str(spent),
                'remaining': str(remaining),
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

- [ ] **Step 4: Run history tests**

```bash
python manage.py test budgets.tests.BudgetHistoryTest -v 2
```

Expected: `OK` (10 tests pass)

- [ ] **Step 5: Commit**

```bash
git add budgets/views.py budgets/tests.py
git commit -m "feat: add budget history endpoint with rollover logic"
```

---

## Task 7: Full test suite and final verification

- [ ] **Step 1: Run the entire project test suite**

```bash
python manage.py test -v 2
```

Expected: all tests pass (no regressions in accounts, categories, transactions, goals, analytics).

- [ ] **Step 2: Check Django system check**

```bash
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Verify migration state is clean**

```bash
python manage.py migrate --check
```

Expected: no unapplied migrations.

- [ ] **Step 4: Commit final state**

```bash
git add -A
git commit -m "feat: complete budgeting feature — model, utils, serializer, viewset, history"
```

---

## Quick Reference

```bash
# Run only budget tests
python manage.py test budgets -v 2

# Run full suite
python manage.py test -v 2

# Django shell to inspect
python manage.py shell
>>> from budgets.utils import current_period
>>> current_period(25)
```
