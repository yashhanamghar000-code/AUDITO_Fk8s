import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:solo_audito/app.dart';
import 'package:solo_audito/core/theme/app_theme.dart';
import 'package:solo_audito/features/auth/domain/auth_repository.dart';
import 'package:solo_audito/features/auth/domain/user.dart';
import 'package:solo_audito/features/auth/presentation/auth_controller.dart';
import 'package:solo_audito/features/chat/domain/chat_models.dart';
import 'package:solo_audito/features/chat/domain/chat_repository.dart';
import 'package:solo_audito/features/chat/presentation/chat_controller.dart';

class FakeAuth implements AuthRepository {
  AuditoUser? user;
  FakeAuth({this.user});
  @override
  Future<AuditoUser?> restore() async => user;
  @override
  Future<AuditoUser> login(String email, String password) async =>
      user = AuditoUser(id: 7, name: 'Sam', email: email);
  @override
  Future<AuditoUser> register(
    String name,
    String email,
    String password,
  ) async => user = AuditoUser(id: 7, name: name, email: email);
  @override
  Future<void> logout() async {
    user = null;
  }
}

class FakeChat implements ChatRepository {
  @override
  Future<List<Conversation>> conversations() async => [];
  @override
  Future<List<ChatMessage>> history(int userId, String session) async => [];
  @override
  Future<ChatMessage> send(String query, String session) async =>
      const ChatMessage(
        'An answer',
        citations: [Citation('Policy.pdf', page: '3')],
      );
}

Future<void> start(WidgetTester tester, {AuditoUser? user}) async {
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        preferencesProvider.overrideWithValue(prefs),
        authRepositoryProvider.overrideWithValue(FakeAuth(user: user)),
        chatRepositoryProvider.overrideWithValue(FakeChat()),
      ],
      child: const SoloAuditoApp(),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('signed-out route validates fields and supports registration', (
    tester,
  ) async {
    await start(tester);
    await tester.tap(find.widgetWithText(FilledButton, 'Login'));
    await tester.pumpAndSettle();
    expect(find.text('Enter a valid email'), findsOneWidget);
    await tester.ensureVisible(find.text('New here? Create account'));
    await tester.tap(find.text('New here? Create account'));
    await tester.pumpAndSettle();
    expect(find.text('Name'), findsOneWidget);
  });
  testWidgets('login reaches dashboard; theme and logout work', (tester) async {
    await start(tester);
    await tester.enterText(find.byType(TextFormField).at(0), 'sam@example.com');
    await tester.enterText(find.byType(TextFormField).at(1), 'password');
    await tester.tap(find.widgetWithText(FilledButton, 'Login'));
    await tester.pumpAndSettle();
    expect(find.text('Ask Audito'), findsOneWidget);
    await tester.tap(find.text('Profile'));
    await tester.pumpAndSettle();
    expect(find.text('sam@example.com'), findsOneWidget);
    await tester.tap(find.text('Dark'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Logout'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Logout'));
    await tester.pumpAndSettle();
    expect(find.text('Welcome back.'), findsOneWidget);
  });
  testWidgets('dashboard and chat fit a small phone and show citations', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 700);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await start(
      tester,
      user: const AuditoUser(id: 7, name: 'Sam', email: 'sam@example.com'),
    );
    expect(tester.takeException(), isNull);
    await tester.tap(find.text('Chat'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'What is covered?');
    await tester.tap(find.byTooltip('Send message'));
    await tester.pumpAndSettle();
    expect(find.text('An answer'), findsOneWidget);
    expect(find.text('Policy.pdf · p. 3'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
