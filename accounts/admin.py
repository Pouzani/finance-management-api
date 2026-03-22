from django.contrib import admin
from django.db.models import Sum, Count, Value, DecimalField
from django.db.models.functions import Coalesce

from transactions.models import Transaction
from .models import Account


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    max_num = 0  # read-only: no new transactions can be added via inline
    fields = ('label', 'amount', 'type', 'category', 'date')
    readonly_fields = ('label', 'amount', 'type', 'category', 'date')
    ordering = ('-date',)

    # Note: Django's inline get_queryset() receives no reference to the parent object,
    # so limiting to "last 10" per-account is not possible without a complex subquery.
    # All transactions for the account are shown, ordered most-recent first.


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'balance', 'transaction_count', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('id', 'created_at', 'balance', 'transaction_count')
    inlines = [TransactionInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _balance=Coalesce(
                Sum('transactions__amount'),
                Value(0),
                output_field=DecimalField(),
            ),
            _transaction_count=Count('transactions'),
        )

    @admin.display(description='Balance', ordering='_balance')
    def balance(self, obj):
        return obj._balance

    @admin.display(description='Transactions', ordering='_transaction_count')
    def transaction_count(self, obj):
        return obj._transaction_count
