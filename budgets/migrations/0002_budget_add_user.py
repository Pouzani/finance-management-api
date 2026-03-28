import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def delete_all_budgets(apps, schema_editor):
    Budget = apps.get_model('budgets', 'Budget')
    Budget.objects.all().delete()


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('budgets', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(delete_all_budgets, migrations.RunPython.noop),
        migrations.AddField(
            model_name='budget',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='budgets',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RemoveConstraint(
            model_name='budget',
            name='unique_budget_category_account',
        ),
        migrations.RemoveConstraint(
            model_name='budget',
            name='unique_budget_category_global',
        ),
        migrations.AddConstraint(
            model_name='budget',
            constraint=models.UniqueConstraint(
                condition=models.Q(account__isnull=False),
                fields=['user', 'category', 'account'],
                name='unique_budget_user_category_account',
            ),
        ),
        migrations.AddConstraint(
            model_name='budget',
            constraint=models.UniqueConstraint(
                condition=models.Q(account__isnull=True),
                fields=['user', 'category'],
                name='unique_budget_user_category_global',
            ),
        ),
    ]
