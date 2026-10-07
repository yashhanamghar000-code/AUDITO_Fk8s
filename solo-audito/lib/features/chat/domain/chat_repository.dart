import 'chat_models.dart';

abstract interface class ChatRepository {
  Future<List<Conversation>> conversations();
  Future<List<ChatMessage>> history(int userId, String session);
  Future<ChatMessage> send(String query, String session);
  // Add a separate Stream<ChatEvent> contract when the backend supports streaming.
}
