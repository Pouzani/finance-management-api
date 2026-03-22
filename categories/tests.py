import uuid
from decimal import Decimal
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient
from rest_framework import status
from categories.models import Category
from accounts.models import Account
from transactions.models import Transaction
from categories.admin import CategoryAdmin


class CategoryModelTest(TestCase):
    def test_category_has_uuid_pk(self):
        from categories.models import Category
        cat = Category.objects.create(name="Logement", color="#FF5733", type="expense")
        self.assertIsInstance(cat.id, uuid.UUID)

    def test_category_str(self):
        from categories.models import Category
        cat = Category.objects.create(name="Alimentation", color="#33FF57", type="expense")
        self.assertEqual(str(cat), "Alimentation")

    def test_category_type_choices(self):
        from categories.models import Category
        income_cat = Category.objects.create(name="Salaire", color="#0000FF", type="income")
        expense_cat = Category.objects.create(name="Transport", color="#FF0000", type="expense")
        self.assertEqual(income_cat.type, "income")
        self.assertEqual(expense_cat.type, "expense")


class CategoryAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/categories/'

    def _make_category(self, name="Logement", type="expense"):
        from categories.models import Category
        return Category.objects.create(name=name, color="#FF5733", type=type)

    def test_list_categories(self):
        self._make_category("Logement")
        self._make_category("Alimentation")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_create_category(self):
        data = {'name': 'Transport', 'color': '#FF5733', 'type': 'expense'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Transport')

    def test_create_category_invalid_type(self):
        data = {'name': 'Bad', 'color': '#FF5733', 'type': 'invalid'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_category_requires_fields(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CategoryAdminTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin', password='password', email='admin@test.com'
        )
        self.client.force_login(self.superuser)

    def _make_category_with_transactions(self):
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
        cat = Category.objects.create(name="Test", color="#FF5733", type="expense")
        ma = CategoryAdmin(model=Category, admin_site=AdminSite())
        result = str(ma.color_preview(cat))
        self.assertIn('#FF5733', result)
        self.assertIn('<span', result)

    def test_color_preview_sanitizes_invalid_color(self):
        cat = Category.objects.create(name="Bad", color='"><script>alert(1)</script>', type="expense")
        ma = CategoryAdmin(model=Category, admin_site=AdminSite())
        result = str(ma.color_preview(cat))
        self.assertNotIn('<script>', result)
        self.assertIn('#cccccc', result)

    def test_transaction_count_method(self):
        cat = self._make_category_with_transactions()
        ma = CategoryAdmin(model=cat.__class__, admin_site=AdminSite())
        request = RequestFactory().get('/admin/categories/category/')
        request.user = self.superuser
        qs = ma.get_queryset(request)
        annotated = qs.get(pk=cat.pk)
        self.assertEqual(ma.transaction_count(annotated), 1)
