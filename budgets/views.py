from rest_framework.viewsets import ModelViewSet
from budgets.models import Budget
from budgets.serializers import BudgetSerializer


class BudgetViewSet(ModelViewSet):
    serializer_class = BudgetSerializer

    def get_queryset(self):
        return Budget.objects.select_related('category', 'account').all()
