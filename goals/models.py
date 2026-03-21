import uuid
from django.db import models


class Goal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=500)
    current = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    target = models.DecimalField(max_digits=12, decimal_places=2)
    icon = models.CharField(max_length=100)
    color = models.CharField(max_length=30)

    class Meta:
        ordering = ['label']

    def __str__(self):
        return self.label
