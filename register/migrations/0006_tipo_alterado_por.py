from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('register', '0005_alter_documento_arquivo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='tipo',
            name='alterado_por',
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL,
                on_delete=django.db.models.deletion.PROTECT,
                null=True,
                blank=True,
                related_name='classificacoes_alteradas',
                verbose_name='Fiscal responsável pela alteração',
            ),
        ),
    ]
