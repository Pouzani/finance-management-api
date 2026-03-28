from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from rest_framework.viewsets import ModelViewSet
from core.mixins import UserOwnedMixin
from accounts.models import Account
from accounts.serializers import AccountSerializer


class AccountViewSet(UserOwnedMixin, ModelViewSet):
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).annotate(
            balance=Coalesce(Sum('transactions__amount'), Value(0), output_field=DecimalField())
        ).order_by('name')
