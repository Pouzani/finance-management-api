# Backoffice Admin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register all five domain models in Django's built-in admin with enhanced list displays, search, filters, and inline relationships.

**Architecture:** Edit each app's existing `admin.py` stub in-place. Each admin class uses `get_queryset()` overrides for computed annotations and `@admin.display` decorators for computed columns. No new files, no migrations, no settings changes — `admin/` is already wired in `urls.py` and `django.contrib.admin` is in `INSTALLED_APPS`.

**Tech Stack:** Django 6.0.3, `django.contrib.admin`, `django.db.models` (Sum, Count, Value, Coalesce), `django.utils.safestring.mark_safe`, `re`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `accounts/admin.py` | Modify | `TransactionInline` + `AccountAdmin` (balance, count) |
| `accounts/tests.py` | Modify | Add `AccountAdminTest` class |
| `categories/admin.py` | Modify | `CategoryAdmin` (color_preview, transaction_count) |
| `categories/tests.py` | Modify | Add `CategoryAdminTest` class |
| `transactions/admin.py` | Modify | `TransactionAdmin` (date_hierarchy, FK filters) |
| `transactions/tests.py` | Modify | Add `TransactionAdminTest` class |
| `goals/admin.py` | Modify | `GoalAdmin` (progress_pct, color_preview) |
| `goals/tests.py` | Modify | Add `GoalAdminTest` class |
| `budgets/admin.py` | Modify | `BudgetAdmin` (account_display) |
| `budgets/tests.py` | Modify | Add `BudgetAdminTest` class |

---

## Shared Test Helper

All admin tests follow the same pattern. Add this import block and helper to each test file:

```python
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory
```

Create a superuser in `setUp`:
```python
self.superuser = User.objects.create_superuser(
    username='admin', password='password', email='admin@test.com'
)
self.client.force_login(self.superuser)
```

To test a list page loads: `GET /admin/<app>/<model>/` → expect status 200.
To test computed columns: call the admin method directly on a test object.

---

## Task 1: AccountAdmin with TransactionInline

**Files:**
- Modify: `accounts/admin.py`
- Modify: `accounts/tests.py`

- [ ] **Step 1: Write failing tests**

Append this class to `accounts/tests.py`:

```python
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User


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
        from decimal import Decimal
        account = Account.objects.create(name="CIH")
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
        from accounts.admin import AccountAdmin
        from decimal import Decimal
        account = self._make_account_with_transactions()
        ma = AccountAdmin(model=account.__class__, admin_site=AdminSite())
        # get_queryset annotates balance — call it via the list view
        from django.test import RequestFactory
        request = RequestFactory().get('/admin/accounts/account/')
        request.user = self.superuser
        qs = ma.get_queryset(request)
        annotated = qs.get(pk=account.pk)
        self.assertEqual(ma.balance(annotated), Decimal("3500.00"))

    def test_transaction_count_display_method(self):
        from accounts.admin import AccountAdmin
        from django.test import RequestFactory
        account = self._make_account_with_transactions()
        ma = AccountAdmin(model=account.__class__, admin_site=AdminSite())
        request = RequestFactory().get('/admin/accounts/account/')
        request.user = self.superuser
        qs = ma.get_queryset(request)
        annotated = qs.get(pk=account.pk)
        self.assertEqual(ma.transaction_count(annotated), 2)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/pouzani/projects/finance_management_api && source myenv/bin/activate && python manage.py test accounts.tests.AccountAdminTest -v 2
```

Expected: FAIL — `ImportError: cannot import name 'AccountAdmin' from 'accounts.admin'`

- [ ] **Step 3: Implement `accounts/admin.py`**

Replace the contents of `accounts/admin.py` with:

```python
from django.contrib import admin
from django.db.models import Sum, Count, Value, DecimalField
from django.db.models.functions import Coalesce

from transactions.models import Transaction
from .models import Account


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    max_num = 0  # read-only: no new transactions can be added via inline
    fields = ('label', 'amount', 'type', 'category', 'date')
    readonly_fields = ('label', 'amount', 'type', 'category', 'date')
    ordering = ('-date',)

    # Note: Django's inline get_queryset() receives no reference to the parent object,
    # so limiting to "last 10" per-account is not possible without a complex subquery.
    # All transactions for the account are shown, ordered most-recent first.


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'balance', 'transaction_count', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('id', 'created_at', 'balance', 'transaction_count')
    inlines = [TransactionInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _balance=Coalesce(
                Sum('transactions__amount'),
                Value(0),
                output_field=DecimalField(),
            ),
            _transaction_count=Count('transactions'),
        )

    @admin.display(description='Balance', ordering='_balance')
    def balance(self, obj):
        return obj._balance

    @admin.display(description='Transactions', ordering='_transaction_count')
    def transaction_count(self, obj):
        return obj._transaction_count
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test accounts.tests.AccountAdminTest -v 2
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add accounts/admin.py accounts/tests.py
git commit -m "feat: add enhanced AccountAdmin with TransactionInline and computed columns"
```

