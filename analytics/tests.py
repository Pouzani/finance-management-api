from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


def make_account():
    from accounts.models import Account
    return Account.objects.create(name="CIH")


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
        self.account = make_account()
        self.income_cat = make_category("Salaire", "income")
        self.expense_cat = make_category("Logement", "expense")

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


class CategorySplitAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.account = make_account()
        self.logement = make_category("Logement", "expense")
        self.alimentation = make_category("Alimentation", "expense")
        self.salaire = make_category("Salaire", "income")

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
