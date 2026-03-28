import uuid
from django.conf import settings
from django.db import models


class Goal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='goals',
    )
    label = models.CharField(max_length=500)
    current = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    target = models.DecimalField(max_digits=12, decimal_places=2)
    icon = models.CharField(max_length=100)
    color = models.CharField(max_length=30)

    class Meta:
        ordering = ['label']

    def __str__(self):
        return self.label
