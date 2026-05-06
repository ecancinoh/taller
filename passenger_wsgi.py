import os
import sys


BASE_DIR = os.path.dirname(__file__)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taller_mecanico.settings.prod')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
