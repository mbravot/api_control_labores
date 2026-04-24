# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env from template
cp .env.example .env  # then fill in DB_PASSWORD and SECRET_KEY

# Run development server (auto-reload)
uvicorn app.main:app --reload

# Generate SECRET_KEY
openssl rand -hex 32
```

API docs available at `http://localhost:8000/docs` when running.

No test suite exists yet. To add one: `pip install pytest pytest-asyncio httpx` and create a `tests/` directory using FastAPI's `TestClient` or `httpx.AsyncClient`.

## Architecture

**Stack:** Python 3.10, FastAPI, SQLAlchemy 2.0 async, aiomysql (MySQL 8), Pydantic v2, JWT (python-jose + passlib bcrypt).

**Layered structure:**
- `app/core/` — cross-cutting: config (pydantic-settings from `.env`), async DB engine/session, JWT security, dependency injection
- `app/models/` — SQLAlchemy ORM entities
- `app/schemas/` — Pydantic DTOs (request/response)
- `app/routers/` — FastAPI route handlers (business logic lives here)

**Multi-tenant hierarchy:** `Empresa → Campo → Usuario`. A user belongs to one empresa and accesses multiple campos via the `usuario_campo` join table.

**Database:** Remote MySQL at `186.64.118.105:3306`, database `agrico24_control_labores`. Connection pool: size=10, max_overflow=20.

**Auth:** Bearer JWT, 8-hour expiration. Token payload: `{"sub": usuario_id}`. Three roles: `admin_empresa`, `supervisor`, `consultor`.

**Activity workflow:** `Actividad` state machine: `creada(1) → revisada(2) → aprobada(3) → finalizada(4)`. State can only advance, never go back.

**Rendimiento types:** `individual` (one yield record per worker) or `grupal` (one total for the group).

## Key Conventions

- **Session management:** `get_db()` auto-commits on success / auto-rolls back on exception. Routers use `await db.flush()` + `await db.refresh()` — never `await db.commit()` directly.
- **Field access guard:** Call `verify_campo_access(campo_id, current_user, db)` manually (not via `Depends`) at the start of any operation touching a campo, because it needs `db` as a direct parameter.
- **Partial updates (PATCH):** Use `model_dump(exclude_none=True)` to apply only provided fields.
- **Eager loading:** Use `selectinload()` for detail endpoints to avoid N+1 queries. List endpoints load only the base entity + estado.
- **Error messages:** All `HTTPException` `detail` strings are in Spanish.
- **Router prefixes:** All routes are registered under `/api/v1` in `main.py`.

## Business Rules to Enforce

- Workers (`trabajador`) assigned to an activity must match the activity's `tipo_personal` (propio/contratista).
- An activity can only be deleted if `estado_id == 1` (creada).
- A worker can only be removed from an activity if no `rendimiento` exists for them in that activity.
- One `rendimiento` per worker per activity (check for duplicates on create).
- Rendimientos can only be deleted if the activity `estado_id` is 1 or 2.
- Bulk rendimiento create (`POST /rendimientos/bulk`) is the primary mobile app use case — all records must reference the same `actividad_id`.
