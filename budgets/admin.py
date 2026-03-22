from django.contrib import admin

from .models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'category', 'account_display', 'amount_limit', 'start_day', 'rollover')
    list_filter = ('rollover', 'account', 'category')
    readonly_fields = ('id', 'created_at', 'updated_at')

    @admin.display(description='Scope')
    def account_display(self, obj):
        return obj.account.name if obj.account_id else 'global'
