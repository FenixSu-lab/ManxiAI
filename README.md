# ManxiAI

ManxiAI is a Django + Vue knowledge-base and RAG chat application. It uses PostgreSQL + pgvector for vector retrieval, supports OpenAI-compatible embedding services, supports DeepSeek/Qwen/OpenAI-compatible chat providers, and can expose a knowledge base as a hosted MCP Server.

## Current Features

- Token-based user registration, login, profile, API key, and team APIs.
- Knowledge-base management with `owner`, `write`, `read`, and `none` access levels.
- Public/Open knowledge bases: all signed-in users can read; only owner/write users can maintain data.
- Document data sources: file upload, web crawl, QA entries, and chat archives.
- RAG chat sessions bound to readable knowledge bases.
- Chat sharing: generate a public read-only conversation link and revoke it later.
- Chat archiving: preview a conversation and save selected QA pairs as a managed `chat_archive` data source.
- Model management UI for DeepSeek, Qwen, OpenAI-compatible, and custom OpenAI-compatible providers.
- Hosted MCP Server export for knowledge bases, with bearer token auth, tool scopes, access logs, and token rotation.
- Vue 3 + TypeScript + Vite + Pinia + Element Plus frontend.

## Tech Stack

- Backend: Django 4.2, Django REST Framework, Token Authentication.
- Database: PostgreSQL with `vector` extension.
- Embeddings: `http_openai_compatible`, `openai`, or local `hash_debug`.
- LLM: model management table first, then `.env` fallback; supports DeepSeek/OpenAI-compatible APIs.
- Frontend: Vue 3, TypeScript, Vite, Element Plus.

## Environment

Create `.env` from `env.example` and set real values. Do not commit `.env`.

```env
DEBUG=True
SECRET_KEY=change-me
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

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

DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_LLM_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=your-deepseek-key

EMBEDDING_PROVIDER=http_openai_compatible
EMBEDDING_MODEL=bge-large-zh-v1.5
EMBEDDING_DIMENSIONS=1024
EMBEDDING_API_URL=http://127.0.0.1:8884/v1/embeddings
EMBEDDING_API_KEY=

MCP_PUBLIC_BASE_URL=
MCP_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

For LAN access, replace `192.168.x.x` with this machine's actual LAN IP:

```env
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.x.x
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://192.168.x.x:3000,http://192.168.x.x:8000
MCP_PUBLIC_BASE_URL=http://192.168.x.x:8000
MCP_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://192.168.x.x:3000
```

## Database Setup

Create PostgreSQL database and enable pgvector:

```sql
CREATE DATABASE manxiai;
\c manxiai
CREATE EXTENSION IF NOT EXISTS vector;
```

Run migrations:

```powershell
.\env\Scripts\python.exe manage.py migrate
```

Create a local diagnostic admin account:

```powershell
.\env\Scripts\python.exe manage.py ensure_dev_admin --allow-default-password
```

Default local account: `admin@example.com` / `Admin123!`. For non-local use, pass `--password <value>` instead of using the default password.

## Run Locally

Backend:

```powershell
cd D:\github\ManxiAI
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
.\env\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

LAN backend:

```powershell
.\env\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

Frontend:

```powershell
cd D:\github\ManxiAI\frontend
npm install
npm run dev
```

Default URLs:

- Frontend: `http://127.0.0.1:3000`
- Backend API: `http://127.0.0.1:8000/api/v1/`
- Health check: `http://127.0.0.1:8000/api/v1/health/`
- Swagger: `http://127.0.0.1:8000/swagger/`
- Django Admin: `http://127.0.0.1:8000/admin/`

For a deterministic full-stack restart:

```powershell
.\scripts\dev_restart.ps1
```

From `frontend/`:

```powershell
npm run dev:fullstack
```

## Core Workflows

### Knowledge Permissions

- `owner`: manage knowledge base settings, users, data sources, MCP exports.
- `write`: maintain data sources and archive chats into the knowledge base.
- `read`: view and chat only.
- `none`: no access.
- Open knowledge bases skip read permission checks for signed-in users, but write operations still require owner/write.

### Chat Sharing

In a chat detail page, use `分享对话` to generate a public read-only URL:

```text
/share/chat/<token>
```

Anyone with the link can view the shared conversation. They cannot continue the chat or modify data. The owner can revoke the share.

