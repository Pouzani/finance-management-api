import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def delete_all_accounts(apps, schema_editor):
    Account = apps.get_model('accounts', 'Account')
    Account.objects.all().delete()


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(delete_all_accounts, migrations.RunPython.noop),
        migrations.AddField(
            model_name='account',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='accounts',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
