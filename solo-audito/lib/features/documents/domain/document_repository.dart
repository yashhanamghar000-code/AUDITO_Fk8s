import 'document_models.dart';

abstract interface class DocumentRepository {
  Future<QueuedUpload> upload(
    SelectedDocument file,
    String session, {
    required void Function(int sent, int total) onProgress,
    required DocumentCancellation cancellation,
  });
  Future<ProcessingStatus> status(
    String task, {
    required DocumentCancellation cancellation,
  });
  Future<List<AuditoDocument>> list(
    String session, {
    required DocumentCancellation cancellation,
  });
}
