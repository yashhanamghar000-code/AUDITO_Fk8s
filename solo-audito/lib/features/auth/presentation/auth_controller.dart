import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../../core/network/dio_client.dart';
import '../../../core/storage/secure_storage.dart';
import '../data/api_auth_repository.dart';
import '../data/auth_api_service.dart';
import '../domain/auth_repository.dart';
import '../domain/user.dart';

final tokenStorageProvider = Provider<TokenStorage>(
  (ref) => SecureTokenStorage(const FlutterSecureStorage()),
);
final dioProvider = Provider((ref) {
  final dio = createDio(
    ref.watch(tokenStorageProvider),
    () => ref.read(authProvider.notifier).expire(),
  );
  ref.onDispose(() => dio.close(force: true));
  return dio;
});
final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => ApiAuthRepository(
    AuthApiService(ref.watch(dioProvider)),
    ref.watch(tokenStorageProvider),
  ),
);
final authProvider = AsyncNotifierProvider<AuthController, AuditoUser?>(
  AuthController.new,
);

class AuthController extends AsyncNotifier<AuditoUser?> {
  @override
  Future<AuditoUser?> build() async {
    final repository = ref.watch(authRepositoryProvider);
    // Give the brand transition time to render without delaying slow restores.
    final results = await Future.wait<Object?>([
      repository.restore(),
      Future<void>.delayed(const Duration(milliseconds: 650)),
    ]);
    return results.first as AuditoUser?;
  }

  Future<void> submit(String email, String password, {String? name}) async {
    final repository = ref.read(authRepositoryProvider);
    final user = name == null
        ? await repository.login(email, password)
        : await repository.register(name, email, password);
    state = AsyncData(user);
  }

  Future<void> expire() async {
    try {
      await ref.read(tokenStorageProvider).clear();
    } finally {
      state = const AsyncData(null);
    }
  }

  Future<void> logout() async {
    await ref.read(authRepositoryProvider).logout();
    state = const AsyncData(null);
  }
}
