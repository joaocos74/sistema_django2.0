"""Entrada do servidor Windows, executada pelo Agendador de Tarefas."""
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
(ROOT / 'logs').mkdir(exist_ok=True)
handler = RotatingFileHandler(ROOT / 'logs' / 'servidor.log', maxBytes=2_000_000, backupCount=5, encoding='utf-8')
logging.basicConfig(level=logging.INFO, handlers=[handler], format='%(asctime)s %(levelname)s %(message)s')


class LogStream:
    def write(self, value):
        if value.strip():
            logging.getLogger('servidor').warning(value.strip())

    def flush(self):
        pass


sys.stdout = sys.stderr = LogStream()


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
    from app.wsgi import application
    from django.db import connection
    from waitress import serve

    for tentativa in range(60):
        try:
            connection.ensure_connection()
            connection.close()
            break
        except Exception:
            if tentativa == 59:
                raise
            time.sleep(2)
    logging.info('Iniciando sistema na porta 8282.')
    serve(application, host='0.0.0.0', port=8282, threads=6, channel_timeout=120,
          max_request_body_size=30 * 1024 * 1024)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logging.exception('Servidor encerrado com erro; o Agendador tentará reiniciar.')
        sys.exit(1)
