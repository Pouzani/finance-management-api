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
