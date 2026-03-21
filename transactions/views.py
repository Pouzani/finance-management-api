import django_filters
from rest_framework.viewsets import ModelViewSet
from transactions.models import Transaction
from transactions.serializers import TransactionSerializer


class TransactionFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    category = django_filters.UUIDFilter(field_name='category__id')
    account = django_filters.UUIDFilter(field_name='account__id')
    type = django_filters.ChoiceFilter(choices=Transaction.TYPE_CHOICES)

    class Meta:
        model = Transaction
        fields = ['start_date', 'end_date', 'category', 'account', 'type']


class TransactionViewSet(ModelViewSet):
    serializer_class = TransactionSerializer
    filterset_class = TransactionFilter
    search_fields = ['label']
    ordering_fields = ['date', 'amount']
    ordering = ['-date']

    def get_queryset(self):
        return Transaction.objects.select_related('account', 'category').all()
