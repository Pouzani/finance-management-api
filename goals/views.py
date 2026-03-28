from rest_framework.viewsets import ModelViewSet
from core.mixins import UserOwnedMixin
from goals.models import Goal
from goals.serializers import GoalSerializer


class GoalViewSet(UserOwnedMixin, ModelViewSet):
    serializer_class = GoalSerializer

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)
