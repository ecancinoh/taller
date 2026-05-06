# Guia de despliegue de TallerPro en cPanel (CloudLinux Passenger)

Esta guia esta orientada al flujo que funciona de forma estable en hosting cPanel con Setup Python App.

## 1. Requisitos previos

1. Repositorio clonado en el hosting, por ejemplo en /home/usuario/repositories/taller.
2. Base de datos PostgreSQL creada y accesible.
3. Dominio o subdominio ya creado en cPanel.

## 2. Configurar app en Setup Python App

Crear aplicacion con estos valores:

1. Python version: 3.11.
2. Application root: repositories/taller.
3. Application URL: / (o seleccionar el subdominio desde el panel).
4. Application startup file: passenger_wsgi.py.
5. Application entry point: application.

Nota: si tambien usas Application Manager, puede haber conflicto de configuracion. Usar un solo flujo (preferible Setup Python App).

## 3. Variables de entorno

Agregar en Setup Python App (Environment Variables) y/o en .env del servidor:

1. DEBUG=False
2. DJANGO_SETTINGS_MODULE=taller_mecanico.settings.prod
3. SECRET_KEY=tu-clave-segura
4. ALLOWED_HOSTS=tudominio.com,www.tudominio.com
5. CSRF_TRUSTED_ORIGINS="hxxps://tudominio.com,hxxps://www.tudominio.com" (reemplazar hxxps por https)
6. DATABASE_URL=postgres://usuario:password-url-encoded@host:5432/base
7. GEMINI_API_KEY=

Importante: DATABASE_URL debe estar en una sola linea y con password URL-encoded.

## 4. Archivo passenger_wsgi.py

Debe existir en la raiz del proyecto y usar WSGI de Django, no Flask ni manage.py como modulo.

## 5. Instalar dependencias

1. En Setup Python App, agregar requirements.txt en Configuration files.
2. Ejecutar Run Pip Install.

## 6. Migraciones y estaticos

En Execute python script:

1. manage.py migrate
2. manage.py collectstatic --noinput

## 7. Reinicio de app

1. Usar Restart en Setup Python App.
2. Si no toma cambios, crear/actualizar tmp/restart.txt en la raiz de la app.

## 8. Validaciones utiles

1. Probar archivo estatico de prueba (probe.txt) en document root para validar ruteo del dominio.
2. Si probe.txt responde y el sitio da 404, revisar PassengerBaseURI y mapeo de dominio.
3. Verificar que manage.py no haya sido sobreescrito por codigo ajeno (por ejemplo Flask).

## 9. Checklist final

1. Dominio correcto en ALLOWED_HOSTS y CSRF_TRUSTED_ORIGINS (con esquema https).
2. passenger_wsgi.py apuntando a taller_mecanico.settings.prod.
3. Dependencias instaladas en el virtualenv de la app activa.
4. Migraciones y collectstatic ejecutados con exito.
