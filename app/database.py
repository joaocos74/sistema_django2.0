"""Configuração de banco; SQLite permanece disponível apenas para transição e testes."""
import os
from django.core.exceptions import ImproperlyConfigured


def database_config(base_dir):
    engine = os.environ.get('DB_ENGINE', 'postgresql').lower()
    if engine == 'sqlite':
        return {'ENGINE': 'django.db.backends.sqlite3', 'NAME': base_dir / 'db.sqlite3'}
    if engine != 'postgresql':
        raise ImproperlyConfigured('DB_ENGINE deve ser postgresql ou sqlite.')
    if not os.environ.get('DB_NAME') or not os.environ.get('DB_USER'):
        raise ImproperlyConfigured('Configure DB_NAME e DB_USER no arquivo .env para usar PostgreSQL.')
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {'connect_timeout': 10, 'sslmode': os.environ.get('DB_SSLMODE', 'prefer')},
    }
