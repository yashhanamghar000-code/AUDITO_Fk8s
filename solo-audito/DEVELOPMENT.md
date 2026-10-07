# Development

Start with README.md for SDK/PATH and API origin setup. Run `flutter run -d chrome`; press `r` for hot reload, `R` for restart and `q` to stop. Use a fixed `--web-port=7357` to preserve the browser origin between sessions. Restart after changing dart-defines. Android development needs an installed Android SDK/emulator; iOS compilation happens later on macOS.

## Current scope

Implemented: clean client layers, configurable Dio, secure auth/session handling, route guards, splash animation, real login/register, dashboard and bottom navigation, persisted appearance, backend profile and initial chat. Recent conversations and simple reopening use the discovered API so chat can be exercised with existing documents. Documents is explicitly a phase-two screen. No production services were started, reconfigured or modified during this work, and no real account was created for testing.

## Continue incrementally

1. Point the app at a staging Audito deployment and sign in with a test account. Verify restore/logout and expired JWT behavior on a real mobile device.
2. Add documents domain/API/repository/controller. Use multipart `/api/upload` with the active session ID and file, then poll `/api/upload/status/{task_id}` with cancellation and bounded backoff. Resolve the ownership limitation documented in the analysis before shipping that workflow.
3. List files with `/api/conversations/{session_id}/files`. Handle queued/failed/indexed states explicitly. Add authenticated file viewing and user-confirmed deletion.
4. Expand history with refresh and pagination only if supported; restore citations only when backend persistence is extended.
5. Add password recovery, notifications or streaming only after actual backend contracts exist. Do not create mobile-only auth or fake API paths.
6. Validate Android and iOS release signing, bundle IDs, secure storage behavior, accessibility, and lifecycle transitions before release.

## Tests

```bash
flutter pub get
dart format lib test
flutter analyze
flutter test
flutter run -d chrome --web-port=7357
```

Tests replace repositories or Dio's transport only inside test code. They check real auth envelopes, bearer headers, expiry vs outage behavior, offline logout, multipart chat/citations, navigation, form validation and a 320-pixel phone layout. They do not assert a live deployment is healthy.

## Validation record

Validated on Ubuntu with Flutter 3.47.2 / Dart 3.13.2:

- `flutter pub get`: passed; resolved versions recorded in pubspec.lock.
- `flutter analyze`: passed with no issues.
- `flutter test`: all 7 tests passed.
- `flutter build web --no-pub`: passed, including the compiler Wasm compatibility dry run (a separate Wasm runtime was not tested).
- `flutter run -d chrome --web-port=7357`: launched and connected to the debug service; Flutter reported starting the application main method.
- `flutter devices`: Chrome and Linux detected; no Android device. `flutter doctor -v` reports no Android SDK, so Android execution/build was not tested.
- iOS host generated and Keychain entitlements configured; compilation/signing not tested because Xcode requires macOS.
- Existing tracked repository files remain unchanged (`git diff --exit-code`).

Live authenticated backend behavior was not exercised with a real account. API integration was verified against discovered source contracts using isolated test transports. Chrome startup verification is not an end-to-end production login test.
