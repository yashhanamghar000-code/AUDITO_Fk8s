# add-ai-auth-service

Register / login / verify-token. Implements `IPasswordHasher` (bcrypt)
and `ITokenService` (JWT) from `add-ai-core`. Holds no database
connection of its own — calls `add-ai-data-service` over HTTP for user
lookup/creation. Only the bcrypt hash crosses that boundary, never the
plaintext password.

## API
- `POST /register` — `{name, email, password}` → `{token, user_id, name, email}`
- `POST /login` — `{email, password}` → same shape
- `POST /verify` — `{token}` → `{user_id, name, email}` (used by
  `add-ai-backend` on every authenticated request)

## Run standalone
Needs `add-ai-data-service` reachable — the bundled `docker-compose.yml`
builds/pulls it plus its own Postgres for you:
```bash
cp .env.example .env
docker compose up --build
curl -X POST localhost:8008/register -H 'content-type: application/json' \
  -d '{"name":"Ada","email":"ada@example.com","password":"hunter2"}'
```

## Local dev
Live-reload override, same pattern as the other services. Point
`DATA_SERVICE_URL` at whichever data-service instance you're running
(this repo's own compose, or the shared one in `add-ai-orchestration`).

## Swapping hashing/token schemes
Write new classes implementing `IPasswordHasher` / `ITokenService` (e.g.
argon2, opaque session tokens) and wire them into `app/main.py` — no
other repo needs to change.
