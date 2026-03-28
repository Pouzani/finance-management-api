from decimal import Decimal
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce, TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from transactions.models import Transaction


class MonthlyFlowView(APIView):
    def get(self, request):
        qs = (
            Transaction.objects
            .filter(account__user=request.user)
            .annotate(month=TruncMonth('date'))
            .values('month', 'type')
            .annotate(total=Coalesce(Sum('amount'), Value(0), output_field=DecimalField()))
            .order_by('month')
        )

        flow_by_month = {}
        for row in qs:
            month_str = row['month'].strftime('%Y-%m')
            if month_str not in flow_by_month:
                flow_by_month[month_str] = {'month': month_str, 'income': Decimal('0'), 'expenses': Decimal('0')}
            if row['type'] == 'income':
                flow_by_month[month_str]['income'] += row['total']
            else:
                flow_by_month[month_str]['expenses'] += abs(row['total'])

        result = sorted(flow_by_month.values(), key=lambda x: x['month'])
        return Response(result)


class CategorySplitView(APIView):
    def get(self, request):
        qs = (
            Transaction.objects
            .filter(account__user=request.user, type='expense')
            .values('category__name', 'category__color')
            .annotate(total=Coalesce(Sum('amount'), Value(0), output_field=DecimalField()))
            .order_by('category__name')
        )

        result = [
            {
                'name': row['category__name'],
                'value': abs(row['total']),
                'color': row['category__color'],
            }
            for row in qs
            if row['category__name'] is not None
        ]
        return Response(result)
