from decimal import Decimal
from rest_framework import serializers
from transactions.models import Transaction
from categories.serializers import CategorySerializer
from accounts.models import Account


class TransactionSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source='category', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'label', 'amount', 'date', 'type',
            'account', 'account_name',
            'category', 'category_detail',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'account_name', 'category_detail']

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            fields['account'].queryset = Account.objects.filter(user=request.user)
        return fields

    def validate(self, data):
        amount = data.get('amount')
        type_ = data.get('type')
        if amount is None or type_ is None:
            return data
        if type_ == 'expense' and amount > Decimal('0'):
            raise serializers.ValidationError(
                {'amount': 'Expense amount must be negative.'}
            )
        if type_ == 'income' and amount < Decimal('0'):
            raise serializers.ValidationError(
                {'amount': 'Income amount must be positive.'}
            )
        return data
