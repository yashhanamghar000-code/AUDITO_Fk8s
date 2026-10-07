class Citation {
  final String source;
  final String? page, fileId, snippet;
  const Citation(this.source, {this.page, this.fileId, this.snippet});
  factory Citation.fromJson(Map<String, dynamic> json) => Citation(
    json['source'] as String,
    page: json['page']?.toString(),
    fileId: json['file_id']?.toString(),
    snippet: json['snippet'] as String?,
  );
}

class ChatMessage {
  final String text;
  final bool isUser;
  final List<Citation> citations;
  const ChatMessage(
    this.text, {
    this.isUser = false,
    this.citations = const [],
  });
}

class Conversation {
  final String id, title;
  const Conversation(this.id, this.title);
  factory Conversation.fromJson(Map<String, dynamic> json) =>
      Conversation(json['session_id'] as String, json['title'] as String);
}
