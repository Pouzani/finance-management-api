import uuid
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


class GoalModelTest(TestCase):
    def test_goal_has_uuid_pk(self):
        from goals.models import Goal
        goal = Goal.objects.create(
            label="Fonds d'urgence", current=Decimal("2000"), target=Decimal("10000"),
            icon="shield", color="#FF5733"
        )
        self.assertIsInstance(goal.id, uuid.UUID)

    def test_goal_str(self):
        from goals.models import Goal
        goal = Goal.objects.create(
            label="Vacances", current=Decimal("500"), target=Decimal("5000"),
            icon="plane", color="#3357FF"
        )
        self.assertEqual(str(goal), "Vacances")


class GoalAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/goals/'

    def _goal_payload(self, **overrides):
        data = {
            'label': "Fonds d'urgence",
            'current': '2000.00',
            'target': '10000.00',
            'icon': 'shield',
            'color': '#FF5733',
        }
        data.update(overrides)
        return data

    def _create_goal(self):
        from goals.models import Goal
        return Goal.objects.create(
            label="Vacances", current=Decimal("500"), target=Decimal("5000"),
            icon="plane", color="#3357FF"
        )

    def test_list_goals(self):
        self._create_goal()
        self._create_goal()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_create_goal(self):
        response = self.client.post(self.url, self._goal_payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['label'], "Fonds d'urgence")

    def test_create_goal_requires_fields(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_goal(self):
        goal = self._create_goal()
        payload = self._goal_payload(label="Updated Goal")
        response = self.client.put(f'/api/goals/{goal.pk}/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        goal.refresh_from_db()
        self.assertEqual(goal.label, 'Updated Goal')

    def test_delete_goal(self):
        goal = self._create_goal()
        response = self.client.delete(f'/api/goals/{goal.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        from goals.models import Goal
        self.assertFalse(Goal.objects.filter(pk=goal.pk).exists())
