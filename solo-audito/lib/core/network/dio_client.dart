import 'package:dio/dio.dart';

import '../config/api_config.dart';
import '../storage/secure_storage.dart';

Dio createDio(TokenStorage storage, Future<void> Function() onUnauthorized) {
  final dio = Dio(
    BaseOptions(
      baseUrl: ApiConfig.baseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 120),
      sendTimeout: const Duration(seconds: 60),
    ),
  );
  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        try {
          if (options.extra['public'] != true) {
            final token = await storage.read();
            if (token != null) {
              options.headers['Authorization'] = 'Bearer $token';
            }
          }
          handler.next(options);
        } catch (error) {
          handler.reject(DioException(requestOptions: options, error: error));
        }
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401 &&
            error.requestOptions.extra['public'] != true) {
          try {
            final currentToken = await storage.read();
            if (error.requestOptions.headers['Authorization'] ==
                'Bearer $currentToken') {
              await onUnauthorized();
            }
          } catch (_) {
            // Always complete the failed request, even if secure storage fails.
          }
        }
        handler.next(error);
      },
    ),
  );
  return dio;
}
