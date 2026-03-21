import uuid
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models


class Budget(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.PROTECT,
        related_name='budgets',
    )
    account = models.ForeignKey(
        'accounts.Account',
        on_delete=models.CASCADE,
        related_name='budgets',
        null=True,
        blank=True,
    )
    amount_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    start_day = models.PositiveSmallIntegerField()
    rollover = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category__name', 'created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['category', 'account'],
                condition=models.Q(account__isnull=False),
                name='unique_budget_category_account',
            ),
            models.UniqueConstraint(
                fields=['category'],
                condition=models.Q(account__isnull=True),
                name='unique_budget_category_global',
            ),
        ]

    def __str__(self):
        scope = f' [{self.account.name}]' if self.account_id else ' [global]'
        return f'{self.category.name}{scope} — {self.amount_limit} MAD'
