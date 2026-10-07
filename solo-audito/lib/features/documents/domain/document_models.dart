import 'dart:typed_data';

class SelectedDocument {
  static const extensions = ['pdf', 'txt', 'docx'];
  static const maxBytes = 200 * 1024 * 1024;
  final String name;
  final int size;
  final String? path;
  final Uint8List? bytes;
  final Stream<List<int>> Function()? readStream;
  const SelectedDocument({
    required this.name,
    required this.size,
    this.path,
    this.bytes,
    this.readStream,
  });
  String? get validationError {
    if (name.trim().isEmpty) return 'Choose a named document.';
    if (!extensions.contains(name.split('.').last.toLowerCase())) {
      return 'Choose a PDF, TXT or DOCX document. Convert legacy DOC files to DOCX first.';
    }
    if (size <= 0 || (bytes != null && bytes!.isEmpty)) {
      return 'Uploaded file is empty.';
    }
    if (size > maxBytes) return 'Choose a document smaller than 200 MB.';
    if ((path == null || path!.isEmpty) &&
        bytes == null &&
        readStream == null) {
      return 'This file is unavailable. Please select it again.';
    }
    return null;
  }

  String get sizeLabel => size < 1024 * 1024
      ? '${(size / 1024).toStringAsFixed(1)} KB'
      : '${(size / (1024 * 1024)).toStringAsFixed(1)} MB';
}

class QueuedUpload {
  final String taskId, fileId;
  const QueuedUpload({required this.taskId, required this.fileId});
  factory QueuedUpload.fromJson(Map<String, dynamic> json) {
    final task = json['task_id']?.toString();
    final file = json['file_id']?.toString();
    if (json['status'] != 'queued' ||
        task == null ||
        task.isEmpty ||
        file == null ||
        file.isEmpty) {
      throw const FormatException(
        'The server did not return a valid upload receipt.',
      );
    }
    return QueuedUpload(taskId: task, fileId: file);
  }
}

enum ProcessingStage { pending, parsing, embedding, success, failure, unknown }

class ProcessingStatus {
  final ProcessingStage stage;
  final String? detail, fileName;
  final int? chunks;
  const ProcessingStatus(this.stage, {this.detail, this.fileName, this.chunks});
  factory ProcessingStatus.fromJson(Map<String, dynamic> json) {
    final stage = switch (json['state']) {
      'PENDING' => ProcessingStage.pending,
      'PARSING' => ProcessingStage.parsing,
      'EMBEDDING' => ProcessingStage.embedding,
      'SUCCESS' => ProcessingStage.success,
      'FAILURE' => ProcessingStage.failure,
      _ => ProcessingStage.unknown,
    };
    // The worker catches ingestion errors and returns status=failed, so Celery
    // may mark the task SUCCESS even when the document was not indexed.
    final failed = json['status'] == 'failed' || json['status'] == 'failure';
    return ProcessingStatus(
      failed ? ProcessingStage.failure : stage,
      detail: json['detail']?.toString(),
      fileName: json['file_name'] as String?,
      chunks: (json['total_chunks_indexed'] as num?)?.toInt(),
    );
  }
  bool get terminal =>
      stage == ProcessingStage.success || stage == ProcessingStage.failure;
  String get label => switch (stage) {
    ProcessingStage.pending => 'Waiting to process...',
    ProcessingStage.parsing => 'Reading document...',
    ProcessingStage.embedding => 'Creating searchable knowledge...',
    ProcessingStage.success => 'Document ready',
    ProcessingStage.failure => 'Processing failed',
    ProcessingStage.unknown => 'Processing document...',
  };
}

class AuditoDocument {
  final String id, name, status;
  final int chunks;
  final DateTime? createdAt;
  const AuditoDocument({
    required this.id,
    required this.name,
    required this.status,
    required this.chunks,
    this.createdAt,
  });
  factory AuditoDocument.fromJson(Map<String, dynamic> json) => AuditoDocument(
    id: json['id'].toString(),
    name: json['name'] as String,
    status: json['status'] as String,
    chunks: (json['total_chunks_indexed'] as num? ?? 0).toInt(),
    createdAt: DateTime.tryParse(json['created_at']?.toString() ?? ''),
  );
  bool get ready => status == 'indexed';
  String get label => ready
      ? 'Document ready'
      : status == 'failed'
      ? 'Processing failed'
      : 'Processing document...';
}

/// Transport-independent cancellation; listeners are removed after each request.
class DocumentCancellation {
  bool isCancelled = false;
  final _listeners = <void Function()>{};
  void Function() listen(void Function() callback) {
    if (isCancelled) {
      callback();
      return () {};
    }
    _listeners.add(callback);
    return () => _listeners.remove(callback);
  }

  void cancel() {
    if (isCancelled) return;
    isCancelled = true;
    for (final callback in _listeners.toList()) {
      callback();
    }
    _listeners.clear();
  }
}
