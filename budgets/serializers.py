from rest_framework import serializers
from accounts.models import Account
from categories.models import Category
from budgets.models import Budget
from budgets.utils import current_period, compute_spent


class BudgetSerializer(serializers.ModelSerializer):
    # Write: accept UUID; Read: overridden in to_representation
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(type='expense')
    )
    account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(),
        required=False,
        allow_null=True,
        default=None,
    )

    # Computed read-only fields
    period = serializers.SerializerMethodField()
    spent = serializers.SerializerMethodField()
    remaining = serializers.SerializerMethodField()
    utilization_pct = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            'id', 'category', 'account',
            'amount_limit', 'start_day', 'rollover',
            'period', 'spent', 'remaining', 'utilization_pct',
        ]
        read_only_fields = ['id', 'period', 'spent', 'remaining', 'utilization_pct']

    def validate_category(self, value):
        if value.type != 'expense':
            raise serializers.ValidationError(
                'Only expense categories can have a budget.'
            )
        return value

    def validate_start_day(self, value):
        if not (1 <= value <= 28):
            raise serializers.ValidationError(
                'start_day must be between 1 and 28.'
            )
        return value

    def validate(self, data):
        category = data.get('category', getattr(self.instance, 'category', None))
        account = data.get('account', getattr(self.instance, 'account', None))
        instance_id = self.instance.id if self.instance else None

        # Use account__isnull for the global case — PostgreSQL treats NULL != NULL,
        # so `filter(account=None)` would silently match nothing on Postgres.
        if account is None:
            qs = Budget.objects.filter(category=category, account__isnull=True)
        else:
            qs = Budget.objects.filter(category=category, account=account)
        if instance_id:
            qs = qs.exclude(id=instance_id)
        if qs.exists():
            scope = 'account-scoped' if account else 'global'
            raise serializers.ValidationError(
                f'A {scope} budget for this category already exists.'
            )
        return data

    def _get_metrics(self, obj):
        """Compute period and spent once per object to avoid repeated queries."""
        cache_key = '_budget_serializer_metrics'
        if not hasattr(obj, cache_key):
            start, end = current_period(obj.start_day)
            spent = compute_spent(obj, start, end)
            setattr(obj, cache_key, {'start': start, 'end': end, 'spent': spent})
        return getattr(obj, cache_key)

    def get_period(self, obj):
        m = self._get_metrics(obj)
        return {'start': m['start'].isoformat(), 'end': m['end'].isoformat()}

    def get_spent(self, obj):
        m = self._get_metrics(obj)
        return str(m['spent'])

    def get_remaining(self, obj):
        m = self._get_metrics(obj)
        return str(obj.amount_limit - m['spent'])

    def get_utilization_pct(self, obj):
        if obj.amount_limit <= 0:
            return 0.0
        m = self._get_metrics(obj)
        return round(float(m['spent'] / obj.amount_limit) * 100, 1)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Replace FK PKs with nested objects on read
        data['category'] = {
            'id': str(instance.category.id),
            'name': instance.category.name,
            'color': instance.category.color,
            'type': instance.category.type,
        }
        if instance.account:
            data['account'] = {
                'id': str(instance.account.id),
                'name': instance.account.name,
            }
        else:
            data['account'] = None
        return data
