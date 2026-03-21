import uuid
from django.db import models


class Category(models.Model):
    TYPE_CHOICES = [('income', 'Income'), ('expense', 'Expense')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    color = models.CharField(max_length=30)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name
