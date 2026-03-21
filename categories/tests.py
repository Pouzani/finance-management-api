import uuid
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


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
