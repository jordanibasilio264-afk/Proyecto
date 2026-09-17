# AGENTS.md - Clinica Django Project

## Quickstart

- **Activate venv**: `.\.venv-1\Scripts\activate`
- **Run dev server**: `python manage.py runserver`
- **Create migrations**: `python manage.py makemigrations`
- **Apply migrations**: `python manage.py migrate`

## Database

- `.env` contains `DB_User`, `DB_Name`, `DB_Password` — **never commit** (gitignored)
- Settings default to SQLite; `.env` overrides for MySQL/PostgreSQL
- If switching DB engines, verify `DATABASES` in `mysite/settings.py`

## Apps

Six apps are installed (in `mysite/settings.py`):
- `apps.usuarios` — user management
- `apps.Reportes` — reports
- `apps.pagos` — payments
- `apps.Citas` — appointments
- `apps.Notificaciones` — notifications
- `apps.SegurosMedicos` — insurance

Each app has its own `migrations/`, `models.py`, `views.py`, `urls.py`, and `tests.py`.

## URLs

Root `mysite/urls.py` routes under prefixes:
- `/admin/`
- `/usuarios/`
- `/reportes/`
- `/pagos/`
- `/citas/`
- `/notificaciones/`
- `/seguros/`

## Testing

- Tests live in each app's `tests.py` (Django `TestCase`)
- Run all tests: `python manage.py test`
- Run single app: `python manage.py test apps.usuarios`

## Gotchas

- `.env` is gitignored — copy settings if you need DB access
- `SECRET_KEY` is hardcoded in `settings.py` — change for production
- Debug mode is `DEBUG = True` — disable for production