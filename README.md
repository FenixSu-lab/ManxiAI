# ManxiAI

ManxiAI is a Django + Vue knowledge-base application with PostgreSQL, pgvector, document ingestion, embeddings, vector retrieval, and RAG chat.

## Current Capabilities

- User registration, login, profile update, teams, and API-key management.
- Knowledge-base CRUD, document upload, web document creation, QA document creation, and document detail browsing.
- Paragraph embedding storage in PostgreSQL with pgvector.
- RAG chat sessions linked to a knowledge base.
- Dashboard summary counters and runtime health display.
- OpenAI-compatible embedding provider support, OpenAI/DeepSeek-compatible LLM support, and local debug providers for smoke tests.
- Frontend built with Vue 3, TypeScript, Vite, Pinia, Element Plus.

## Runtime Requirements

- Python 3.10+ recommended.
- Node.js 18+ recommended.
- PostgreSQL with the `vector` extension installed.
- A reachable OpenAI-compatible embedding endpoint, or `hash_debug` for diagnostics only.
- A DeepSeek/OpenAI-compatible chat model key for real LLM replies, or `debug` for diagnostics only.

## Backend Setup

```powershell
cd D:\github\ManxiAI
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create PostgreSQL database and pgvector extension:

```sql
CREATE DATABASE manxiai;
\c manxiai
CREATE EXTENSION IF NOT EXISTS vector;
```

Create `.env` from `env.example` and set real values:

```env
DEBUG=True
SECRET_KEY=change-me
ALLOWED_HOSTS=localhost,127.0.0.1

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

Run migrations and start Django:

```powershell
.\env\Scripts\python.exe manage.py migrate
.\env\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

## Frontend Setup

```powershell
cd D:\github\ManxiAI\frontend
npm install
npm run dev
```

The Vite dev server runs on `http://127.0.0.1:3000` and proxies `/api` to `http://127.0.0.1:8000`.
Set `VITE_API_PROXY_TARGET` if you need the dev proxy to point at a different backend port.

For the normal local workflow, prefer the deterministic restart script. It stops stale Django/Vite processes for this workspace, runs backend checks, starts both servers, and verifies the frontend proxy:

```powershell
.\scripts\dev_restart.ps1
```

From the frontend directory, the same flow is available as:

```powershell
npm run dev:fullstack
```

## Verification Commands

Run these after changing database, embedding, RAG, auth, or frontend integration code:

```powershell
.\env\Scripts\python.exe manage.py check
.\env\Scripts\python.exe manage.py makemigrations --check --dry-run
.\env\Scripts\python.exe manage.py migrate --check
.\env\Scripts\python.exe manage.py check_db_latency --warn-only --compare-client-modes
.\env\Scripts\python.exe manage.py check_embedding_endpoint --warn-only
.\env\Scripts\python.exe manage.py check_rag_stack
.\env\Scripts\python.exe manage.py check_rag_stack --live
.\env\Scripts\python.exe manage.py check_llm_stack
.\env\Scripts\python.exe manage.py check_llm_stack --live
.\env\Scripts\python.exe manage.py smoke_auth_flow
.\env\Scripts\python.exe manage.py smoke_api_stack
.\env\Scripts\python.exe manage.py smoke_api_stack --real-embedding --timeout 30
```

Frontend build check:

```powershell
cd frontend
npm run build
npm run smoke:fullstack
```

Focused backend tests:

```powershell
$env:USE_SQLITE='True'
.\env\Scripts\python.exe -m pytest apps/chat/tests apps/document/tests apps/embedding/tests apps/model_management/tests apps/pipeline/tests -q
```

## Provider Notes

- `EMBEDDING_PROVIDER=http_openai_compatible` calls `EMBEDDING_API_URL` using the OpenAI `/embeddings` response shape.
- `EMBEDDING_PROVIDER=openai` uses `OPENAI_BASE_URL + /embeddings` and requires a real `OPENAI_API_KEY` or `EMBEDDING_API_KEY`.
- `EMBEDDING_PROVIDER=hash_debug` is deterministic and local, but it is only for tests and smoke checks.
- `check_embedding_endpoint --warn-only` diagnoses the configured embedding service with TCP, health, and OpenAI-compatible POST checks.
- `DEFAULT_LLM_PROVIDER=debug` is deterministic and local, useful for smoke tests without spending LLM tokens.
- `DEFAULT_LLM_PROVIDER=deepseek` or `openai` is needed for real assistant answers.
- `check_llm_stack --live` sends one minimal real chat request. Use it when validating production LLM credentials.

## Authentication Notes

- The SPA uses DRF token authentication, not Django session authentication.
- Login and registration must work without a CSRF cookie when called from `http://localhost:3000`.
- Run `.\env\Scripts\python.exe manage.py smoke_auth_flow` after changing auth, CORS, CSRF, or frontend proxy settings.
- If a stale backend keeps returning old behavior, stop duplicate runserver processes before restarting:

```powershell
Get-CimInstance Win32_Process -Filter "name='python.exe'" |
  Where-Object { $_.CommandLine -like '*manage.py runserver*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

## Database Latency Notes

- `GET /api/v1/health/` returns backend status and database query latency without authentication.
- Run `.\env\Scripts\python.exe manage.py check_db_latency --warn-only --compare-client-modes` when the frontend reports backend timeouts after login.
- If TCP latency is low but PostgreSQL handshake latency is high, first check `DB_GSSENCMODE=disable`. On Windows and local networks, default libpq GSS negotiation can add 15-20 seconds to the first PostgreSQL connection.
- Keep `DB_SSLMODE=disable` for local PostgreSQL servers that do not use SSL. Use `require` or `verify-full` only when the server is configured for SSL.
- Prefer `DB_HOST=127.0.0.1` only when PostgreSQL is actually listening locally and `pg_hba.conf` allows it. Otherwise use the reachable host and fix the handshake delay at the database layer.

## Useful URLs

- Frontend: `http://127.0.0.1:3000`
- Backend API: `http://127.0.0.1:8000/api/v1/`
- Health check: `http://127.0.0.1:8000/api/v1/health/`
- Swagger: `http://127.0.0.1:8000/swagger/`
- ReDoc: `http://127.0.0.1:8000/redoc/`
- Django Admin: `http://127.0.0.1:8000/admin/`

## Development Conventions

- Add a file header comment/docstring for new files.
- Add docstrings for functions and methods.
- Log key inputs, outputs, IDs, and failure states around backend operations.
- Do not commit `.env`, local databases, virtualenvs, build output, or runtime logs.
