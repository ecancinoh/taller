# TallerPro 🔧

Sistema web de gestion para taller mecanico automotriz. Construido con Django 5 + PostgreSQL + Bootstrap 5 + SB Admin 2. Mobile-first, responsive y listo para despliegue.

## Características

- **Gestión de clientes** — CRUD completo con búsqueda y paginación
- **Gestión de vehículos** — Vinculados a clientes, historial completo de servicios
- **Órdenes de servicio** — Flujo completo con estados, repuestos, mano de obra y fotos
- **Control de acceso por roles** — Admin y Mecanico con vistas diferenciadas
- **Vista pública compartible** — Enlace por UUID sin necesidad de login para el cliente
- **Integración Gemini AI** — Asistente de diagnóstico (requiere API key)
- **Gestion financiera** — Dashboard de ingresos, costos, gastos y ganancia neta
- **Importación CSV/VCF** — Importar contactos desde Excel o celular

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Django 5.1.4 + Python 3.11+ |
| Base de datos | PostgreSQL 15+ |
| Frontend | Bootstrap 5 + SB Admin 2 (CDN) |
| Autenticación | Django auth integrado con roles personalizados |
| IA | Google Gemini 1.5 Flash |
| Estáticos | WhiteNoise |
| Entorno | django-environ |
| App server (prod) | Gunicorn |

## Estructura del proyecto

```
taller/
├── manage.py
├── requirements.txt
├── .env.example
├── AGENTS.md                    # Contexto para agentes IA
├── taller_mecanico/
│   ├── settings/
│   │   ├── base.py              # Settings compartidos
│   │   ├── dev.py               # Desarrollo local
│   │   └── prod.py              # Producción
│   └── urls.py
├── apps/
│   ├── core/                    # TimeStampedModel, mixins, dashboard
│   ├── accounts/                # CustomUser (ADMIN/MECHANIC)
│   ├── customers/               # CRUD clientes
│   ├── vehicles/                # CRUD vehículos
│   ├── service_orders/          # Órdenes de servicio
│   ├── diagnostics/             # Integración Gemini AI
│   └── shared_views/            # Vista pública por token UUID
├── templates/
│   ├── base.html                # Layout SB Admin 2
│   ├── partials/                # sidebar, topbar, status_badge
│   ├── registration/            # login
│   ├── core/                    # dashboard
│   ├── customers/
│   ├── vehicles/
│   ├── service_orders/
│   └── shared_views/
└── static/
    └── css/custom.css
```

## Requisitos previos

- Python 3.10+
- PostgreSQL 13+
- Git

## Instalación local

### 1. Clonar el repositorio

```bash
git clone https://github.com/ecancinoh/taller.git
cd taller
```

### 2. Crear entorno virtual e instalar dependencias

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` con tus valores:

```env
DEBUG=True
SECRET_KEY=tu-clave-secreta-muy-larga
ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_URL=postgres://usuario:contraseña@localhost:5432/taller_mecanico_db

GEMINI_API_KEY=tu-api-key-de-google-ai  # Opcional en dev

DJANGO_SETTINGS_MODULE=taller_mecanico.settings.dev
```

### 4. Crear la base de datos PostgreSQL

```sql
-- En psql o pgAdmin:
CREATE DATABASE taller_mecanico_db;
```

### 5. Aplicar migraciones

```bash
python manage.py migrate
```

### 6. Crear superusuario (Admin)

```bash
python manage.py createsuperuser
```

### 7. Ejecutar el servidor de desarrollo

```bash
python manage.py runserver
```

Acceder a **http://127.0.0.1:8000/**

## URLs principales

| URL | Descripción | Acceso |
|-----|-------------|--------|
| `/` | Redirige al dashboard | Autenticado |
| `/accounts/login/` | Inicio de sesión | Público |
| `/dashboard/` | Dashboard (diferenciado por rol) | Autenticado |
| `/clientes/` | Gestión de clientes | Admin + Mecánico |
| `/vehiculos/` | Gestión de vehículos | Admin + Mecánico |
| `/ordenes/` | Órdenes de servicio | Admin + Mecánico |
| `/p/orden/<uuid>/` | Vista pública compartible | Sin login |
| `/admin/` | Django admin | Solo Admin |

## Roles de usuario

### Admin
- Ve y gestiona todos los clientes, vehículos y órdenes
- Accede a datos financieros (precios, costos, margen)
- Ve notas internas de cada orden
- Puede crear y gestionar usuarios mecánicos

### Mecánico
- Ve solo sus órdenes asignadas
- No ve precios, costos ni notas internas
- Puede actualizar estado y observaciones de sus órdenes

## Modelo de datos

```
CustomUser (ADMIN|MECHANIC)
    │
    └──> ServiceOrder ──> Vehicle ──> Customer
              │
              ├──> ServiceOrderPart
              ├──> ServiceOrderLabor
              ├──> ServiceOrderPhoto (is_public: bool)
              └──> ShareToken (UUID) ──> Vista pública /p/orden/<uuid>/

AIDiagnosticRequest ──> ServiceOrder
```

## Estados de orden de servicio

| Estado | Color | Descripción |
|--------|-------|-------------|
| `PENDING` | Amarillo | Orden creada, sin iniciar |
| `IN_PROGRESS` | Azul | Vehículo en reparación activa |
| `WAITING_PARTS` | Naranja | Esperando repuestos |
| `DONE` | Verde | Reparación completada |
| `DELIVERED` | Gris | Vehículo entregado al cliente |
| `CANCELLED` | Rojo | Orden cancelada |

## Seguridad

- Datos financieros y notas internas **nunca** se exponen al mecánico ni en la vista pública
- La vista pública `/p/orden/<uuid>/` no requiere autenticación pero solo muestra información básica del servicio, sin costos
- CSRF activo en todos los formularios POST
- Variables sensibles en `.env` (excluido del repositorio)

## Despliegue en hosting (produccion)

### 1. Variables de entorno

Configura estas variables en tu hosting:

```env
DEBUG=False
DJANGO_SETTINGS_MODULE=taller_mecanico.settings.prod
SECRET_KEY=tu-clave-secreta-segura

ALLOWED_HOSTS=tudominio.com,www.tudominio.com
CSRF_TRUSTED_ORIGINS=https://tudominio.com,https://www.tudominio.com

DATABASE_URL=postgres://usuario:password@host:5432/nombre_db

# Opcional (si usas diagnostico IA)
GEMINI_API_KEY=tu-api-key
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Migraciones y estaticos

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### 4. Crear superusuario

```bash
python manage.py createsuperuser
```

### 5. Iniciar aplicacion con Gunicorn

```bash
gunicorn taller_mecanico.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

### 6. Reverse proxy (Nginx recomendado)

- Apunta el dominio al servidor.
- Configura proxy hacia Gunicorn.
- Sirve /static y /media desde el sistema de archivos.
- Habilita HTTPS.

Nota: si tu hosting no envia cabeceras HTTPS correctamente, ajusta SECURE_SSL_REDIRECT en variables de entorno.

## Contribuir

1. Fork el repositorio
2. Crear rama: `git checkout -b feature/nombre-feature`
3. Commit: `git commit -m 'feat: descripción del cambio'`
4. Push: `git push origin feature/nombre-feature`
5. Abrir Pull Request

## Licencia

MIT — Ver [LICENSE](LICENSE) para detalles.

---

Desarrollado por [Emanuel Cancino](https://github.com/ecancinoh)
