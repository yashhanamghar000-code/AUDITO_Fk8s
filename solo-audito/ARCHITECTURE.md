# Architecture

```text
Flutter UI
    ↓
Riverpod controllers/providers
    ↓
Domain repository interfaces
    ↓
API repository implementations
    ↓
API services
    ↓
Dio (timeouts, secure bearer interceptor)
    ↓
Audito public backend / existing gateway
    ↓
Auth / RAG / Documents / LLM services
```

Widgets render state and invoke controllers; no widget constructs an HTTP request or contains a URL. Auth and chat each have domain models/interfaces, API service adapters, repositories and presentation state. Lightweight home/profile/history screens reuse those providers. Dependencies are composed with Riverpod and can be overridden in tests without a live backend.

`core/config` owns public origin and literal API paths. The origin is validated at bootstrap to prevent duplicated `/api` or accidental credentials. `core/network` creates Dio with bounded timeouts, attaches credentials only to protected requests and translates errors into user-facing messages. It deliberately does not automatically retry mutations. `core/storage` defines replaceable token storage backed by flutter_secure_storage. `core/theme` persists only appearance in shared_preferences.

Auth restores via `/api/auth/me`. A protected 401 clears the local session; a restoration transport/503 error retains the token and shows a retry screen. Login/register 401 errors stay on the form. Logout attempts the existing server endpoint and then clears local credentials, including offline. The server has no refresh or revocation API. GoRouter observes auth state to guard all app routes. The app never treats a locally present token as proof of a verified user.

The shell retains the current chat across tabs; it is disposed on logout. Chat generations prevent late requests from writing into a newly opened conversation. The current backend returns a single JSON answer; introduce a separate stream event repository method when an actual streaming endpoint exists. Sessions use random client identifiers, matching the web ownership model. An empty session is local until the backend persists work. Text-only persisted history has no citations; current answers render the citations actually returned by the server.

The presentation is Material 3 with a shared seed palette, responsive bounded content, scrollable forms, rounded cards and semantic controls. Wider previews keep readable content widths. Native Android/iOS and web share all Dart source; no dart:io dependencies or platform-only networking.

Phase two should add a documents domain/repository, session-scoped file listing, file_picker selection, cancellable multipart upload progress and bounded ingestion polling. Confirm task ownership protections on upload status before relying on task IDs as private resources. Add authenticated PDF viewing separately. Avoid moving server parsing, retrieval or model logic into this client.
