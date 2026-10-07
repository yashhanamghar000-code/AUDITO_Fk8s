import 'user.dart';

abstract interface class AuthRepository {
  Future<AuditoUser?> restore();
  Future<AuditoUser> login(String email, String password);
  Future<AuditoUser> register(String name, String email, String password);
  Future<void> logout();
}
