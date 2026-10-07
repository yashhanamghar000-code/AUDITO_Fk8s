import 'dart:math';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_exception.dart';
import '../../auth/presentation/auth_controller.dart';
import '../data/api_chat_repository.dart';
import '../data/chat_api_service.dart';
import '../domain/chat_models.dart';
import '../domain/chat_repository.dart';

final chatRepositoryProvider = Provider<ChatRepository>(
  (ref) => ApiChatRepository(ChatApiService(ref.watch(dioProvider))),
);
final conversationsProvider = FutureProvider.autoDispose<List<Conversation>>((
  ref,
) {
  final user = ref.watch(authProvider).asData?.value;
  if (user == null) return [];
  return ref.watch(chatRepositoryProvider).conversations();
});

class ChatState {
  final String session;
  final List<ChatMessage> messages;
  final bool busy;
  final String? error, failedQuery;
  const ChatState(
    this.session, {
    this.messages = const [],
    this.busy = false,
    this.error,
    this.failedQuery,
  });
}

final chatProvider = NotifierProvider.autoDispose<ChatController, ChatState>(
  ChatController.new,
);

class ChatController extends Notifier<ChatState> {
  int generation = 0;
  bool disposed = false;
  String newId() => List.generate(
    16,
    (_) => Random.secure().nextInt(256).toRadixString(16).padLeft(2, '0'),
  ).join();
  @override
  ChatState build() {
    ref.watch(authProvider.select((auth) => auth.asData?.value?.id));
    disposed = false;
    generation++;
    ref.onDispose(() {
      disposed = true;
      generation++;
    });
    return ChatState(newId());
  }

  void newChat() {
    generation++;
    state = ChatState(newId());
  }

  void activateSession(String session) {
    if (state.session == session) return;
    open(Conversation(session, 'Conversation'));
  }

  Future<void> open(Conversation conversation) async {
    final user = ref.read(authProvider).asData?.value;
    if (user == null) return;
    final current = ++generation;
    state = ChatState(conversation.id, busy: true);
    try {
      final messages = await ref
          .read(chatRepositoryProvider)
          .history(user.id, conversation.id);
      if (!disposed && current == generation) {
        state = ChatState(conversation.id, messages: messages);
      }
    } catch (e) {
      if (!disposed && current == generation) {
        state = ChatState(conversation.id, error: ApiException.from(e).message);
      }
    }
  }

  Future<void> send(String query, {bool retry = false}) async {
    if (state.busy || query.trim().isEmpty) return;
    final current = generation;
    final session = state.session;
    final messages = [
      ...state.messages,
      if (!retry) ChatMessage(query.trim(), isUser: true),
    ];
    state = ChatState(session, messages: messages, busy: true);
    try {
      final answer = await ref
          .read(chatRepositoryProvider)
          .send(query.trim(), session);
      if (!disposed && current == generation) {
        state = ChatState(session, messages: [...messages, answer]);
        ref.invalidate(conversationsProvider);
      }
    } catch (e) {
      if (!disposed && current == generation) {
        state = ChatState(
          session,
          messages: messages,
          error: ApiException.from(e).message,
          failedQuery: query,
        );
      }
    }
  }
}