---

## Task 2: CategoryAdmin

**Files:**
- Modify: `categories/admin.py`
- Modify: `categories/tests.py`

- [ ] **Step 1: Write failing tests**

Append to `categories/tests.py`:

```python
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory


class CategoryAdminTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin', password='password', email='admin@test.com'
        )
        self.client.force_login(self.superuser)

    def _make_category_with_transactions(self):
        from categories.models import Category
        from accounts.models import Account
        from transactions.models import Transaction
        from decimal import Decimal
        cat = Category.objects.create(name="Alimentation", color="#FF5733", type="expense")
        account = Account.objects.create(name="CIH")
        Transaction.objects.create(
            label="Groceries", amount=Decimal("-200.00"),
            date="2024-01-15", type="expense", account=account, category=cat
        )
        return cat

    def test_category_list_page_loads(self):
        self._make_category_with_transactions()
        response = self.client.get('/admin/categories/category/')
        self.assertEqual(response.status_code, 200)

    def test_color_preview_renders_span(self):
        from categories.admin import CategoryAdmin
        from categories.models import Category
        cat = Category.objects.create(name="Test", color="#FF5733", type="expense")
        ma = CategoryAdmin(model=Category, admin_site=AdminSite())
        result = str(ma.color_preview(cat))
        self.assertIn('#FF5733', result)
        self.assertIn('<span', result)

    def test_color_preview_sanitizes_invalid_color(self):
        from categories.admin import CategoryAdmin
        from categories.models import Category
        cat = Category.objects.create(name="Bad", color='"><script>alert(1)</script>', type="expense")
        ma = CategoryAdmin(model=Category, admin_site=AdminSite())
        result = str(ma.color_preview(cat))
        self.assertNotIn('<script>', result)
        self.assertIn('#cccccc', result)

    def test_transaction_count_method(self):
        from categories.admin import CategoryAdmin
        cat = self._make_category_with_transactions()
        ma = CategoryAdmin(model=cat.__class__, admin_site=AdminSite())
        request = RequestFactory().get('/admin/categories/category/')
        request.user = self.superuser
        qs = ma.get_queryset(request)
        annotated = qs.get(pk=cat.pk)
        self.assertEqual(ma.transaction_count(annotated), 1)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test categories.tests.CategoryAdminTest -v 2
```

Expected: FAIL — `ImportError: cannot import name 'CategoryAdmin'`

- [ ] **Step 3: Implement `categories/admin.py`**

```python
import re
from django.contrib import admin
from django.db.models import Count
from django.utils.safestring import mark_safe

from .models import Category

_SAFE_COLOR_RE = re.compile(
    r'^#[0-9a-fA-F]{3}$|^#[0-9a-fA-F]{6}$|^[a-zA-Z]+$|^rgb\([\d\s,]+\)$'
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'color_preview', 'transaction_count')
    search_fields = ('name',)
    list_filter = ('type',)
    readonly_fields = ('id', 'color_preview', 'transaction_count')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _transaction_count=Count('transactions'),
        )

    @admin.display(description='Color')
    def color_preview(self, obj):
        color = obj.color if _SAFE_COLOR_RE.match(obj.color or '') else '#cccccc'
        return mark_safe(
            f'<span style="display:inline-block;width:16px;height:16px;'
            f'background:{color};border-radius:3px;border:1px solid #ccc;"></span>'
            f' {obj.color}'
        )

    @admin.display(description='Transactions', ordering='_transaction_count')
    def transaction_count(self, obj):
        return obj._transaction_count
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test categories.tests.CategoryAdminTest -v 2
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add categories/admin.py categories/tests.py
git commit -m "feat: add enhanced CategoryAdmin with color preview and transaction count"
```

---

## Task 3: TransactionAdmin

**Files:**
- Modify: `transactions/admin.py`
- Modify: `transactions/tests.py`

- [ ] **Step 1: Write failing tests**

Append to `transactions/tests.py`:

```python
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User


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
        from decimal import Decimal
        account = Account.objects.create(name="CIH")
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
        ma = TransactionAdmin(model=None, admin_site=AdminSite())
        filter_fields = [
            f if isinstance(f, str) else f[0]
            for f in ma.list_filter
        ]
        self.assertIn('type', filter_fields)
        self.assertIn('category', filter_fields)
        self.assertIn('account', filter_fields)

    def test_date_hierarchy_set(self):
        from transactions.admin import TransactionAdmin
        ma = TransactionAdmin(model=None, admin_site=AdminSite())
        self.assertEqual(ma.date_hierarchy, 'date')
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test transactions.tests.TransactionAdminTest -v 2
```

Expected: FAIL — `ImportError: cannot import name 'TransactionAdmin'`

- [ ] **Step 3: Implement `transactions/admin.py`**

