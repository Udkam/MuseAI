# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MuseAI is a Museum AI Guide System - a RAG (Retrieval-Augmented Generation) application for intelligent museum content interaction for the Xi'an Banpo Museum. It integrates Elasticsearch, PostgreSQL, Redis, and OpenAI-compatible LLM providers (default: Alibaba Qwen via DashScope compatible-mode).

The system has **two separate frontends** — do not conflate them:

- **Admin web frontend** — `backend/frontend/` (Vue 3 + Element Plus + Vite). The management console for exhibits, halls, documents, prompts, LLM traces, and TTS personas. It lives **inside this backend repository**.
- **Visitor mini-program frontend** — a separate top-level `frontend/` Git repository (native WeChat mini-program). The guest-facing guide client used by museum visitors. It is **NOT in this repository** and is opened with WeChat DevTools.

This `backend/` repository contains the FastAPI backend **and** the admin web frontend at `backend/frontend/`.

## Development Commands

### Backend

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest backend/tests/unit backend/tests/contract -v

# Run a single test file
uv run pytest backend/tests/unit/test_domain_entities.py -v

# Run a single test
uv run pytest backend/tests/unit/test_domain_entities.py::test_user_creation -v

# Run e2e tests (requires running infrastructure)
uv run pytest backend/tests/e2e -v

# Linting
uv run ruff check backend/

# Type checking
uv run mypy backend/

# Start development server
uv run uvicorn backend.app.main:app --reload
```

### Admin Web Frontend (`backend/frontend/`)

Vue 3 + Element Plus + Vite. This is the management console — **not** the visitor client.

```bash
cd frontend     # i.e. backend/frontend, the admin console (relative to this backend repo root)
npm install
npm run dev      # Vite dev server
npm run build    # Production build
```

> The visitor-facing WeChat mini-program lives in the **separate top-level `frontend/` repository** and is opened with WeChat DevTools, not built with the commands above.

### Infrastructure

```bash
# Start all services (Elasticsearch, PostgreSQL, Redis)
docker-compose up -d

