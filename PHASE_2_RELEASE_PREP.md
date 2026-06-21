# Phase 2 Hardening + Release Prep

## Release scope (v2)

- User authentication with JWT and per-user data isolation
- Database-backed broker, portfolio, risk, and research routes
- WebSocket realtime updates for market and order events
- Frontend login/signup flow with protected app routes
- API contract export and runtime production safety checks

## Release checklist

1. Export OpenAPI schema:
   - `python scripts\export_openapi.py --output docs\api\openapi.json`
2. Validate tests:
   - `python -m pytest tests\integration -q`
   - `python -m pytest tests\unit -q`
3. Verify environment config:
   - `FASTAPI_ENV=production`
   - Strong `SECRET_KEY`
   - PostgreSQL `DATABASE_URL`
   - Correct `CORS_ORIGINS`
4. Confirm release docs and checkpoint files are current.

## Non-goals for this release

- Live broker execution
- Automated strategy execution
- Multi-broker routing
- Mobile app client

