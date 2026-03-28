import uuid
from decimal import Decimal
from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status


def make_user(username='testuser'):
    return User.objects.create_user(username=username, password='testpass123')


def make_goal(user, label='Vacances', current='500', target='5000'):
    from goals.models import Goal
    return Goal.objects.create(
        label=label, current=Decimal(current), target=Decimal(target),
        icon='plane', color='#3357FF', user=user,
    )


class GoalModelTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_goal_has_uuid_pk(self):
        from goals.models import Goal
        goal = Goal.objects.create(
            label="Fonds d'urgence", current=Decimal("2000"), target=Decimal("10000"),
            icon="shield", color="#FF5733", user=self.user,
        )
        self.assertIsInstance(goal.id, uuid.UUID)

    def test_goal_str(self):
        from goals.models import Goal
        goal = Goal.objects.create(
            label="Vacances", current=Decimal("500"), target=Decimal("5000"),
            icon="plane", color="#3357FF", user=self.user,
        )
        self.assertEqual(str(goal), "Vacances")

    def test_goal_has_user_field(self):
        from goals.models import Goal
        goal = Goal.objects.create(
            label='Test', current='0', target='1000',
            icon='star', color='#fff', user=self.user,
        )
        self.assertEqual(goal.user, self.user)


class GoalAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
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

    def test_unauthenticated_request_returns_401(self):
        unauth_client = APIClient()
        response = unauth_client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_goals(self):
        make_goal(self.user)
        make_goal(self.user, label='Goal 2')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_user_only_sees_own_goals(self):
        other_user = make_user('other')
        make_goal(self.user, label='My Goal')
        make_goal(other_user, label='Other Goal')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['label'], 'My Goal')

    def test_create_goal(self):
        response = self.client.post(self.url, self._goal_payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['label'], "Fonds d'urgence")

    def test_create_goal_assigns_current_user(self):
        from goals.models import Goal
        self.client.post(self.url, self._goal_payload(), format='json')
        goal = Goal.objects.get(label="Fonds d'urgence")
        self.assertEqual(goal.user, self.user)

    def test_create_goal_requires_fields(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_goal(self):
        goal = make_goal(self.user)
        payload = self._goal_payload(label="Updated Goal")
        response = self.client.put(f'/api/goals/{goal.pk}/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        goal.refresh_from_db()
        self.assertEqual(goal.label, 'Updated Goal')

    def test_cannot_update_other_users_goal(self):
        other_user = make_user('other')
        goal = make_goal(other_user)
        response = self.client.put(f'/api/goals/{goal.pk}/', self._goal_payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_goal(self):
        goal = make_goal(self.user)
        response = self.client.delete(f'/api/goals/{goal.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        from goals.models import Goal
        self.assertFalse(Goal.objects.filter(pk=goal.pk).exists())

    def test_cannot_delete_other_users_goal(self):
        other_user = make_user('other')
        goal = make_goal(other_user)
        response = self.client.delete(f'/api/goals/{goal.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class GoalAdminTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin', password='password', email='admin@test.com'
        )
        self.client.force_login(self.superuser)

    def _make_goal(self, current='250.00', target='1000.00', color='#3498db'):
        from goals.models import Goal
        return Goal.objects.create(
            label="Emergency Fund",
            current=Decimal(current),
            target=Decimal(target),
            icon="shield",
            color=color,
            user=self.superuser,
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
        ma = GoalAdmin(model=Goal, admin_site=AdminSite())
        goal = Goal(
            label="Zero Target", current=Decimal("0"), target=Decimal("0"),
            icon="x", color="#fff", user=self.superuser,
        )
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
