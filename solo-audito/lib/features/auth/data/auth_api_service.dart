import 'package:dio/dio.dart';

import '../../../core/config/api_config.dart';

class AuthApiService {
  final Dio dio;
  AuthApiService(this.dio);
  Future<Map<String, dynamic>> authenticate(
    String path,
    Map<String, String> data,
  ) async => Map<String, dynamic>.from(
    (await dio.post(
          path,
          data: data,
          options: Options(extra: {'public': true}),
        )).data
        as Map,
  );
  Future<Map<String, dynamic>> me() async =>
      Map<String, dynamic>.from((await dio.get(ApiConfig.me)).data as Map);
  Future<void> logout() async {
    await dio.post(ApiConfig.logout);
  }
}
