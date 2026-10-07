import 'package:dio/dio.dart';

import '../../../core/config/api_config.dart';
import '../../../core/storage/secure_storage.dart';
import '../domain/auth_repository.dart';
import '../domain/user.dart';
import 'auth_api_service.dart';

class ApiAuthRepository implements AuthRepository {
  final AuthApiService api;
  final TokenStorage storage;
  ApiAuthRepository(this.api, this.storage);
  @override
  Future<AuditoUser?> restore() async {
    if (await storage.read() == null) return null;
    try {
      return AuditoUser.fromJson(await api.me());
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        await storage.clear();
        return null;
      }
      rethrow;
    }
  }

  Future<AuditoUser> _authenticate(
    String path,
    Map<String, String> data,
  ) async {
    final result = await api.authenticate(path, data);
    final user = AuditoUser.fromJson(
      Map<String, dynamic>.from(result['user'] as Map),
    );
    final token = result['token'] as String;
    if (token.isEmpty) {
      throw const FormatException('Empty authentication token');
    }
    await storage.write(token);
    return user;
  }

  @override
  Future<AuditoUser> login(String email, String password) =>
      _authenticate(ApiConfig.login, {'email': email, 'password': password});
  @override
  Future<AuditoUser> register(String name, String email, String password) =>
      _authenticate(ApiConfig.register, {
        'name': name,
        'email': email,
        'password': password,
      });
  @override
  Future<void> logout() async {
    try {
      await api.logout();
    } catch (_) {
      /* Local sign-out works offline. */
    }
    await storage.clear();
  }
}
