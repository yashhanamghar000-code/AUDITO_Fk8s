import 'package:dio/dio.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_exception.dart';
import '../domain/document_models.dart';

class DocumentApiService {
  final Dio dio;
  DocumentApiService(this.dio);
  Future<T> _request<T>(
    DocumentCancellation cancellation,
    Future<T> Function(CancelToken) action,
  ) async {
    final token = CancelToken();
    final remove = cancellation.listen(
      () => token.cancel('Document view closed'),
    );
    try {
      return await action(token);
    } finally {
      remove();
    }
  }

  Future<Map<String, dynamic>> upload(
    SelectedDocument file,
    String session,
    void Function(int, int) onProgress,
    DocumentCancellation cancellation,
  ) => _request(cancellation, (token) async {
    final part = file.bytes != null
        ? MultipartFile.fromBytes(file.bytes!, filename: file.name)
        : file.path != null
        ? await MultipartFile.fromFile(file.path!, filename: file.name)
        : MultipartFile.fromStream(
            file.readStream!,
            file.size,
            filename: file.name,
          );
    if (part.length == 0) throw const ApiException('Uploaded file is empty.');
    if (part.length > SelectedDocument.maxBytes) {
      throw const ApiException('Choose a document smaller than 200 MB.');
    }
    final response = await dio.post(
      ApiConfig.upload,
      data: FormData.fromMap({'session_id': session, 'file': part}),
      cancelToken: token,
      onSendProgress: onProgress,
      options: Options(
        sendTimeout: const Duration(minutes: 10),
        receiveTimeout: const Duration(seconds: 60),
      ),
    );
    return Map<String, dynamic>.from(response.data as Map);
  });
  Future<Map<String, dynamic>> status(
    String task,
    DocumentCancellation cancellation,
  ) => _request(
    cancellation,
    (token) async => Map<String, dynamic>.from(
      (await dio.get(
            ApiConfig.uploadStatus(task),
            cancelToken: token,
            options: Options(receiveTimeout: const Duration(seconds: 20)),
          )).data
          as Map,
    ),
  );
  Future<Map<String, dynamic>> list(
    String session,
    DocumentCancellation cancellation,
  ) => _request(
    cancellation,
    (token) async => Map<String, dynamic>.from(
      (await dio.get(ApiConfig.documents(session), cancelToken: token)).data
          as Map,
    ),
  );
}
