# ManxiAI Deployment Guide

This guide describes the current local and server deployment path for ManxiAI.

## Architecture

- Backend: Django REST Framework on `127.0.0.1:8000`.
- Frontend: Vite/Vue dev server on `127.0.0.1:3000`, or static build from `frontend/dist`.
- Database: PostgreSQL with `pgvector`.
- Embeddings: OpenAI-compatible `/v1/embeddings` endpoint.
- LLM: DeepSeek/OpenAI-compatible chat endpoint.

## Required Environment

Use `.env` for runtime configuration. Do not commit real secrets.

```env
SECRET_KEY=change-me
DEBUG=False
ALLOWED_HOSTS=your-domain.com,127.0.0.1

USE_SQLITE=False
DB_NAME=manxiai
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=127.0.0.1
DB_PORT=5432
DB_CONN_MAX_AGE=60
DB_CONNECT_TIMEOUT=10
DB_GSSENCMODE=disable
DB_SSLMODE=disable
DB_APPLICATION_NAME=manxiai-django

DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_LLM_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=your-deepseek-key

EMBEDDING_PROVIDER=http_openai_compatible
EMBEDDING_MODEL=bge-large-zh-v1.5
EMBEDDING_DIMENSIONS=1024
EMBEDDING_API_URL=http://127.0.0.1:8884/v1/embeddings
EMBEDDING_API_KEY=
```

## Database

```sql
CREATE DATABASE manxiai;
\c manxiai
CREATE EXTENSION IF NOT EXISTS vector;
```

Apply migrations:

```powershell
.\env\Scripts\python.exe manage.py migrate
```

For local diagnostics only, create or reset a known administrator:

```powershell
.\env\Scripts\python.exe manage.py ensure_dev_admin --allow-default-password
```

This creates `admin@example.com` / `Admin123!`. For non-local environments,
pass a real password with `--password` and do not use the default development
password.

Verify:

```powershell
.\env\Scripts\python.exe manage.py migrate --check
.\env\Scripts\python.exe manage.py check_db_latency --warn-only --compare-client-modes
.\env\Scripts\python.exe manage.py check_embedding_endpoint --warn-only
.\env\Scripts\python.exe manage.py check_rag_stack
.\env\Scripts\python.exe manage.py check_rag_stack --live
.\env\Scripts\python.exe manage.py check_llm_stack
.\env\Scripts\python.exe manage.py check_llm_stack --live
```

`check_rag_stack --live` makes a real embedding request. Use it before testing document ingestion or RAG chat.

## Backend Startup

Development:

```powershell
.\env\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

For local development, prefer the deterministic restart script so stale Django/Vite processes do not keep serving old code:

```powershell
.\scripts\dev_restart.ps1
```

Production should run Django behind a process manager and reverse proxy. Keep static/media handling explicit for the target server environment.

## Frontend Startup

Development:

```powershell
cd frontend
npm install
npm run dev
```

To start both backend and frontend from the frontend directory:

```powershell
npm run dev:fullstack
```

Production build:

```powershell
cd frontend
npm run build
npm run smoke:fullstack
```

Serve `frontend/dist` with your reverse proxy or static hosting. Forward `/api/` requests to the Django backend.

## Smoke Tests

Use debug providers for fast plumbing checks:

```powershell
.\env\Scripts\python.exe manage.py smoke_auth_flow
.\env\Scripts\python.exe manage.py smoke_api_stack
```

Use the real configured embedding endpoint while keeping the LLM deterministic:

```powershell
.\env\Scripts\python.exe manage.py smoke_api_stack --real-embedding --timeout 30
```

This command covers:

- Token login from the frontend origin without a CSRF cookie.
- Token-authenticated current-user lookup and logout.
- Current-user settings update.
- API-key create, regenerate, and delete.
- Team create, add member, and remove member.
- Knowledge-base creation.
- QA document creation.
- Paragraph embedding persistence.
- Chat session creation.
- Chat message API with retrieved context.

## Common Failures

### `settings.DATABASES is improperly configured`

`DB_NAME` is empty or not loaded. Check `.env` and run:

```powershell
Select-String -Path .env -Pattern "DB_NAME|DB_USER|DB_HOST|DB_PORT"
```

### `pgvector extension is not installed`

Run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Embedding provider reports OK but document ingestion fails

Run:

```powershell
.\env\Scripts\python.exe manage.py check_rag_stack --live
```

If this fails, fix `EMBEDDING_API_URL`, `EMBEDDING_API_KEY`, model name, or the embedding service process.

### LLM provider reports configuration errors

Run:

```powershell
.\env\Scripts\python.exe manage.py check_llm_stack
.\env\Scripts\python.exe manage.py check_llm_stack --live
```

If `--live` fails, fix the provider API key, base URL, model name, or upstream model service.

### Frontend cannot reach backend

The Vite proxy expects Django on `http://127.0.0.1:8000`.
For alternate local ports, set `VITE_API_PROXY_TARGET`, for example `VITE_API_PROXY_TARGET=http://127.0.0.1:18000`.
`npm run smoke:fullstack` starts a real Django process, so the configured PostgreSQL database must also be reachable.

Check:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/swagger/
Invoke-WebRequest http://127.0.0.1:8000/api/v1/health/
```

If API calls eventually succeed but take longer than the frontend timeout, check database latency:

```powershell
.\env\Scripts\python.exe manage.py check_db_latency --warn-only --compare-client-modes
```

When raw TCP is fast but PostgreSQL handshake is slow, first compare client modes. If `gssencmode=disable` is much faster, keep `DB_GSSENCMODE=disable` in `.env`. On Windows and local networks, default libpq GSS negotiation can add 15-20 seconds to the first PostgreSQL connection. Also check PostgreSQL authentication, `pg_hba.conf`, DNS/routing, firewall rules, and whether `DB_HOST` points at the intended database host.

### Login returns CSRF errors

The frontend uses DRF token authentication. Login should not require a CSRF cookie.
Run:

```powershell
.\env\Scripts\python.exe manage.py smoke_auth_flow
```

If the command passes but the browser still returns CSRF errors, the browser is probably connected to a stale backend process. Stop duplicate runserver processes and restart with the project virtualenv:

```powershell
Get-CimInstance Win32_Process -Filter "name='python.exe'" |
  Where-Object { $_.CommandLine -like '*manage.py runserver*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

.\env\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

### Refreshing frontend redirects to login

This should be handled by the router guard. If it recurs, check whether the `token` cookie exists and whether `/api/v1/auth/users/me/` returns `200`.

## Release Checklist

```powershell
.\env\Scripts\python.exe manage.py check
.\env\Scripts\python.exe manage.py makemigrations --check --dry-run
.\env\Scripts\python.exe manage.py migrate --check
.\env\Scripts\python.exe manage.py check_db_latency --warn-only --compare-client-modes
.\env\Scripts\python.exe manage.py check_embedding_endpoint --warn-only
.\env\Scripts\python.exe manage.py check_rag_stack --live
.\env\Scripts\python.exe manage.py check_llm_stack --live
.\env\Scripts\python.exe manage.py smoke_auth_flow
.\env\Scripts\python.exe manage.py smoke_api_stack --real-embedding --timeout 30

cd frontend
npm run build
npm run smoke:fullstack
```
