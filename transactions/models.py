import uuid
from django.db import models


class Transaction(models.Model):
    TYPE_CHOICES = [('income', 'Income'), ('expense', 'Expense')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=500)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    account = models.ForeignKey(
        'accounts.Account', on_delete=models.CASCADE, related_name='transactions'
    )
    category = models.ForeignKey(
        'categories.Category', on_delete=models.SET_NULL, null=True, related_name='transactions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['type']),
            models.Index(fields=['account']),
        ]

    def __str__(self):
        return f"{self.label} ({self.amount})"
