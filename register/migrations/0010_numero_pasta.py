from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


def preservar_numeracao(apps, schema_editor):
    Estabelecimento = apps.get_model('register', 'Estabelecimento')
    Sequencia = apps.get_model('register', 'SequenciaPasta')
    Historico = apps.get_model('register', 'HistoricoPasta')
    banco = schema_editor.connection.alias
    Estabelecimento.objects.using(banco).update(numero_pasta=models.F('id'))
    maior = Estabelecimento.objects.using(banco).aggregate(valor=models.Max('id'))['valor'] or 0
    Sequencia.objects.using(banco).update_or_create(pk=1, defaults={'ultimo_numero': maior})
    lote = []
    for est in Estabelecimento.objects.using(banco).iterator(chunk_size=1000):
        lote.append(Historico(estabelecimento_id=est.pk, numero_novo=est.numero_pasta, inativo_novo=est.status))
        if len(lote) == 1000:
            Historico.objects.using(banco).bulk_create(lote)
            lote = []
    if lote:
        Historico.objects.using(banco).bulk_create(lote)


class Migration(migrations.Migration):
    dependencies = [
        ('register', '0009_remove_notificacaopadrao_atualizado_por_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(model_name='estabelecimento', name='numero_pasta',
            field=models.PositiveBigIntegerField(null=True, blank=True, verbose_name='Número da pasta',
                validators=[MinValueValidator(1)],
                help_text='Identificação da pasta física. Em novos cadastros, deixe vazio para numerar automaticamente.')),
        migrations.CreateModel(name='SequenciaPasta', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('ultimo_numero', models.PositiveBigIntegerField(default=0)),
        ]),
        migrations.CreateModel(name='HistoricoPasta', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('numero_anterior', models.PositiveBigIntegerField(null=True, blank=True)),
            ('numero_novo', models.PositiveBigIntegerField()),
            ('inativo_anterior', models.BooleanField(null=True, blank=True)),
            ('inativo_novo', models.BooleanField()),
            ('criado_em', models.DateTimeField(auto_now_add=True)),
            ('alterado_por', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ('estabelecimento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historico_pastas', to='register.estabelecimento')),
        ], options={'ordering': ('-criado_em', '-pk'), 'verbose_name': 'histórico de pasta', 'verbose_name_plural': 'históricos de pastas'}),
        migrations.RunPython(preservar_numeracao, migrations.RunPython.noop),
        migrations.AlterField(model_name='estabelecimento', name='numero_pasta',
            field=models.PositiveBigIntegerField(blank=True, verbose_name='Número da pasta',
                validators=[MinValueValidator(1)],
                help_text='Identificação da pasta física. Em novos cadastros, deixe vazio para numerar automaticamente.')),
        migrations.AlterModelOptions(name='estabelecimento', options={'ordering': ('numero_pasta', 'pk')}),
        migrations.AddConstraint(model_name='estabelecimento', constraint=models.UniqueConstraint(
            fields=('numero_pasta',), condition=models.Q(status=False), name='pasta_unica_estabelecimento_ativo')),
        migrations.AddConstraint(model_name='estabelecimento', constraint=models.CheckConstraint(
            condition=models.Q(numero_pasta__gte=1), name='pasta_numero_positivo')),
    ]
