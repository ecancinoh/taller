# Guia de despliegue de TallerPro

Esta guia te deja el sistema listo para subir a un hosting Linux con Python y PostgreSQL.

## 1. Preparar servidor

1. Instala Python 3.11+ y PostgreSQL.
2. Crea la base de datos y usuario.
3. Clona el repositorio en el servidor.

## 2. Configurar entorno

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Configurar variables de entorno

Crea tu archivo .env en raiz del proyecto:

```env
DEBUG=False
DJANGO_SETTINGS_MODULE=taller_mecanico.settings.prod
SECRET_KEY=tu-clave-larga-y-segura

ALLOWED_HOSTS=tudominio.com,www.tudominio.com
CSRF_TRUSTED_ORIGINS=https://tudominio.com,https://www.tudominio.com

DATABASE_URL=postgres://usuario:password@host:5432/taller_mecanico_db
GEMINI_API_KEY=
```

## 4. Aplicar migraciones y estaticos

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```

## 5. Crear usuario administrador

```bash
python manage.py createsuperuser
```

## 6. Levantar con Gunicorn

```bash
gunicorn taller_mecanico.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

## 7. Configurar Nginx (resumen)

1. Proxy pass al puerto de Gunicorn.
2. Alias para estaticos y media.
3. Certificado TLS (Let's Encrypt).

## 8. Checklist final

- DEBUG en False.
- Dominio en ALLOWED_HOSTS.
- CSRF_TRUSTED_ORIGINS con https.
- collectstatic ejecutado.
- Base de datos accesible desde app.
- Respaldos programados de PostgreSQL.

## 9. Comandos utiles

```bash
python manage.py check --deploy
python manage.py showmigrations
python manage.py createsuperuser
```
