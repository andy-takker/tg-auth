# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Telegram OpenID Connect login via `oauth.telegram.org/js/telegram-login.js`.
- Server-side JWT (`id_token`) validation against Telegram's JWKS, with
  `iss` / `aud` / `exp` / `iat` checks.
- SQLAlchemy 2.0 async models for `User` and `TelegramAccount`. Phone is
  mirrored to both tables to support cross-channel linking with future SMS
  auth.
- Idempotent user upsert in `UsersRepository.upsert_user_from_claims`:
  reuse-by-`telegram_id`, link-by-`phone_number`, fallback to create.
- Dishka DI container with APP / REQUEST scopes.
- Cookie-backed signed session via Litestar's `CookieBackendConfig`.
- `/health/live` liveness probe and `/health/ready` readiness probe with a
  pluggable `IHealthcheck` adapter list (DB probe included).
- `POST /api/v1/auth/logout` endpoint that clears the cookie session.
- Stale-session self-heal: `/app` clears the cookie and redirects to `/`
  when the session points to a user that no longer exists in DB.
- CSS-styled status page at `/app` with logout button.
- In-memory rate limit on `/api/v1/auth/telegram` (30 req / min / IP).
- Test suite (pytest + pytest-asyncio): unit tests for the JWT verifier and
  the repository upsert paths, integration tests for every HTTP route.
- GitHub Actions CI: ruff, mypy, pytest with coverage.
- Multi-stage Dockerfile and `docker-compose.yaml` for local containerized run.
- MIT license.