# Stop all services
docker-compose down
```

## Architecture

### Backend Structure

The backend follows a strict layered architecture (API → Application → Domain → Infrastructure):

```
backend/app/
├── api/                    # FastAPI routers and request/response models
│   ├── deps.py            # Dependency injection (DB session, auth, rate limiting)
│   ├── _shared_responses.py # Shared response models across routers
│   ├── auth.py            # Authentication endpoints
│   ├── chat.py            # Chat session and message endpoints
│   ├── client_ip.py       # Client IP extraction from proxy headers
│   ├── curator.py         # Curator AI agent endpoints (plan-tour, narrative, reflection)
│   ├── documents.py       # Document upload API
│   ├── exhibits.py        # Public exhibit browsing endpoints
│   ├── health.py          # Health check endpoints
│   ├── profile.py         # Visitor profile endpoints
│   ├── tour.py            # Tour session, events, report, and chat endpoints
│   ├── tts.py             # TTS synthesis endpoint
│   └── admin/             # Admin-only router namespace
│       ├── documents.py   # Admin document management
│       ├── exhibits.py    # Admin exhibit management (CRUD, reindex)
│       ├── halls.py       # Admin hall management
│       ├── llm_traces.py  # LLM trace viewing and analysis
│       ├── prompts.py     # Admin prompt template management (versioning, rollback)
│       └── tts_persona.py # Admin TTS persona management and voice preview
├── application/            # Business logic and services
│   ├── auth_service.py    # User registration/login
│   ├── chat_service.py    # Chat message handling, SSE streaming
│   ├── chat_message_service.py  # Chat message CRUD
│   ├── chat_session_service.py  # Chat session CRUD
│   ├── chat_stream_service.py   # RAG streaming orchestration
│   ├── document_service.py # Document CRUD
│   ├── document_filter.py # Dynamic retrieval document filtering
│   ├── ingestion_service.py # Document chunking and embedding
│   ├── unified_indexing_service.py # Unified ES indexing pipeline
│   ├── exhibit_service.py  # Exhibit CRUD
│   ├── exhibit_indexing_service.py # Exhibit ES indexing
│   ├── content_source.py   # Content source abstraction
│   ├── curator_service.py  # Curator AI agent orchestration
│   ├── profile_service.py  # Visitor profile CRUD
│   ├── prompt_service.py   # Prompt template CRUD
│   ├── prompt_service_adapter.py # Prompt service adapter
│   ├── tour_chat_service.py # Tour chat streaming
│   ├── tour_session_service.py # Tour session CRUD
│   ├── tour_event_service.py  # Tour event recording
│   ├── tour_report_service.py # Tour report generation
│   ├── tts_service.py     # TTS service with config resolution
│   ├── tts_streaming.py   # Sentence-level TTS streaming and audio interleaving
│   ├── chunking.py        # Text chunking algorithms (hierarchical parent-child)
│   ├── context_manager.py # Context window management
│   ├── error_handling.py  # Centralized error handling
│   ├── sse_events.py      # SSE event type definitions
│   ├── ports/             # Port interfaces (dependency inversion)
│   ├── llm_trace/         # LLM call tracing and auditing
│   │   ├── context.py     # Trace context management
│   │   ├── formatter.py   # Trace data formatting
│   │   ├── masking.py     # Sensitive data masking
│   │   ├── recorder.py    # Trace recording
│   │   └── repository.py  # Trace persistence
│   └── workflows/         # Multi-turn conversation workflows
│       ├── multi_turn.py  # State machine for retrieval evaluation
│       ├── query_transform.py # Query transformation (HyDE, step-back)
│       └── reflection_prompts.py # Reflection prompt templates
├── domain/                 # Domain entities and value objects
│   ├── entities.py        # User, ChatSession, Document, IngestionJob, Exhibit, TourSession, etc.
│   ├── value_objects.py   # Typed IDs (UserId, SessionId, ExhibitId, TourSessionId, etc.)
│   ├── exceptions.py      # Domain-specific exceptions
│   └── services/          # Domain services
│       └── retrieval.py   # RRF fusion algorithm with source deduplication
├── infra/                  # Infrastructure layer
│   ├── postgres/          # Database models and session management
│   │   ├── models.py      # SQLAlchemy ORM models (13 classes)
│   │   └── database.py    # Engine lifecycle, session factory
│   ├── elasticsearch/     # ES client for vector/BM25 search
│   ├── redis/             # Caching and token blacklist
│   ├── cache/             # Application-level caching
│   │   └── prompt_cache.py # Prompt template cache with Redis fallback
│   ├── langchain/         # LangChain integrations
│   │   ├── embeddings.py  # Custom Ollama embeddings
│   │   ├── retrievers.py  # RRF retriever implementation
│   │   ├── agents.py      # RAG agent with LangGraph state machine (includes filter and merge nodes)
│   │   ├── curator_agent.py # Curator agent with LangGraph
│   │   ├── curator_tools/ # Curator tool definitions (path planning, narrative, etc.)
│   │   ├── llm_trace_callback.py # LangChain callback for LLM tracing
│   │   └── tools.py       # Shared tool utilities
│   ├── providers/         # External service providers
│   │   ├── llm.py         # OpenAI-compatible LLM provider
│   │   ├── embedding.py   # Embedding provider abstraction
│   │   ├── rerank/        # Rerank providers
│   │   │   ├── base.py    # Base rerank provider ABC
│   │   │   ├── factory.py # Rerank provider factory
│   │   │   ├── mock.py    # Mock rerank for testing
│   │   │   ├── openai.py  # OpenAI-compatible rerank
│   │   │   └── siliconflow.py # SiliconFlow rerank provider
│   │   └── tts/           # TTS providers
│   │       ├── base.py    # BaseTTSProvider ABC
│   │       ├── cached.py  # Redis-cached TTS wrapper
│   │       ├── factory.py # TTS provider factory
│   │       ├── mock.py    # Mock TTS for testing
│   │       └── xiaomi.py  # Xiaomi TTS provider
│   └── security/          # JWT handling, password hashing
├── config/                 # Configuration management
│   └── settings.py        # Pydantic settings with validation
└── main.py                 # FastAPI app and global singletons
```

### Key Architectural Patterns

1. **Dependency Injection**: FastAPI's `Depends()` for session management, authentication, and rate limiting. See `api/deps.py` for the dependency chain.

2. **Global Singletons**: `main.py` manages global instances (ES client, LLM, embeddings, retriever, RAG agent) with lazy initialization.

3. **RRF Fusion Retrieval**: Combines dense (vector) and sparse (BM25) search using Reciprocal Rank Fusion with source-level deduplication. See `domain/services/retrieval.py` and `infra/langchain/retrievers.py`.

4. **RAG Agent with LangGraph**: State machine that evaluates retrieval quality, applies dynamic document filtering, merges hierarchical chunks, and can transform queries if scores are low. See `infra/langchain/agents.py`.

5. **SSE Streaming**: Chat and tour responses stream via Server-Sent Events with structured event types (`thinking`, `chunk`, `done`, `error`, `audio` for TTS).

6. **TTS Integration**: Text-to-speech with provider abstraction (Xiaomi, Mock), sentence-level streaming, Redis caching, and persona management. Audio events are interleaved with text in SSE streams.

7. **LLM Tracing**: Transparent call recording with sensitive data masking, stored in PostgreSQL for auditing. See `application/llm_trace/`.

8. **Prompt Management**: Versioned prompt templates with cache layer, rollback support, and admin CRUD. See `infra/cache/prompt_cache.py`.

### Database Schema

PostgreSQL tables:
- `users`: id, email, password_hash, role, created_at
- `documents`: id, user_id, filename, status, error, created_at
- `ingestion_jobs`: id, document_id, status, chunk_count, error, created_at, updated_at
- `chat_sessions`: id, user_id, title, created_at
- `chat_messages`: id, session_id, role, content, trace_id, created_at
- `halls`: id, name, slug, description, floor, sort_order, is_active, created_at, updated_at
- `exhibits`: id, name, description, location_x/y, floor, hall, category, era, importance, estimated_visit_time, document_id, is_active, display_order, created_at, updated_at
- `visitor_profiles`: id, user_id, interests, knowledge_level, narrative_preference, reflection_depth, visited_exhibit_ids, feedback_history, created_at, updated_at
- `tour_paths`: id, name, description, theme, estimated_duration, exhibit_ids, is_active, created_by, created_at, updated_at
- `tour_sessions`: id, user_id, guest_id, session_token, interest_type, persona, assumption, current_hall, current_exhibit_id, visited_halls, visited_exhibit_ids, status, last_active_at, started_at, completed_at, created_at
- `tour_events`: id, tour_session_id, event_type, exhibit_id, hall, duration_seconds, metadata, created_at
- `tour_reports`: id, tour_session_id, total_duration_minutes, most_viewed_exhibit_id, most_viewed_exhibit_duration, longest_hall, longest_hall_duration, total_questions, total_exhibits_viewed, ceramic_questions, identity_tags, radar_scores, one_liner, report_theme, created_at
- `prompts`: id, key, name, description, category, content, variables, is_active, created_at, updated_at
- `prompt_versions`: id, prompt_id, version, content, changed_by, change_reason, created_at
- `llm_traces`: id, call_id, session_id, user_id, provider, model, prompt_tokens, completion_tokens, latency_ms, status, request/response masked data, created_at

### Elasticsearch Index

Index `museai_chunks_v1` with:
- `chunk_id` (keyword), `document_id` (keyword), `parent_chunk_id` (keyword)
- `content` (text with ik_max_word analyzer)
- `content_vector` (dense_vector, configurable dims)
- `chunk_level` (keyword), `source` (keyword)
- Supports hierarchical chunking (parent-child relationships) and source-level deduplication

## Configuration

Environment variables (see `.env.example` for full reference):

### Core
- `APP_NAME`: str, default `"MuseAI"` — Application display name
- `APP_ENV`: str, default `"development"` — One of: development, test, local, production
- `DEBUG`: bool, default `False` — Enable debug mode

### Auth
- `JWT_SECRET`: str, default `""` — **Required in production** (≥32 chars)
- `JWT_ALGORITHM`: str, default `"HS256"` — JWT signing algorithm
- `JWT_EXPIRE_MINUTES`: int, settings.py default `60` — Token lifetime in minutes (`.env.example` ships `1440`)
- `ADMIN_EMAILS`: str, default `""` — Comma-separated admin emails. **Deprecated**: in production this raises a `DeprecationWarning`. Initialize admins with `scripts/bootstrap_admin.py` instead.

### Database
- `DATABASE_URL`: str, default `"sqlite+aiosqlite:///:memory:"` — PostgreSQL connection string

### Elasticsearch
- `ELASTICSEARCH_URL`: str, default `"http://localhost:9200"` — ES endpoint
- `ELASTICSEARCH_INDEX`: str, default `"museai_chunks_v1"` — ES index name
- `EMBEDDING_DIMS`: int, settings.py default `768` (1–4096) — Vector dimensionality. ⚠️ Must match the deployed embedding model **and** the ES index mapping. `.env.example` ships `1536`; confirm the value matches your actual embedding model before (re)indexing.

### Redis
- `REDIS_URL`: str, default `"redis://localhost:6379"` — Redis endpoint

### LLM
- `LLM_PROVIDER`: str, default `"qwen"` — One of: openai_compatible, openai, deepseek, qwen
- `LLM_BASE_URL`: str, default `"https://dashscope.aliyuncs.com/compatible-mode/v1"` — OpenAI-compatible base URL (DashScope Beijing; use `dashscope-intl` / `dashscope-us` for Singapore / Virginia)
- `LLM_API_KEY`: str, default `""` — **Required in production** (DashScope / Model Studio API key)
- `LLM_MODEL`: str, default `"qwen-flash"` — Backward-compatible fallback model
- `LLM_TOUR_MODEL`: str, default `"qwen-flash"` — Tour chat / RAG query rewrite / streaming guide answers
- `LLM_REPORT_MODEL`: str, default `"qwen-plus"` — Reports and research-style summarization
- `LLM_COMPAT_MODE`: str, default `"qwen"` — One of: auto, openai, deepseek, qwen (provider-specific request shaping)
- `LLM_HEADERS`: str, default `""` — JSON object string of extra headers, e.g. `{"User-Agent": "curl/8.5.0"}`
- `LLM_TEMPERATURE`: float, default `0.2` — 0.0–2.0
- `LLM_MAX_TOKENS`: int, default `800` — `0` = no limit
- `LLM_ENABLE_THINKING`: bool, default `False` — Disables provider thinking mode where supported. Qwen3.5/3.6 hybrid-thinking models default thinking **on**; keep this `False` to control cost/latency.

### Embedding
- `EMBEDDING_PROVIDER`: str, default `"ollama"` — One of: ollama, openai
- `EMBEDDING_OLLAMA_BASE_URL`: str, default `"http://localhost:11434"` — Ollama endpoint (provider=ollama)
- `EMBEDDING_OLLAMA_MODEL`: str, default `"nomic-embed-text"` — Ollama model name (provider=ollama)
- `EMBEDDING_OPENAI_BASE_URL` / `EMBEDDING_OPENAI_API_KEY` / `EMBEDDING_OPENAI_MODEL`: str, default `""` — Used when provider=openai (SiliconFlow / OpenAI-compatible embeddings)

### Rerank
- `RERANK_PROVIDER`: str, settings.py default `"siliconflow"` — One of: siliconflow, openai, cohere, custom, mock. (`.env.example` ships `mock` for local/test; use a real provider in production.)
- `RERANK_BASE_URL`: str, default `""` — Required for openai/cohere/custom providers. (The SiliconFlow provider's base URL is hardcoded in its provider class — do not change.)
- `RERANK_API_KEY`: str, default `""` — **Required in production for real (non-mock) providers**
- `RERANK_MODEL`: str, default `"rerank-v1"` — Rerank model identifier
- `RERANK_TOP_N`: int, default `10` — Candidates returned by rerank
- `RERANK_ABSOLUTE_THRESHOLD`: float, default `0.25` — Dynamic-filter absolute score gate (0–1)
- `RERANK_RELATIVE_GAP`: float, default `0.25` — Dynamic-filter relative-gap strategy (0–1)
- `RERANK_MIN_DOCS`: int, default `1` — Minimum docs kept after filtering
- `RERANK_MAX_DOCS`: int, default `8` — Maximum docs kept after filtering (≤ `RERANK_TOP_N`)

### Retrieval & Chunk Merge
- `RETRIEVAL_TOP_K`: int, default `15` — Candidates retrieved before rerank
- `CHUNK_MERGE_ENABLED`: bool, default `True` — Promote parent chunks when child chunks are retrieved
- `CHUNK_MERGE_MAX_LEVEL`: int, default `1` — Max chunk level allowed during merge
- `CHUNK_MERGE_MAX_PARENTS`: int, default `3` — Max parent chunks promoted

### TTS
- `TTS_ENABLED`: bool, settings.py default `True` — Enable text-to-speech. (`.env.example` ships `false`; the mini-program uses manual TTS playback.)
- `TTS_PROVIDER`: str, default `"xiaomi"` — One of: xiaomi, mock
- `TTS_BASE_URL`: str, default `"https://api.xiaomimimo.com/v1"` — Xiaomi MiMo TTS base URL
- `TTS_API_KEY`: str, default `""` — **Required in production when TTS_ENABLED and provider != mock**
- `TTS_MODEL`: str, default `"mimo-v2.5-tts"` — TTS model identifier
- `TTS_DEFAULT_VOICE`: str, default `"冰糖"` — Default voice/persona (frontend pins to 冰糖)
- `TTS_TIMEOUT`: float, default `30.0` — TTS request timeout (seconds)
- `TTS_VOICE_DESIGN_MODEL`: str, default `"mimo-v2.5-tts-voicedesign"` — Voice design model (admin voice preview)

### Logging
- `LOG_LEVEL`: str, default `"INFO"` — One of: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `LOG_DIR`: str, default `"logs"` — Log file directory
- `LOG_FORMAT`: str, default `"json"` — Log format ("json" or "text")

### Rate Limiting
- `RATE_LIMIT_ENABLED`: bool, default `True` — Enable/disable rate limiting

### Security
- `ALLOW_INSECURE_DEV_DEFAULTS`: bool, default `False` — Allow dev secrets in non-production environments
- `TRUSTED_PROXIES`: str, default `""` — Comma-separated trusted proxy IPs for X-Forwarded-For

### CORS
- `CORS_ORIGINS`: str, default `"http://localhost:3000"` — Comma-separated origins or `"*"` (wildcard forbidden in production)
- `CORS_ALLOW_CREDENTIALS`: bool, default `True` — Allow credentials in CORS

Production requires `JWT_SECRET` (≥32 chars), `LLM_API_KEY`, `RERANK_API_KEY` (when `RERANK_PROVIDER` != mock), and `TTS_API_KEY` (when `TTS_ENABLED` and provider != mock). `ADMIN_EMAILS` is deprecated in production — use `scripts/bootstrap_admin.py`.

## Testing Structure

```
backend/tests/
├── conftest.py     # Global test fixtures (shared across all test types)
├── unit/           # Unit tests (fast, mocked dependencies)
│   └── conftest.py # Unit-specific fixtures
├── contract/       # API contract tests (FastAPI TestClient)
├── e2e/            # End-to-end tests (requires running infra)
└── fixtures/       # Test fixtures and mocks (mock_factories replaces mock_providers)
```

Test configuration in `pyproject.toml`: `asyncio_mode = "auto"`, `testpaths = ["backend/tests"]`.

## Authentication Flow

1. Register/login via `/api/v1/auth/*` endpoints
2. JWT token in `Authorization: Bearer <token>` header
3. Token blacklist in Redis for logout
4. Rate limiting: regular endpoints (fail-open), auth endpoints (fail-closed)

## Common Patterns

### Adding a new API endpoint

1. Create request/response Pydantic models in the router file
2. Add router function with appropriate dependencies (`SessionDep`, `CurrentUser`, `RateLimitDep`)
3. Business logic goes in `application/` layer
4. Database operations use SQLAlchemy async session

### Adding a new test

1. Unit tests: mock external dependencies, test in isolation
2. Contract tests: use `FastAPI TestClient`, mock database with `aiosqlite`
3. E2E tests: require running infrastructure (docker-compose)

### Working with the RAG pipeline

1. Query enters through `chat_service.ask_question_stream_with_rag()`
2. RAG agent retrieves documents, reranks, then applies dynamic filter node (absolute/relative gap strategies)
3. Hierarchical chunk merge node promotes parent chunks when child chunks are retrieved
4. If score < threshold, query transformation may occur
5. Response generated with context, streamed via SSE (with optional TTS audio events)

### Database migrations (Alembic)

The project uses Alembic for schema migrations. Configuration is in `alembic.ini` and `backend/alembic/env.py`.

```bash
# Generate a migration after model changes
alembic revision --autogenerate -m "add_new_table"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current migration state
alembic current
```

Guidelines:
- Always review auto-generated migrations before applying — Alembic may miss column renames or detect false changes
- Never edit applied migrations — create a new revision instead
- Test migrations against a clean database before deploying: `alembic upgrade head` from scratch
- Include `backfill` logic in the migration for data transformations, not in application code
