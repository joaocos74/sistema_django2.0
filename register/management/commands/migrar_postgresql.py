"""Transfere o SQLite para um PostgreSQL vazio sem apagar o banco original."""
import json
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connections, transaction


class Command(BaseCommand):
    help = 'Cria backup do SQLite e transfere seus dados para um PostgreSQL vazio.'

    def add_arguments(self, parser):
        parser.add_argument('--prepare-only', action='store_true', help='Somente backup e exportação, sem alterar o destino.')

    def handle(self, *args, **options):
        origem = settings.BASE_DIR / 'db.sqlite3'
        if not origem.is_file():
            raise CommandError('db.sqlite3 não encontrado.')
        if not options['prepare_only'] and connections['default'].vendor != 'postgresql':
            raise CommandError('Configure DB_ENGINE=postgresql no .env. O SQLite não será alterado.')
        pasta = settings.BASE_DIR / 'backups' / datetime.now().strftime('migracao_%Y%m%d_%H%M%S_%f')
        pasta.mkdir(parents=True)
        backup = pasta / 'origem.sqlite3'
        with sqlite3.connect(origem.as_uri() + '?mode=ro', uri=True) as fonte:
            with sqlite3.connect(backup) as destino:
                fonte.backup(destino)
        # Exporta a cópia estável, não o arquivo de trabalho.
        connections.databases['origem_sqlite'] = {
            'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(backup),
            'OPTIONS': {}, 'TIME_ZONE': None, 'CONN_MAX_AGE': 0, 'CONN_HEALTH_CHECKS': False,
            'AUTOCOMMIT': True, 'ATOMIC_REQUESTS': False, 'USER': '', 'PASSWORD': '',
            'HOST': '', 'PORT': '', 'TEST': {},
        }
        fixture = pasta / 'dados.json'
        try:
            call_command('dumpdata', database='origem_sqlite', natural_foreign=True,
                         exclude=['contenttypes', 'auth.permission'], output=str(fixture), verbosity=0)
        finally:
            connections['origem_sqlite'].close()
        self.stdout.write(f'Backup e dados exportados: {pasta}')
        if options['prepare_only']:
            self.stdout.write('Nenhum dado foi transferido. Preserve também media/ e arquivos_privados/.')
            return
        existentes = set(connections['default'].introspection.table_names())
        modelos = [m for m in apps.get_models() if m._meta.label_lower not in ('contenttypes.contenttype', 'auth.permission')]
        for model in modelos:
            if model._meta.db_table in existentes and model.objects.exists():
                raise CommandError('O PostgreSQL de destino já contém dados. Use um banco vazio; nada foi sobrescrito.')
        call_command('migrate', database='default', interactive=False)
        with fixture.open(encoding='utf-8') as entrada:
            esperados = Counter(item['model'] for item in json.load(entrada))
        with transaction.atomic():
            call_command('loaddata', str(fixture), database='default', verbosity=0)
            for model in modelos:
                esperado = esperados.get(model._meta.label_lower, 0)
                if model.objects.count() != esperado:
                    raise CommandError(f'Contagem divergente em {model._meta.label}. Importação revertida.')
        self.stdout.write(self.style.SUCCESS('Migração concluída e contagens conferidas. SQLite original preservado.'))
