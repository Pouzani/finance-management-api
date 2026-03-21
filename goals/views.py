from rest_framework.viewsets import ModelViewSet
from goals.models import Goal
from goals.serializers import GoalSerializer


class GoalViewSet(ModelViewSet):
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
