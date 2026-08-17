# add-ai-frontend

The AUDITO AI web client — a TanStack Start (React + Vite + Nitro) SSR
app. Split out of the original monolith unchanged; it already read its
backend URL from `VITE_API_BASE_URL` (see `src/services/api.ts` and
`src/lib/citationApi.js`), so no code changes were needed to make this a
standalone repo — only a `Dockerfile` and compose files.

## Talks to
`add-ai-backend`'s HTTP API, at whatever URL `VITE_API_BASE_URL` points
to. This is a Vite **client-side** env var, so it's baked in at **build
time**, not read at container start — see the `ARG`/`ENV` combo in the
`Dockerfile`. Rebuild the image if you need to point at a different
backend URL.

## Run standalone (production build)
```bash
cp .env.example .env
docker compose up --build
# -> http://localhost:3000
```

## Local dev (hot reload, no Docker build step per change)
```bash
docker compose up --build
# -> http://localhost:5173, edits under src/ hot-reload immediately
```
or entirely outside Docker:
```bash
npm ci
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Testing
This repo didn't have a test suite in the original monolith. `npm run
lint` is the existing check:
```bash
npm run lint
```
