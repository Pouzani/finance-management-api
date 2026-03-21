from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from rest_framework.viewsets import ModelViewSet
from accounts.models import Account
from accounts.serializers import AccountSerializer


class AccountViewSet(ModelViewSet):
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.annotate(
            balance=Coalesce(Sum('transactions__amount'), Value(0), output_field=DecimalField())
        ).order_by('name')
