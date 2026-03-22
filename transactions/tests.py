import uuid
from decimal import Decimal
from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status


def make_account(name="CIH"):
    from accounts.models import Account
    return Account.objects.create(name=name)


def make_category(name="Logement", type="expense"):
    from categories.models import Category
    return Category.objects.create(name=name, color="#FF5733", type=type)


class TransactionModelTest(TestCase):
    def setUp(self):
        self.account = make_account()
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
        self.url = '/api/transactions/'
        self.account = make_account()
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

    def test_list_transactions(self):
        self._create_transaction(label="T1")
        self._create_transaction(label="T2")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_create_transaction(self):
        response = self.client.post(self.url, self._transaction_payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['label'], 'Loyer')
        self.assertIn('category_detail', response.data)
        self.assertIn('account_name', response.data)

    def test_create_transaction_validates_type_amount_consistency(self):
        # expense with positive amount should fail
        payload = self._transaction_payload(type='expense', amount='1500.00')
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # income with negative amount should fail
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
