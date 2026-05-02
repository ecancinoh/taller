# TallerPro — Contexto para agentes IA

Sistema web de gestión para taller mecánico automotriz. Django 5 + PostgreSQL + SB Admin 2. Mobile-first.

## Comandos esenciales

```bash
# Activar entorno
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac

# Desarrollo
python manage.py runserver
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic

# Settings: DJANGO_SETTINGS_MODULE=taller_mecanico.settings.dev (por defecto en manage.py)
```

## Estructura de apps (`apps/`)

| App | Responsabilidad |
|-----|----------------|
| `core` | `TimeStampedModel`, mixins de roles, dashboard, utilidades |
| `accounts` | `CustomUser` (roles: ADMIN/MECHANIC), login/logout |
| `customers` | CRUD de clientes, importación CSV/VCF |
| `vehicles` | CRUD de vehículos vinculados a clientes |
| `service_orders` | Órdenes de servicio, repuestos, mano de obra, fotos, ShareToken |
| `diagnostics` | Integración Gemini (AIDiagnosticRequest) |
| `shared_views` | Vista pública sin autenticación, acceso por UUID token |

## Modelo de datos clave

- `CustomUser.role`: `ADMIN` o `MECHANIC` — verificar con `user.is_admin` / `user.is_mechanic`
- `ServiceOrder` → `Vehicle` → `Customer` (cadena de FK)
- `ShareToken.token`: UUID v4, acceso público en `/p/orden/<uuid>/`
- `ServiceOrderPhoto.is_public`: controla si la foto aparece en vista pública
- `ServiceOrder.internal_notes` + datos financieros (precios, costos): **nunca exponer en vista pública ni a Mecánico**

## Convenciones de código

- Todas las vistas heredan de `MechanicRequiredMixin` (cualquier usuario) o `AdminRequiredMixin` (solo admin)
- Modelos heredan de `TimeStampedModel` (abstract) para `created_at`/`updated_at`
- Formularios con `attrs={'class': 'form-control'}` para compatibilidad Bootstrap
- Templates organizados en `templates/<app_name>/`
- Partials reutilizables en `templates/partials/`

## Seguridad — reglas críticas

- Datos financieros (`unit_price`, `unit_cost`, `subtotal`, `grand_total`, `internal_notes`) → **solo visibles si `user.is_admin`**
- `shared_views` no requiere login — **nunca pasar costos ni notas internas al contexto de esa view**
- CSRF siempre activo — formularios POST siempre con `{% csrf_token %}`

## Templates y UI

- `templates/base.html`: layout SB Admin 2 completo (sidebar + topbar + content)
- Sidebar en `templates/partials/sidebar.html`: navegación condicional por rol
- Topbar en `templates/partials/topbar.html`: acceso rápido "Nueva orden", menú usuario
- Badge de estado en `templates/partials/status_badge.html`
- Bootstrap 5 + SB Admin 2 via CDN — `static/css/custom.css` para overrides
- Mobile-first: tarjetas en `d-md-none`, tablas en `d-none d-md-block`

## Variables de entorno (`.env`)

- `DATABASE_URL` — PostgreSQL connection string
- `SECRET_KEY` — clave Django
- `GEMINI_API_KEY` — para integración IA (opcional en dev)
- Ver `.env.example` para plantilla completa

## URLs

```
/                      → redirect al dashboard
/accounts/login/       → login
/accounts/logout/      → logout (POST)
/dashboard/            → dashboard (diferenciado por rol)
/clientes/             → CRUD clientes
/vehiculos/            → CRUD vehículos
/ordenes/              → CRUD órdenes de servicio
/p/orden/<uuid>/       → vista pública compartible (sin auth)
/admin/                → Django admin
```

## Próximos módulos a implementar

- **CRUD repuestos/labor inline** dentro de ServiceOrder detail
- **Upload de fotos** con AJAX o htmx en orden de servicio
- **Importación CSV/VCF** en `customers` app
- **Vista diagnóstico IA** usando `google-generativeai` con `GEMINI_API_KEY`
- **Generación de ShareToken** desde detail de orden (botón "Compartir")
- **CRUD usuarios internos** (solo Admin) con activar/desactivar
