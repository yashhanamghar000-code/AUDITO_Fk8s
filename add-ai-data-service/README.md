# add-ai-data-service

Owns the platform's one relational schema: `users`, `conversations`,
`chat_messages`, `uploaded_files`. Implements `IUserRepository`,
`IConversationRepository`, `IChatMessageRepository`, `IFileRepository`
from `add-ai-core`, exposed over HTTP. The only service on the platform
that opens a SQLAlchemy session against Postgres.

## Why one service, not four
These four tables have real foreign keys (deleting a conversation
cascades to its messages and files). Splitting each repository into its
own database would mean trading DB-enforced referential integrity for
application-level integrity checks — doable, but a genuine cost, not
just a refactor. If you outgrow this later, the natural next split is
`users` (identity) vs. `conversations/chat_messages/uploaded_files`
(chat data) as two services with two databases, since those two groups
don't share foreign keys with each other today... actually they do
(`conversations.user_id`) — so that split needs an app-level "does this
user_id exist" check instead of a DB foreign key. Worth doing only once
you actually need to scale or deploy them independently.

## API (selected)
- `POST /users`, `GET /users/by-email/{email}`, `GET /users/{id}`
- `POST /conversations/get-or-create`, `GET /conversations?user_id=`, `DELETE /conversations/{session_id}?user_id=`
- `POST /chat-messages/turn`, `GET /chat-messages/history?user_id=&session_id=`
- `POST /files/pending`, `PATCH /files/{id}/status`, `GET /files/{id}?user_id=`, `DELETE /files/{id}?user_id=`, `GET /files?user_id=&session_id=`

## Run standalone (spins up its own Postgres)
```bash
cp .env.example .env
docker compose up --build
```

## Local dev
Live-reload override, same pattern as the other services.

## Migrations
This repo currently uses `Base.metadata.create_all()` (create-if-missing,
like the original monolith) — fine for a fresh dev DB, not a real
migration tool. If you add/change a column on a live database, either
add a hand-written `ALTER TABLE` or bring in Alembic here; nothing
outside this repo needs to know either way.
