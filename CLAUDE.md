# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server (auto-reload on changes)
uvicorn main:app --reload

# Access the app
# http://localhost:8000
```

There is no test suite or linter configured. The app is a single-file FastAPI backend with a static HTML frontend.

## Architecture

This is a financial management system ("financeiro") for a gym ("academia") named **Body Fitness**. It is a monolithic FastAPI application deployed on Railway with a pure HTML/JS frontend.

### Key files

- **`main.py`** — The entire backend: FastAPI app, all API routes, auth, report generation (PDF/Excel), and the scheduled notification jobs. ~1000 lines.
- **`database.py`** — Database connection abstraction: returns either a PostgreSQL connection (production on Railway) or SQLite (local dev). Also defines `init_postgres_tables()` for PostgreSQL schema creation.
- **`relatorios.py`** — Legacy CSV/XLSX/HTML report helpers (mostly superseded by the in-`main.py` report logic; not imported by `main.py`).
- **`static/index.html`** — The complete frontend (single-page app, vanilla JS + Chart.js, no build step).

### Database dual-mode pattern

The app detects `DATABASE_URL` env var at startup to choose the backend:

- **No `DATABASE_URL`** → SQLite (`financeiro.db`, local file)
- **`DATABASE_URL` set** → PostgreSQL (Railway)

All queries go through four helper functions in `main.py` that abstract over this difference:
- `execute_query()` — replaces `?` with `%s` for PostgreSQL
- `fetchall_dict()` — returns `List[Dict]` for both drivers
- `fetchone_dict()` — returns `Dict | None`
- `scalar()` — returns a single value

When adding queries, always use `?` as the placeholder (the helpers handle the rewrite). Never call `conn.execute()` directly outside `relatorios.py`.

### Auth

Session-based auth stored in the `sessoes` table. Sessions are valid for 12 hours. The token is accepted as an HTTP-only cookie (`token`) **or** an `Authorization: Bearer <token>` header.

Three permission levels enforced via FastAPI `Depends`:
- `get_usuario` — any authenticated user (read-only operations)
- `pode_editar` — `editor` or `admin` (create/update)
- `requer_admin` — `admin` only (delete, user management, restricted entries)

Restricted entries (`restrita=1`) are hidden from non-admin users via `filtro_restritas()` which injects a `AND restrita=0` SQL clause.

### Admin bootstrap

If `ADMIN_EMAIL` and `ADMIN_PASSWORD` env vars are set at startup, `init_db()` creates an admin user automatically if it doesn't exist yet.

### Report generation (`/api/relatorios`)

The endpoint accepts `tipo` (financeiro, dre, fluxo, and several aliases like "contas a pagar", "inadimplencia") and `formato` (pdf or excel). PDF is generated with ReportLab; Excel with openpyxl. Both are streamed directly as `StreamingResponse`.

### Scheduled notifications

APScheduler runs a background job daily at 08:00 (America/Sao_Paulo) that sends email (Gmail SMTP) and WhatsApp (Z-API) alerts about overdue and soon-due accounts. Configured via env vars:
- `EMAIL_FROM`, `EMAIL_PASSWORD`, `EMAIL_TO`
- `ZAPI_INSTANCE_ID`, `ZAPI_INSTANCE_TOKEN`, `ZAPI_CLIENT_TOKEN`, `WHATSAPP_PHONES`

### Utility/migration scripts

The `fix_*.py`, `corrigir.py`, `atualizar.py`, `migrar_config.py`, and similar scripts in the root are one-off migration helpers and are **not part of the running application**. They were used to patch the database or `main.py` during development. Do not import or rely on them.

## Environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL URL (Railway). Absent = SQLite. |
| `ADMIN_EMAIL` | Seeds an admin user on first boot |
| `ADMIN_PASSWORD` | Seeds an admin user on first boot |
| `EMAIL_FROM` | Gmail address for notification emails |
| `EMAIL_PASSWORD` | Gmail app password |
| `EMAIL_TO` | Comma-separated extra notification recipients |
| `ZAPI_INSTANCE_ID` | Z-API WhatsApp instance |
| `ZAPI_INSTANCE_TOKEN` | Z-API token |
| `ZAPI_CLIENT_TOKEN` | Z-API client token |
| `WHATSAPP_PHONES` | Comma-separated phone numbers for WhatsApp alerts |
