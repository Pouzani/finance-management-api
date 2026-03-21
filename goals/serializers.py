from rest_framework import serializers
from goals.models import Goal


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = ['id', 'label', 'current', 'target', 'icon', 'color']
        read_only_fields = ['id']
