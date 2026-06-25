# RAG Runtime Checks

Use these commands after editing database, embedding, or chat code.

## Database And pgvector

```powershell
.\env\Scripts\python.exe manage.py migrate --check
.\env\Scripts\python.exe manage.py makemigrations --check --dry-run
.\env\Scripts\python.exe manage.py check_embedding_endpoint --warn-only
.\env\Scripts\python.exe manage.py check_rag_stack
.\env\Scripts\python.exe manage.py check_rag_stack --live
.\env\Scripts\python.exe manage.py check_llm_stack
.\env\Scripts\python.exe manage.py check_llm_stack --live
```

`check_rag_stack` validates:

- Django can connect to the configured database.
- PostgreSQL has the `vector` extension enabled.
- The configured embedding provider can be instantiated.
- Required embedding settings are not empty or known placeholder values.
- The paragraph embedding table is reachable.

`check_rag_stack --live` also sends one real embedding request and verifies the returned vector shape.

`check_llm_stack` validates the configured LLM provider, rejects empty or known placeholder API keys, and prints the selected provider/model. `check_llm_stack --live` also sends one minimal real chat request.

## Live Embedding Failures

If `check_rag_stack --live` fails with `Embedding request failed`, the Django
database and pgvector checks may still be healthy. The failure is usually the
external embedding service configured by `EMBEDDING_API_URL`.

Check the endpoint directly:

```powershell
.\env\Scripts\python.exe manage.py check_embedding_endpoint --warn-only
curl.exe --max-time 10 --silent --show-error --write-out "`nHTTP_STATUS:%{http_code}`n" http://172.16.60.26:8884/v1/embeddings
```

`Empty reply from server`, `Connection reset`, or `HTTP_STATUS:000` means the
service is not returning a valid HTTP response to this project. Verify that the
embedding service process is running, the route is exactly an OpenAI-compatible
`POST /v1/embeddings` endpoint, and the configured model name matches what the
service serves.

## Local Retrieval Smoke Test

```powershell
.\env\Scripts\python.exe manage.py smoke_rag_stack
```

This command temporarily switches embeddings to `hash_debug`, creates a throwaway
knowledge base and document, writes vectors into PostgreSQL, performs a pgvector
similarity search, and deletes the temporary user afterward.

Use `--keep` only when you want to inspect the generated rows:

```powershell
.\env\Scripts\python.exe manage.py smoke_rag_stack --keep
```

## Chat API Smoke Test

```powershell
.\env\Scripts\python.exe manage.py smoke_chat_stack
```

This command temporarily switches embeddings to `hash_debug` and the LLM to
`debug`, posts a message through the DRF chat API, verifies retrieved context
reaches the LLM, and deletes the temporary user afterward.

## Full API Smoke Test

```powershell
.\env\Scripts\python.exe manage.py smoke_api_stack
```

This command exercises the same URL routes used by the frontend: account
settings, API keys, team membership, knowledge-base creation, QA document
creation, embedding persistence, chat session creation, and chat message
posting. By default, it uses `hash_debug` embeddings and `debug` LLM replies.
It temporarily enables `RUN_BACKGROUND_TASKS_SYNC` so background embedding
completes deterministically inside the smoke run.

Use the real configured embedding endpoint while keeping the LLM deterministic:

```powershell
.\env\Scripts\python.exe manage.py smoke_api_stack --real-embedding --timeout 30
```

## Embedding Providers

- `openai`: uses `OPENAI_BASE_URL + /embeddings` and `OPENAI_API_KEY`.
- `http_openai_compatible`: uses `EMBEDDING_API_URL` and `EMBEDDING_API_KEY`.
- `hash_debug`: deterministic local vectors for development diagnostics only.

## LLM Providers

- `deepseek`: uses `DEEPSEEK_BASE_URL` and `DEEPSEEK_API_KEY`.
- `openai`: uses `OPENAI_BASE_URL` and `OPENAI_API_KEY`.
- `debug`: deterministic local replies for smoke tests only.

Do not use `hash_debug` or `debug` for production quality. They are only meant
to prove that PostgreSQL, pgvector, persistence, retrieval, and chat plumbing work.
