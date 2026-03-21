from decimal import Decimal
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from budgets.models import Budget
from budgets.serializers import BudgetSerializer
from budgets.utils import last_n_periods, compute_spent


class BudgetViewSet(ModelViewSet):
    serializer_class = BudgetSerializer

    def get_queryset(self):
        return Budget.objects.select_related('category', 'account').all()

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        budget = self.get_object()

        try:
            n = int(request.query_params.get('periods', 12))
        except ValueError:
            return Response(
                {'error': 'periods must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (1 <= n <= 24):
            return Response(
                {'error': 'periods must be between 1 and 24.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        periods = last_n_periods(budget.start_day, n)
        effective_limit = budget.amount_limit
        records = []

        for period_start, period_end in periods:
            spent = compute_spent(budget, period_start, period_end)
            remaining = effective_limit - spent
            surplus_carried = max(remaining, Decimal('0'))
            records.append({
                'period': {
                    'start': period_start.isoformat(),
                    'end': period_end.isoformat(),
                },
                'effective_limit': f'{effective_limit:.2f}',
                'spent': f'{spent:.2f}',
                'remaining': f'{remaining:.2f}',
            })
            effective_limit = (
                budget.amount_limit + surplus_carried
                if budget.rollover
                else budget.amount_limit
            )

        return Response({
            'budget_id': str(budget.id),
            'periods_requested': n,
            'history': records,
        })
