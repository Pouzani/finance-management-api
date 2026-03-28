from rest_framework.viewsets import ModelViewSet
from core.mixins import UserOwnedMixin
from goals.models import Goal
from goals.serializers import GoalSerializer


class GoalViewSet(UserOwnedMixin, ModelViewSet):
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
