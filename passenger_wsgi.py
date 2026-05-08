import os
import sys
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

ERROR_LOG_PATH = os.path.join(BASE_DIR, "passenger_wsgi_error.log")


def _write_probe(message):
    for path in [
        os.path.join(BASE_DIR, "tmp", "wsgi_probe.log"),
        os.path.join(BASE_DIR, "wsgi_probe.log"),
        "/tmp/taller_wsgi_probe.log",
    ]:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(message + "\n")
            break
        except Exception:
            continue


def _fallback_application(environ, start_response):
    body = b"TALLER WSGI fallback active. Check passenger_wsgi_error.log"
    start_response("503 Service Unavailable", [("Content-Type", "text/plain"), ("Content-Length", str(len(body)))])
    return [body]


try:
    _write_probe("passenger_wsgi.py loaded")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "taller_mecanico.settings.prod")

    from django.core.wsgi import get_wsgi_application

    application = get_wsgi_application()
    _write_probe("Django application loaded OK")
except Exception:
    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
        f.write("\n=== Passenger WSGI startup error ===\n")
        f.write(traceback.format_exc())
    _write_probe("passenger_wsgi.py failed; fallback active")
    application = _fallback_application
