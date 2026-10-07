import '../domain/chat_models.dart';
import '../domain/chat_repository.dart';
import 'chat_api_service.dart';

class ApiChatRepository implements ChatRepository {
  final ChatApiService api;
  ApiChatRepository(this.api);
  @override
  Future<List<Conversation>> conversations() async =>
      ((await api.conversations())['conversations'] as List)
          .map(
            (e) => Conversation.fromJson(Map<String, dynamic>.from(e as Map)),
          )
          .toList();
  @override
  Future<List<ChatMessage>> history(int userId, String session) async =>
      ((await api.history(userId, session))['history'] as List)
          .map(
            (e) =>
                ChatMessage(e['text'] as String, isUser: e['sender'] == 'user'),
          )
          .toList();
  @override
  Future<ChatMessage> send(String query, String session) async {
    final json = await api.send(query, session);
    return ChatMessage(
      json['response'] as String,
      citations: (json['citations'] as List? ?? [])
          .map((e) => Citation.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
    );
  }
}
