from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('label', 'amount', 'type', 'account', 'category', 'date')
    search_fields = ('label',)
    list_filter = [
        'type',
        ('category', admin.RelatedOnlyFieldListFilter),
        ('account', admin.RelatedOnlyFieldListFilter),
    ]
    date_hierarchy = 'date'
    ordering = ('-date',)
    readonly_fields = ('id', 'created_at', 'updated_at')
