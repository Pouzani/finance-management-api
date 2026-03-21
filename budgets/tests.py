import uuid
from datetime import date
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APITestCase
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
        # Place a transaction in the oldest of 3 periods relative to today
        from budgets.utils import last_n_periods
        from datetime import date as d
        periods = last_n_periods(1, 3)
        oldest_start, oldest_end = periods[0]
        second_start, _ = periods[1]
        # Put the transaction in the oldest period
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
