import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

PROJECT_HOME = Path(__file__).resolve().parent
LOG_DIR = PROJECT_HOME / 'logs'
LOG_DIR.mkdir(exist_ok=True)


def _write_log(filename, message):
    log_file = LOG_DIR / filename
    with log_file.open('a', encoding='utf-8') as f:
        f.write(f"[{datetime.utcnow().isoformat()}Z] {message}\n")


try:
    if str(PROJECT_HOME) not in sys.path:
        sys.path.insert(0, str(PROJECT_HOME))

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taller_mecanico.settings.prod')
    _write_log('passenger_boot.log', f"Booting WSGI with settings={os.environ.get('DJANGO_SETTINGS_MODULE')}")

    from django.core.wsgi import get_wsgi_application

    application = get_wsgi_application()
    _write_log('passenger_boot.log', 'WSGI application loaded successfully')
except Exception:
    _write_log('passenger_error.log', traceback.format_exc())
    raise
