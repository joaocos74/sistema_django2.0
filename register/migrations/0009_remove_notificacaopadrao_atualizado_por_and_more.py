from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('register', '0008_notificacaopadrao')]
    # Move somente o estado; as tabelas e todos os padrões existentes são preservados.
    operations = [migrations.SeparateDatabaseAndState(
        database_operations=[],
        state_operations=[migrations.DeleteModel('AutoTermoPadrao'), migrations.DeleteModel('NotificacaoPadrao')],
    )]
