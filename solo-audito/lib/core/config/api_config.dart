class ApiConfig {
  static const baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://auditoai.online',
  );
  static const login = '/api/auth/login';
  static const register = '/api/auth/register';
  static const me = '/api/auth/me';
  static const logout = '/api/auth/logout';
  static const chat = '/api/chat';
  static const upload = '/api/upload';
  static String uploadStatus(String task) =>
      '/api/upload/status/${Uri.encodeComponent(task)}';
  static String documents(String session) =>
      '/api/conversations/${Uri.encodeComponent(session)}/files';
  static const conversations = '/api/conversations';
  static String history(int userId, String session) =>
      '/api/chat/history/$userId/${Uri.encodeComponent(session)}';
  static void validate() {
    final uri = Uri.tryParse(baseUrl);
    if (uri == null ||
        !['http', 'https'].contains(uri.scheme) ||
        uri.host.isEmpty ||
        (uri.path.isNotEmpty && uri.path != '/') ||
        uri.hasQuery ||
        uri.hasFragment ||
        uri.userInfo.isNotEmpty) {
      throw ArgumentError(
        'API_BASE_URL must be an HTTP(S) origin without /api, credentials or query parameters.',
      );
    }
  }
}
