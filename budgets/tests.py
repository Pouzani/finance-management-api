import uuid
from datetime import date
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APITestCase
from django.urls import reverse
from accounts.models import Account
from categories.models import Category
from budgets.models import Budget
from budgets.utils import current_period, last_n_periods, compute_spent
from transactions.models import Transaction


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