### Chat Archive As Knowledge

In a chat detail page, use `归档为数据源` to preview QA pairs and save them into a writable knowledge base as a `chat_archive` data source. The archived source remains visible and manageable from the knowledge-base data-source table.

### Model Management

Open `Model Management` in the sidebar to manage chat providers.

- DeepSeek default endpoint: `https://api.deepseek.com`
- Qwen DashScope OpenAI-compatible endpoint: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- Custom providers must expose an OpenAI-compatible `/chat/completions` API.
- If no active database provider exists, the backend falls back to `.env` settings.

### Hosted MCP Server Export

Knowledge-base owners can export a knowledge base as a hosted MCP Server from the knowledge-base detail page.

- Endpoint: `/mcp/<profile_id>/`
- Auth: dedicated `Bearer mcp_...` token, shown only on create/rotate.
- Protocol: Streamable HTTP style JSON-RPC POST with `application/json` responses.
- MCP methods: `initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/read`.
- Tools: `search_knowledge`, `list_sources`, `get_document`, `get_paragraph`, `answer_with_citations`.
- Scopes: `search_only`, `citations_only`, `read_only`.
- Audit logs: method, tool, query, caller IP, latency, result count, status.

Example external MCP client config:

```json
{
  "name": "ManxiAI Knowledge Base",
  "url": "http://192.168.x.x:8000/mcp/<profile_id>/",
  "authorization": "Bearer <token>",
  "protocol": "mcp-streamable-http"
}
```

## Verification

Backend checks:

```powershell
.\env\Scripts\python.exe manage.py check
.\env\Scripts\python.exe manage.py makemigrations --check --dry-run
.\env\Scripts\python.exe manage.py migrate --check
.\env\Scripts\python.exe manage.py check_db_latency --warn-only --compare-client-modes
.\env\Scripts\python.exe manage.py check_embedding_endpoint --warn-only
.\env\Scripts\python.exe manage.py check_rag_stack
.\env\Scripts\python.exe manage.py check_llm_stack
.\env\Scripts\python.exe manage.py smoke_auth_flow
.\env\Scripts\python.exe manage.py smoke_api_stack
```

Live provider checks:

```powershell
.\env\Scripts\python.exe manage.py check_rag_stack --live
.\env\Scripts\python.exe manage.py check_llm_stack --live
.\env\Scripts\python.exe manage.py smoke_api_stack --real-embedding --timeout 30
```

Frontend build:

```powershell
cd frontend
npm run build
```

Focused tests:

```powershell
$env:USE_SQLITE='True'
.\env\Scripts\python.exe -m pytest apps/chat/tests apps/knowledge_base/tests apps/document/tests apps/mcp_server/tests apps/model_management/tests apps/pipeline/tests -q
```

## Troubleshooting

### Frontend reports network error

- Confirm Django is running.
- Confirm Vite proxy target points to the backend.
- Visit `http://127.0.0.1:8000/api/v1/health/`.
- If the backend is slow after login, run `check_db_latency --warn-only --compare-client-modes`.

### PostgreSQL connection is slow on Windows

Keep these local settings unless your database requires SSL/GSS:

```env
DB_GSSENCMODE=disable
DB_SSLMODE=disable
```

### Login returns CSRF errors

The SPA uses DRF token authentication. Login should not require a CSRF cookie. If CSRF errors appear, stop duplicate stale Django runserver processes and restart the backend from this project virtualenv.

### MCP URL still shows `127.0.0.1`

Set:

```env
MCP_PUBLIC_BASE_URL=http://<lan-ip>:8000
```

Then restart Django and reload the knowledge-base detail page.

## Cleanup Policy

Generated files are intentionally ignored:

- `.env`
- `env/`, `venv/`, `.venv/`
- `__pycache__/`, `.pytest_cache/`
- `logs/`, `tmp/`, `*.log`
- `db.sqlite3`
- `frontend/node_modules/`, `frontend/dist/`
- `media/`, `staticfiles/`

Do not commit real API keys, local databases, runtime logs, build output, or virtual environments.

## Development Conventions

- New backend files should include a module docstring.
- New functions and methods should include concise docstrings.
- Log key IDs, inputs, outputs, and failure states around backend operations.
- Keep user-facing UI text Chinese-first for product pages.
- Prefer PostgreSQL + pgvector for real local validation; use SQLite only for isolated tests.
