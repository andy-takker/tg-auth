# tg-auth

A small Litestar service that signs users in with Telegram via [OpenID Connect](https://core.telegram.org/bots/telegram-login#openid-connect) — using the new `oauth.telegram.org` flow that Telegram shipped in 2025, not the legacy [`telegram.org/widgets/login`](https://core.telegram.org/widgets/login) widget.

The point of the repo is to show the OIDC integration end-to-end: BotFather setup, JWT verification against Telegram's JWKS, the user/account schema, and where the cookie session fits in. It's a PoC, not a framework.

[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?logo=github-actions&logoColor=white)](.github/workflows/ci.yaml)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/release/python-3130/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Screenshots

| Login page (`GET /`) | Status page (`GET /app`) |
|---|---|
| ![Sign in with Telegram](docs/sign_in.jpg) | ![You're signed in](docs/app_page.jpg) |

The login page hosts Telegram's OIDC widget; the popup returns a signed `id_token` which the backend verifies before setting a cookie session. The status page reads the user from the DB and exposes a logout button that clears that cookie via `POST /api/v1/auth/logout`.

---

## Table of contents

1. [What this is](#what-this-is)
2. [Why it exists](#why-it-exists)
3. [Tech stack](#tech-stack)
4. [Authentication flow](#authentication-flow)
5. [Project layout](#project-layout)
6. [HTTP routes](#http-routes)
7. [Database schema](#database-schema)
8. [Setup](#setup)
9. [Running locally](#running-locally)
10. [Running with Docker](#running-with-docker)
11. [Tests](#tests)
12. [Continuous integration](#continuous-integration)
13. [Troubleshooting](#troubleshooting)
14. [Limitations](#limitations)
15. [Extending it (e.g. adding SMS auth)](#extending-it)
16. [License](#license)

---

## What this is

A [Litestar](https://litestar.dev/) service that:

- serves a login page with Telegram's OIDC widget (`oauth.telegram.org/js/telegram-login.js`);
- receives the resulting `id_token` (JWT signed by Telegram) on `POST /api/v1/auth/telegram`;
- verifies the JWT against Telegram's JWKS — `iss`, `aud`, `exp`, `iat`, signature;
- upserts a `User` + `TelegramAccount` row in SQLite via async [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/) + [aiosqlite](https://github.com/omnilib/aiosqlite);
- sets a signed cookie session;
- self-heals stale sessions (if the cookie points at a user that was deleted, `/app` clears the cookie and redirects to `/`);
- rate-limits the auth endpoint and exposes `/health/live` + `/health/ready`.

It uses [Dishka](https://github.com/reagento/dishka) for DI, [Alembic](https://alembic.sqlalchemy.org/) for migrations, [structlog](https://www.structlog.org/) for logs, and ships with pytest tests, a GitHub Actions workflow, and a Dockerfile.

## Why it exists

Most Telegram-login examples on GitHub still use the legacy `telegram.org/js/telegram-widget.js` widget: HMAC of the bot token, `/setdomain` in BotFather, raw user fields on a callback. The new flow is a regular OIDC provider — discovery document, JWKS, ID tokens — and the integration looks nothing like the old one.

[Telegram's docs](https://core.telegram.org/bots/telegram-login#openid-connect) cover the protocol but not the wiring in any specific stack, so this repo writes it out: BotFather configuration, JWT validation, the user/telegram-account schema. The Litestar / Dishka / SQLAlchemy choices are incidental — the auth-relevant bits port to any Python web stack.

## Tech stack

### Runtime dependencies

| Library | Why it's here | Link |
|---|---|---|
| **Litestar** | Async web framework, dataclass DTOs, built-in cookie sessions, rate-limit middleware | [litestar.dev](https://litestar.dev/) · [GitHub](https://github.com/litestar-org/litestar) |
| **uvicorn** | ASGI server (production-grade, fast) | [uvicorn.org](https://www.uvicorn.org/) · [GitHub](https://github.com/encode/uvicorn) |
| **Dishka** | Dependency injection with explicit `APP` / `REQUEST` scopes | [GitHub](https://github.com/reagento/dishka) · [docs](https://dishka.readthedocs.io/) |
| **PyJWT** | JWT decoding + signature verification (with `[crypto]` extras for RSA/EC) | [pyjwt.readthedocs.io](https://pyjwt.readthedocs.io/) · [GitHub](https://github.com/jpadilla/pyjwt) |
| **SQLAlchemy 2.0** | Async ORM (`AsyncSession`, mapped dataclasses) | [docs](https://docs.sqlalchemy.org/en/20/) · [GitHub](https://github.com/sqlalchemy/sqlalchemy) |
| **aiosqlite** | SQLite async driver for SQLAlchemy | [GitHub](https://github.com/omnilib/aiosqlite) |
| **Alembic** | Schema migrations | [alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/) · [GitHub](https://github.com/sqlalchemy/alembic) |
| **Jinja2** | HTML templating for `index.html` and `app.html` | [palletsprojects.com/p/jinja](https://palletsprojects.com/p/jinja/) · [GitHub](https://github.com/pallets/jinja) |
| **structlog** | Structured logs (console in dev, JSON-ready for prod) | [structlog.org](https://www.structlog.org/) · [GitHub](https://github.com/hynek/structlog) |
| **orjson** | Fast JSON serializer used by SQLAlchemy `json_serializer` | [GitHub](https://github.com/ijl/orjson) |

### Development dependencies

| Tool | Purpose | Link |
|---|---|---|
| **uv** | Project + dependency manager (replaces pip + venv + pip-tools) | [GitHub](https://github.com/astral-sh/uv) · [docs](https://docs.astral.sh/uv/) |
| **ruff** | Linter + formatter (replaces flake8, isort, black) | [GitHub](https://github.com/astral-sh/ruff) · [docs](https://docs.astral.sh/ruff/) |
| **mypy** | Static type checking | [mypy-lang.org](https://mypy-lang.org/) · [GitHub](https://github.com/python/mypy) |
| **pre-commit** | Git hook framework for ruff + mypy | [pre-commit.com](https://pre-commit.com/) · [GitHub](https://github.com/pre-commit/pre-commit) |

### Test dependencies

| Tool | Purpose | Link |
|---|---|---|
| **pytest** | Test runner | [docs.pytest.org](https://docs.pytest.org/) · [GitHub](https://github.com/pytest-dev/pytest) |
| **pytest-asyncio** | Async test support | [GitHub](https://github.com/pytest-dev/pytest-asyncio) |
| **pytest-cov** | Coverage reporting | [GitHub](https://github.com/pytest-dev/pytest-cov) |
| **httpx** | HTTP client used by Litestar's `AsyncTestClient` | [python-httpx.org](https://www.python-httpx.org/) · [GitHub](https://github.com/encode/httpx) |
| **cryptography** | RSA keypair generation in tests (transitively comes via `pyjwt[crypto]`) | [GitHub](https://github.com/pyca/cryptography) |

### External services consumed

- [`https://oauth.telegram.org/js/telegram-login.js`](https://core.telegram.org/bots/telegram-login#using-the-telegram-login-library) — Telegram's OIDC JS widget (loaded in `tg_auth/presentors/rest/templates/index.html`).
- [`https://oauth.telegram.org/.well-known/jwks.json`](https://core.telegram.org/bots/telegram-login#manual-implementation) — JWKS for ID-token signature verification.
- [`https://oauth.telegram.org`](https://core.telegram.org/bots/telegram-login#openid-connect) — `iss` claim that we validate against.

## Authentication flow

This repo uses the **JS-library** variant of Telegram OIDC. The full Authorization-Code-with-PKCE round trip happens **inside the popup window served by `oauth.telegram.org`** — your backend never makes a `POST /token` call. You only validate the resulting JWT.

```
                              ┌──────────────────────────────────┐
                              │  Browser (your origin)           │
                              │                                  │
1. user opens /               │  GET /                           │
                              │  ← HTML with telegram-login.js   │
2. user clicks button         │                                  │
                              │  popup → oauth.telegram.org/auth │
                              │                                  │
3. inside popup: Telegram     │  …user approves login…           │
   does its own /auth → /token│                                  │
   exchange and signs an      │  popup posts back via            │
   id_token (JWT)             │  postMessage({ id_token, user }) │
                              │                                  │
4. your JS posts JWT to       │  POST /api/v1/auth/telegram      │
   the backend                │       { id_token: "<jwt>" }      │
                              └────────────────┬─────────────────┘
                                               │
                              ┌────────────────▼─────────────────┐
                              │  Backend (Litestar)              │
                              │                                  │
5. fetch JWKS once, cache     │  PyJWKClient.get_signing_key…    │
6. verify JWT signature +     │  jwt.decode(                     │
   iss/aud/exp/iat            │      id_token, key,              │
                              │      issuer="…oauth.telegram…",  │
                              │      audience=APP_TG_CLIENT_ID)  │
                              │                                  │
7. upsert User + TelegramAcc  │  upsert_user_from_claims(claims) │
                              │                                  │
8. set signed-cookie session  │  request.session["user"] = {id}  │
                              │  ← 200 OK { UserDTO }            │
                              └──────────────────────────────────┘
```

What you don't have to do (and won't see in this code):

- **No `client_secret` handling** — that secret only matters for the server-side flow with a `code` exchange. The JS popup performs the exchange internally.
- **No PKCE bookkeeping** for the same reason.
- **No redirect-URI dance** — the popup posts back via `postMessage`, not via a top-level redirect.

If you ever need to switch to the server-side flow (e.g. for a non-browser client), the building blocks in `domain/use_cases/upsert_user_from_telegram.py` (the JWT validator) are unchanged — only the route layer would gain a `/auth/telegram/login` redirect endpoint and a `/auth/telegram/callback` token-exchange endpoint.

## Project layout

```
tg_auth/
├── __main__.py                          # `python -m tg_auth` — uvicorn entrypoint
│
├── application/                         # App-level scaffolding (no I/O, no HTTP)
│   ├── config.py                        # AppConfig dataclasses, all env vars
│   └── logging.py                       # structlog setup + LoggingConfig
│
├── domains/                             # Business logic, no I/O imports
│   ├── di.py                            # DomainProvider — wires use cases
│   ├── uow.py                           # AbstractUow protocol
│   ├── entities/                        # Plain dataclass DTOs
│   │   ├── healthcheck.py               # HealthcheckResult / HealthcheckStatus
│   │   ├── telegram.py                  # TelegramAuthDTO (the id_token payload)
│   │   └── user.py                      # UserDTO (response shape)
│   ├── interfaces/                      # Protocols implemented by adapters
│   │   ├── healthcheck.py               # IHealthcheck
│   │   └── users.py                     # IUsersRepository
│   └── use_cases/                       # One class per action
│       ├── check_readiness.py           # parallel-fan-out over IHealthcheck list
│       ├── fetch_user_by_id.py          # session-restore lookup
│       └── upsert_user_from_telegram.py # validate JWT → upsert
│
├── adapters/                            # Outbound I/O — concrete implementations
│   ├── database/
│   │   ├── __main__.py                  # `python -m tg_auth.adapters.database upgrade head`
│   │   ├── alembic.ini
│   │   ├── base.py                      # DeclarativeBase + naming convention + mixins
│   │   ├── tables.py                    # User, TelegramAccount
│   │   ├── config.py                    # DatabaseConfig dataclass
│   │   ├── di.py                        # DatabaseProvider
│   │   ├── uow.py                       # SqlalchemyUow (transaction-per-use-case)
│   │   ├── utils.py                     # create_engine / create_sessionmaker
│   │   ├── repositories/
│   │   │   └── users.py                 # UsersRepository
│   │   └── migrations/
│   │       ├── env.py
│   │       └── versions/
│   │           └── 2026_05_10_191282743bea_initial_commit.py
│   └── healthcheck/
│       ├── database.py                  # DatabaseHealthcheck — implements IHealthcheck
│       └── di.py                        # HealthcheckProvider
│
└── presentors/                          # Inbound transports
    └── rest/
        ├── app_factory.py               # Litestar factory, Dishka container, rate limit
        ├── controllers/                 # HTTP handlers (thin — delegate to use cases)
        │   ├── auth.py                  # /, /api/v1/auth/{telegram,logout}, /app
        │   └── system.py                # /health/live, /health/ready
        └── templates/
            ├── index.html               # Login page
            └── app.html                 # Signed-in status page (CSS + Logout)

tests/
├── conftest.py                          # RSA keypair, fake JWKS, app/client fixtures
├── domains/use_cases/
│   └── test_jwt_verifier.py             # 6 cases: happy, empty, bad aud/iss, expired, missing claim
├── adapters/database/
│   └── test_users_repository.py         # 5 cases: upsert paths + uow lifecycle
└── presentors/rest/
    └── test_routes.py                   # 10 cases: full HTTP flow + self-heal + health + logout

.github/workflows/ci.yaml                # lint + typecheck + test
Dockerfile                               # multi-stage, non-root, uv-based
docker-compose.yaml                      # one-service compose with named SQLite volume
Makefile                                 # develop / test / lint / docker / migrate recipes
```

The split follows the layered / clean-architecture conventions used by [`andy-takker/example-litestar-service`](https://github.com/andy-takker/example-litestar-service):

- **`application/`** — config and logging. No HTTP, no I/O.
- **`domains/`** — entities, Protocols, use cases. The Protocols (`IUsersRepository`, `IHealthcheck`) are defined here; adapters implement them. `domains/` does not import `adapters/` directly.
- **`adapters/`** — outbound I/O. One subpackage per concern (`database/`, `healthcheck/`).
- **`presentors/rest/`** — Litestar app, controllers, templates.

`presentors` and `adapters` both depend on `domains`; `domains` depends on neither.

## HTTP routes

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Login page. Redirects to `/app` if the cookie session is valid; otherwise renders `index.html`. |
| `POST` | `/api/v1/auth/telegram` | Accepts `{ "id_token": "<jwt>" }` from the Telegram widget. Validates the JWT, upserts user + telegram-account, sets a cookie session **and** returns an access + refresh token pair. **Rate-limited.** |
| `POST` | `/api/v1/auth/refresh` | Accepts `{ "refresh_token": "<jwt>" }`. Validates it, confirms the user still exists, returns a new `TokenPair`. |
| `GET`  | `/api/v1/me` | Protected JSON endpoint. Requires `Authorization: Bearer <access_token>`. Returns `UserDTO`. |
| `POST` | `/api/v1/auth/logout` | Clears the cookie session. Returns 204. (Bearer tokens are stateless — clients discard them on logout.) |
| `GET`  | `/app` | HTML status page. Reads the cookie session, renders `app.html` with the user's name + phone + a Logout button. Self-heals stale sessions. |
| `GET`  | `/health/live` | Liveness probe — always 200 while the process is alive. |
| `GET`  | `/health/ready` | Readiness probe — fans out across registered `IHealthcheck` implementations (currently `DatabaseHealthcheck`). Returns 200 with per-component status, or 503 if anything is down. |

### `POST /api/v1/auth/telegram` — request/response

```http
POST /api/v1/auth/telegram
Content-Type: application/json

{ "id_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjE…" }
```

```http
HTTP/1.1 200 OK
Set-Cookie: session=…; HttpOnly; Secure; SameSite=Lax
Content-Type: application/json

{
  "user": {
    "id": "8f7c1e2a-…-…",
    "name": "Jane Doe",
    "phone_number": "+15551234567"
  },
  "tokens": {
    "access_token":  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9…",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9…",
    "token_type": "Bearer",
    "expires_in": 900
  }
}
```

Use `tokens.access_token` as `Authorization: Bearer …` on every API call. When the access token expires, exchange `tokens.refresh_token` at `POST /api/v1/auth/refresh` for a new pair. The cookie session is what keeps the HTML pages logged in; the tokens are for the JSON API.

Failure modes:

- `401 NotAuthorized` — JWT signature invalid, `aud` mismatch, expired, etc. Body contains the underlying PyJWT error message.
- `400` — payload didn't deserialize (missing `id_token`).
- `429 Too Many Requests` — rate limit exceeded.

The `id_token`'s claims that we read:

| Claim | Used as |
|---|---|
| `sub` (required) / `id` | Telegram user numeric id |
| `name` | `User.name` and `TelegramAccount.name` |
| `preferred_username` | `TelegramAccount.username` |
| `picture` | `TelegramAccount.picture` (URL) |
| `phone_number` | `User.phone_number` and `TelegramAccount.phone_number` (only if user granted the `phone` scope) |
| `iss`, `aud`, `exp`, `iat` | validated, not stored |

## Database schema

```
┌───────────────────┐         ┌───────────────────────────────┐
│ users             │         │ telegram_accounts             │
├───────────────────┤         ├───────────────────────────────┤
│ id           UUID │◄────────┤ user_id        UUID  FK       │
│ phone_number TEXT │ unique  │ telegram_id    BIGINT unique  │
│ name         TEXT │         │ username       TEXT           │
│ created_at   …    │         │ name           TEXT           │
│ updated_at   …    │         │ picture        TEXT           │
│ deleted_at   …    │         │ phone_number   TEXT           │
└───────────────────┘         │ id, created_at, updated_at, … │
                              └───────────────────────────────┘
```

Two tables, one purposeful piece of duplication:

- `users` is the **canonical user** of the application. `phone_number` is unique-indexed because it will be the lookup key when SMS auth is added later.
- `telegram_accounts` holds **provider-specific** facts. `telegram_id` is unique. The relationship is `user → many telegram_accounts` even though in practice it's typically 1:1.
- `phone_number` is mirrored on both sides intentionally:
  - `users.phone_number` is "the phone of this app user" — the cross-channel key.
  - `telegram_accounts.phone_number` is "what Telegram returned to us at login time" — for audit and provenance.

`upsert_user_from_claims` (in `repositories/users.py`) implements the linking logic:

1. Find existing `TelegramAccount` by `telegram_id` → reuse its user.
2. Else find existing `User` by `phone_number` → link a new `TelegramAccount` to it.
3. Else create a new `User` and a new `TelegramAccount`.

Step 2 is what enables the "register via SMS first, then later add Telegram" path (and vice versa) without orphaning duplicate users.

## Setup

### 1. Configure your Telegram bot

You need a Telegram bot that represents your application.

1. Open [@BotFather](https://t.me/botfather) → create a bot or pick an existing one.
2. Open the **BotFather mini-app** (not the chat). Navigate to **Bot Settings → Web Login**.
3. **Trusted Origins** — add the origin that will host the login page (e.g. `https://your-subdomain.ngrok-free.app`). Origin only — no path, no trailing slash.
4. **Redirect URIs** — leave empty for the JS-library flow used here. Only needed if you implement the server-side `/auth` → `/token` exchange yourself.
5. Copy the **Client ID** that BotFather shows.

The legacy `/setdomain` command applies to the old widget, not OIDC — ignore it.

### 2. Environment variables

Create `.env` (gitignored) from `.env.dev`:

```bash
APP_TG_CLIENT_ID=8506301481                       # the Client ID from BotFather
APP_SECRET_KEY=replace-me-with-32-bytes-for-aes-key   # signs the cookie session (must be 16/24/32 bytes)
APP_DB_URL=sqlite+aiosqlite:///./tg_auth.db       # default; override for Postgres
APP_DEBUG=true
```

Generate a session secret. Litestar's `CookieBackendConfig` uses the secret as an AES key, so it **must be exactly 16, 24, or 32 bytes long** — pick 32:

```bash
python3 -c "import secrets; print(secrets.token_hex(16))"   # 32 hex chars = 32 bytes
```

The same `Client ID` must match `data-client-id` in `tg_auth/presentors/rest/templates/index.html`.

### 3. ngrok (or any HTTPS tunnel)

Telegram's OIDC popup will only `postMessage` back to **HTTPS** origins listed in BotFather. Plain `http://localhost:8080` won't work.

```bash
ngrok http 8000
```

Take the HTTPS URL (e.g. `https://random-string.ngrok-free.app`) and add it to **Trusted Origins** in BotFather. On free ngrok the subdomain rotates on every restart — update BotFather each time, or pay for a static domain.

## Running locally

```bash
make develop                 # creates .venv, installs deps via uv, sets up pre-commit
make migrate                 # apply alembic migrations
make run                     # runs `python -m tg_auth` on $APP_HTTP_PORT (default 8000)
```

Or step by step:

```bash
source .venv/bin/activate
python -m tg_auth.adapters.database upgrade head
python -m tg_auth
```

## Running with Docker

```bash
make docker-up               # docker compose up (foreground)
# in another terminal:
ngrok http 8000
```

`docker-compose.yaml` maps `:8000`, mounts a named volume `tg-auth-data` for the SQLite file, and configures a Docker healthcheck against `/health/ready`.

To wipe the database and start fresh:

```bash
make docker-down-volumes
```

The image is multi-stage based on `python:3.13-slim` and runs as a non-root user (`UID=10001`).

## Tests

```bash
make test                    # run pytest locally
make test-ci                 # with coverage + junit.xml (used by CI)
```

What's covered:

- **Domain — JWT verifier** (`tests/domains/use_cases/test_jwt_verifier.py`): happy path, empty token, wrong audience, wrong issuer, expired, missing required claim. Tests sign tokens with a generated RSA keypair and feed them to a fake `PyJWKClient` so the real validation logic runs end-to-end.
- **Adapter — repository** (`tests/adapters/database/test_users_repository.py`): the four `upsert_user_from_claims` branches — brand new user, returning user (mutable fields refresh), link-by-phone to a pre-existing user, phone-backfill on subsequent login — plus a `SqlalchemyUow` lifecycle smoke test.
- **Integration — HTTP** (`tests/presentors/rest/test_routes.py`): full request/response roundtrip via `litestar.testing.AsyncTestClient`. Login happy path, invalid token (401), `/app` rendering, redirects, logout, **stale-session self-heal**, `/health/live`, `/health/ready`.

The fake `PyJWKClient` is wired in via `create_app(config, jwks_client=...)` — the same parameter is available in production code if you ever need a custom client.

## Continuous integration

GitHub Actions runs three jobs in parallel on every push and PR:

- **Lint** — `ruff check` + `ruff format --check`.
- **Typecheck** — `mypy` against `./tg_auth`.
- **Tests** — `pytest` with coverage + JUnit XML; both uploaded as workflow artifacts.

All three use [`astral-sh/setup-uv@v3`](https://github.com/astral-sh/setup-uv) with caching, so a cached run takes ~30 s.

Configuration: [`.github/workflows/ci.yaml`](.github/workflows/ci.yaml).

## Troubleshooting

**Popup opens but `onTelegramAuth` never fires.**
Almost always one of: (a) origin not in BotFather → Trusted Origins, (b) you served `Cross-Origin-Opener-Policy: same-origin` (which blocks popup `postMessage`). Litestar doesn't set COOP by default; check upstream proxies.

**`401 Invalid id_token: Audience doesn't match`.**
`APP_TG_CLIENT_ID` is not the same as `data-client-id` in `index.html`.

**`401 Invalid id_token: Signature verification failed`.**
JWKS cache went stale across a key rotation. Restart the process (cache lives in-memory) or wait for `lifespan=600` to refresh.

**`429 Too Many Requests` during testing.**
You hit the auth rate limit (30 req/min/IP). Wait or temporarily relax `RateLimitConfig` in `app_factory.py`.

**`/app` redirects to `/` despite a fresh login.**
The session cookie points to a user UUID that's not in the DB (e.g. you deleted `tg_auth.db` after authing). The route self-heals: it clears the cookie and bounces to `/`. Hit `/` again and re-login.

**Migrations fail on Postgres after switching DSN.**
The shipped migration is dialect-agnostic — no `gen_random_uuid()` server defaults. UUIDs are generated Python-side via `uuid.uuid4`. If you fork and add Postgres-specific defaults later, update both `base.py` and the migration so they match.

## Limitations

This is a PoC. Things to be aware of before copying it into something larger:

- JWKS cache and rate-limit store are in-process. For multi-replica deployments swap the store for `litestar.stores.redis`.
- No CSRF token on the JSON auth endpoint. The cookie is set by the same request that returns it; SameSite=Lax + HttpOnly is the only protection.
- Cookie session has a fixed 30-day TTL. No refresh / sliding logic.
- Prometheus extras are installed via Litestar but no `/metrics` endpoint is wired.
- On schema reset the in-process JWKS cache may serve stale keys for up to 10 minutes — restart the process if it matters.

## Extending it

### Adding SMS auth later

The schema is already shaped for it:

1. New use case `upsert_user_from_phone(phone)` that mirrors `upsert_user_from_claims`:
   - find `User` by `phone_number` → reuse;
   - else create one.
2. New routes `POST /api/v1/auth/sms/start` (issues an OTP) and `POST /api/v1/auth/sms/verify` (calls the use case and sets the same cookie session).
3. A user who logged in via Telegram first (and granted phone) will have `users.phone_number` set, so the SMS flow finds them automatically. A user who started with SMS will have `users.phone_number` set too, and a later Telegram login will reuse the row via step 2 of `upsert_user_from_claims`.

No schema changes needed.

### Switching to Postgres

1. Set `APP_DB_URL=postgresql+asyncpg://user:pass@host/db`.
2. Add `asyncpg` to `pyproject.toml` dependencies.
3. Run `python -m tg_auth.adapters.database upgrade head` against the new DSN.

The `pool_size`/`max_overflow`/`pool_timeout` settings in `DatabaseConfig` start mattering at this point — `aiosqlite` ignores them.

### Frontend integration

The `index.html` in this repo is intentionally bare. In a real SPA you'd:

1. Render the `<script src="…oauth.telegram.org/js/telegram-login.js">` and the `<button class="tg-auth-button">` from your own component.
2. Wire `data-onauth` to a function that POSTs the `id_token` to your backend.
3. After 200 OK, navigate / refetch user state.

Backend stays the same.

## License

MIT — see [LICENSE](LICENSE).

The Dockerfile and CI scaffolding are inspired by [andy-takker/example-litestar-service](https://github.com/andy-takker/example-litestar-service).
