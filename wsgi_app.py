import os
import sys
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

ERROR_LOG_PATH = os.path.join(BASE_DIR, "wsgi_app_error.log")


def _fallback_application(environ, start_response):
    body = b"TALLER WSGI fallback active. Check wsgi_app_error.log"
    start_response("503 Service Unavailable", [("Content-Type", "text/plain"), ("Content-Length", str(len(body)))])
    return [body]


try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "taller_mecanico.settings.prod")

    from django.core.wsgi import get_wsgi_application

    application = get_wsgi_application()
except Exception:
    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
        f.write("\n=== WSGI startup error ===\n")
        f.write(traceback.format_exc())
    application = _fallback_application
