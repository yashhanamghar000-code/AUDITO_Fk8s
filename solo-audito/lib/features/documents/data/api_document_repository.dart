import '../../../core/network/api_exception.dart';
import '../domain/document_models.dart';
import '../domain/document_repository.dart';
import 'document_api_service.dart';

class ApiDocumentRepository implements DocumentRepository {
  final DocumentApiService api;
  ApiDocumentRepository(this.api);
  @override
  Future<QueuedUpload> upload(
    SelectedDocument file,
    String session, {
    required void Function(int, int) onProgress,
    required DocumentCancellation cancellation,
  }) async {
    final error = file.validationError;
    if (error != null) throw ApiException(error);
    if (session.trim().isEmpty) {
      throw const ApiException('Choose a conversation before uploading.');
    }
    return QueuedUpload.fromJson(
      await api.upload(file, session, onProgress, cancellation),
    );
  }

  @override
  Future<ProcessingStatus> status(
    String task, {
    required DocumentCancellation cancellation,
  }) async => ProcessingStatus.fromJson(await api.status(task, cancellation));
  @override
  Future<List<AuditoDocument>> list(
    String session, {
    required DocumentCancellation cancellation,
  }) async => ((await api.list(session, cancellation))['files'] as List)
      .map((e) => AuditoDocument.fromJson(Map<String, dynamic>.from(e as Map)))
      .toList();
}
