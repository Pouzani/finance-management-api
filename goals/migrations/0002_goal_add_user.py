import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def delete_all_goals(apps, schema_editor):
    Goal = apps.get_model('goals', 'Goal')
    Goal.objects.all().delete()


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('goals', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(delete_all_goals, migrations.RunPython.noop),
        migrations.AddField(
            model_name='goal',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='goals',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
