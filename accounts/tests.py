import uuid
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


class AccountModelTest(TestCase):
    def test_account_has_uuid_pk(self):
        from accounts.models import Account
        account = Account.objects.create(name="CIH Principale")
        self.assertIsInstance(account.id, uuid.UUID)

    def test_account_str(self):
        from accounts.models import Account
        account = Account.objects.create(name="Wafacash")
        self.assertEqual(str(account), "Wafacash")

    def test_account_created_at_set(self):
        from accounts.models import Account
        account = Account.objects.create(name="Attijari")
        self.assertIsNotNone(account.created_at)

    def test_balance_zero_with_no_transactions(self):
        from accounts.models import Account
        from django.db.models import Sum, Value, DecimalField
        from django.db.models.functions import Coalesce
        account = Account.objects.create(name="Empty Account")
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
        account = Account.objects.create(name="CIH")
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
        self.url = '/api/accounts/'

    def _make_account(self, name="CIH"):
        from accounts.models import Account
        return Account.objects.create(name=name)

    def test_list_accounts(self):
        self._make_account("CIH")
        self._make_account("Wafacash")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_create_account(self):
        response = self.client.post(self.url, {'name': 'CIH Principale'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'CIH Principale')
        self.assertIn('balance', response.data)

    def test_create_account_requires_name(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_account(self):
        account = self._make_account("Old Name")
        response = self.client.put(f'/api/accounts/{account.pk}/', {'name': 'New Name'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        account.refresh_from_db()
        self.assertEqual(account.name, 'New Name')

    def test_delete_account(self):
        account = self._make_account("To Delete")
        response = self.client.delete(f'/api/accounts/{account.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        from accounts.models import Account
        self.assertFalse(Account.objects.filter(pk=account.pk).exists())
