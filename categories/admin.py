import re
from django.contrib import admin
from django.db.models import Count
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .models import Category

_SAFE_COLOR_RE = re.compile(
    r'^#[0-9a-fA-F]{3}$|^#[0-9a-fA-F]{6}$|^[a-zA-Z]+$|^rgb\([\d\s,]+\)$'
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'color_preview', 'transaction_count')
    search_fields = ('name',)
    list_filter = ('type',)
    readonly_fields = ('id', 'color_preview', 'transaction_count')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _transaction_count=Count('transactions'),
        )

    @admin.display(description='Color')
    def color_preview(self, obj):
        color = obj.color if _SAFE_COLOR_RE.match(obj.color or '') else '#cccccc'
        return mark_safe(
            f'<span style="display:inline-block;width:16px;height:16px;'
            f'background:{color};border-radius:3px;border:1px solid #ccc;"></span>'
            f' {escape(obj.color)}'
        )

    @admin.display(description='Transactions', ordering='_transaction_count')
    def transaction_count(self, obj):
        return obj._transaction_count
