from decimal import Decimal
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from rest_framework import serializers
from accounts.models import Account


class AccountSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = ['id', 'name', 'balance', 'created_at']
        read_only_fields = ['id', 'created_at', 'balance']

    def get_balance(self, obj):
        if hasattr(obj, 'balance'):
            return obj.balance
        result = Account.objects.filter(pk=obj.pk).annotate(
            balance=Coalesce(Sum('transactions__amount'), Value(0), output_field=DecimalField())
        ).values_list('balance', flat=True).first()
        return result or Decimal('0')