```python
from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('label', 'amount', 'type', 'account', 'category', 'date')
    search_fields = ('label',)
    list_filter = [
        'type',
        ('category', admin.RelatedOnlyFieldListFilter),
        ('account', admin.RelatedOnlyFieldListFilter),
    ]
    date_hierarchy = 'date'
    ordering = ('-date',)
    readonly_fields = ('id', 'created_at', 'updated_at')
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test transactions.tests.TransactionAdminTest -v 2
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add transactions/admin.py transactions/tests.py
git commit -m "feat: add enhanced TransactionAdmin with date hierarchy and FK filters"
```

---

## Task 4: GoalAdmin

**Files:**
- Modify: `goals/admin.py`
- Modify: `goals/tests.py`

- [ ] **Step 1: Write failing tests**

Append to `goals/tests.py`:

```python
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User


class GoalAdminTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin', password='password', email='admin@test.com'
        )
        self.client.force_login(self.superuser)

    def _make_goal(self, current='250.00', target='1000.00', color='#3498db'):
        from goals.models import Goal
        from decimal import Decimal
        return Goal.objects.create(
            label="Emergency Fund",
            current=Decimal(current),
            target=Decimal(target),
            icon="shield",
            color=color,
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
        from decimal import Decimal
        ma = GoalAdmin(model=Goal, admin_site=AdminSite())
        # Use an unsaved in-memory instance to test the zero-division guard
        goal = Goal(label="Zero Target", current=Decimal("0"), target=Decimal("0"), icon="x", color="#fff")
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

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test goals.tests.GoalAdminTest -v 2
```

Expected: FAIL — `ImportError: cannot import name 'GoalAdmin'`

- [ ] **Step 3: Implement `goals/admin.py`**

```python
import re
from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import Goal

_SAFE_COLOR_RE = re.compile(
    r'^#[0-9a-fA-F]{3}$|^#[0-9a-fA-F]{6}$|^[a-zA-Z]+$|^rgb\([\d\s,]+\)$'
)


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('label', 'current', 'target', 'progress_pct', 'icon', 'color_preview')
    search_fields = ('label',)
    readonly_fields = ('id', 'progress_pct', 'color_preview')

    @admin.display(description='Progress')
    def progress_pct(self, obj):
        if not obj.target:
            return '0%'
        pct = (obj.current / obj.target) * 100
        return f'{pct:.1f}%'

    @admin.display(description='Color')
    def color_preview(self, obj):
        color = obj.color if _SAFE_COLOR_RE.match(obj.color or '') else '#cccccc'
        return mark_safe(
            f'<span style="display:inline-block;width:16px;height:16px;'
            f'background:{color};border-radius:3px;border:1px solid #ccc;"></span>'
            f' {obj.color}'
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test goals.tests.GoalAdminTest -v 2
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add goals/admin.py goals/tests.py
git commit -m "feat: add enhanced GoalAdmin with progress percentage and color preview"
```

---

## Task 5: BudgetAdmin

**Files:**
- Modify: `budgets/admin.py`
- Modify: `budgets/tests.py`

- [ ] **Step 1: Write failing tests**

Append to `budgets/tests.py`:

```python
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User


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
        account = Account.objects.create(name="CIH") if with_account else None
        return Budget.objects.create(
            category=cat,
            account=account,
            amount_limit=Decimal("500.00"),
            start_day=1,
            rollover=False,
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

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test budgets.tests.BudgetAdminTest -v 2
```

Expected: FAIL — `ImportError: cannot import name 'BudgetAdmin'`

- [ ] **Step 3: Implement `budgets/admin.py`**

```python
from django.contrib import admin

from .models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'category', 'account_display', 'amount_limit', 'start_day', 'rollover')
    list_filter = ('rollover', 'account', 'category')
    readonly_fields = ('id', 'created_at', 'updated_at')

    @admin.display(description='Scope')
    def account_display(self, obj):
        return obj.account.name if obj.account_id else 'global'
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test budgets.tests.BudgetAdminTest -v 2
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add budgets/admin.py budgets/tests.py
git commit -m "feat: add enhanced BudgetAdmin with account scope display"
```

---

## Task 6: Full Test Run & Smoke Test

- [ ] **Step 1: Run full test suite**

```bash
python manage.py test -v 2
```

Expected: All tests pass, including new admin test classes.

- [ ] **Step 2: Create superuser for manual smoke test**

```bash
python manage.py createsuperuser
```

Use username `admin`, any password.

- [ ] **Step 3: Start dev server and open admin**

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/admin/` — log in, verify:
- All 5 models appear in the admin index
- Account list shows balance and transaction count columns
- Account detail page shows recent transactions inline
- Category list shows color swatches
- Transaction list has date drill-down bar at top and sidebar filters
- Goal list shows progress percentages
- Budget list shows "global" or account name in Scope column

- [ ] **Step 4: Seed data and re-verify (optional)**

```bash
python manage.py seed_data
```

Re-open admin to verify computed columns and filters work with real data.
