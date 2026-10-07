import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:solo_audito/core/network/dio_client.dart';
import 'package:solo_audito/core/storage/secure_storage.dart';
import 'package:solo_audito/features/auth/data/api_auth_repository.dart';
import 'package:solo_audito/features/auth/data/auth_api_service.dart';
import 'package:solo_audito/features/chat/data/api_chat_repository.dart';
import 'package:solo_audito/features/chat/data/chat_api_service.dart';

class MemoryStorage implements TokenStorage {
  String? token;
  @override
  Future<String?> read() async => token;
  @override
  Future<void> write(String token) async {
    this.token = token;
  }

  @override
  Future<void> clear() async {
    token = null;
  }
}

class Adapter implements HttpClientAdapter {
  final ResponseBody Function(RequestOptions) handler;
  Adapter(this.handler);
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? stream,
    Future<void>? cancelFuture,
  ) async => handler(options);
  @override
  void close({bool force = false}) {}
}

ResponseBody jsonResponse(Object body, [int code = 200]) =>
    ResponseBody.fromString(
      jsonEncode(body),
      code,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
void main() {
  test(
    'auth consumes actual token envelope, attaches bearer and restores profile',
    () async {
      final storage = MemoryStorage();
      final dio = createDio(storage, storage.clear);
      addTearDown(dio.close);
      dio.httpClientAdapter = Adapter((options) {
        if (options.path == '/api/auth/login') {
          expect(options.data, {
            'email': 'sam@example.com',
            'password': 'secret',
          });
          expect(options.headers['Authorization'], isNull);
          return jsonResponse({
            'token': 'jwt',
            'user': {'id': 7, 'name': 'Sam', 'email': 'sam@example.com'},
          });
        }
        expect(options.path, '/api/auth/me');
        expect(options.headers['Authorization'], 'Bearer jwt');
        return jsonResponse({
          'id': 7,
          'name': 'Sam',
          'email': 'sam@example.com',
        });
      });
      final repo = ApiAuthRepository(AuthApiService(dio), storage);
      expect((await repo.login('sam@example.com', 'secret')).id, 7);
      expect(storage.token, 'jwt');
      expect((await repo.restore())?.name, 'Sam');
    },
  );
  test('401 clears expired tokens, 503 restoration preserves them', () async {
    final storage = MemoryStorage()..token = 'jwt';
    var expired = false;
    final dio = createDio(storage, () async {
      expired = true;
      await storage.clear();
    });
    addTearDown(dio.close);
    final repo = ApiAuthRepository(AuthApiService(dio), storage);
    dio.httpClientAdapter = Adapter(
      (_) => jsonResponse({'detail': 'unavailable'}, 503),
    );
    await expectLater(repo.restore(), throwsA(isA<DioException>()));
    expect(storage.token, 'jwt');
    dio.httpClientAdapter = Adapter(
      (_) => jsonResponse({'detail': 'expired'}, 401),
    );
    expect(await repo.restore(), isNull);
    expect(expired, isTrue);
    expect(storage.token, isNull);
  });
  test(
    'chat uses multipart query/session and maps real citation fields',
    () async {
      final dio = Dio();
      addTearDown(dio.close);
      dio.httpClientAdapter = Adapter((options) {
        expect(options.path, '/api/chat');
        expect(Map.fromEntries((options.data as FormData).fields), {
          'query': 'Coverage?',
          'session_id': 'session-1',
        });
        return jsonResponse({
          'response': 'Covered',
          'citations': [
            {
              'source': 'policy.pdf',
              'page': 4,
              'file_id': '2',
              'snippet': 'Policy text',
            },
          ],
        });
      });
      final answer = await ApiChatRepository(ChatApiService(dio))
          .send('Coverage?', 'session-1');
      expect(answer.text, 'Covered');
      expect(answer.citations.single.page, '4');
      expect(answer.citations.single.fileId, '2');
    },
  );
  test('offline logout still clears local credentials', () async {
    final storage = MemoryStorage()..token = 'jwt';
    final dio = createDio(storage, storage.clear);
    addTearDown(dio.close);
    dio.httpClientAdapter = Adapter((_) => jsonResponse({}, 503));
    await ApiAuthRepository(AuthApiService(dio), storage).logout();
    expect(storage.token, isNull);
  });
}
