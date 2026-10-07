import 'dart:async';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:solo_audito/core/network/api_exception.dart';
import 'package:solo_audito/core/network/dio_client.dart';
import 'package:solo_audito/features/auth/domain/user.dart';
import 'package:solo_audito/features/auth/presentation/auth_controller.dart';
import 'package:solo_audito/features/chat/presentation/chat_controller.dart';
import 'package:solo_audito/features/documents/data/api_document_repository.dart';
import 'package:solo_audito/features/documents/data/document_api_service.dart';
import 'package:solo_audito/features/documents/domain/document_models.dart';
import 'package:solo_audito/features/documents/domain/document_repository.dart';
import 'package:solo_audito/features/documents/presentation/document_controller.dart';

import 'api_contract_test.dart' show Adapter, MemoryStorage, jsonResponse;
import 'widget_test.dart' show FakeAuth, FakeChat;

SelectedDocument fixture() => SelectedDocument(
  name: 'sample.txt',
  size: 4,
  bytes: Uint8List.fromList([116, 101, 115, 116]),
);

class FakeDocuments implements DocumentRepository {
  final List<ProcessingStatus> statuses;
  final Completer<QueuedUpload>? queued;
  int polls = 0, uploads = 0;
  String? uploadedSession;
  DocumentCancellation? cancellation;
  Object? statusError;
  FakeDocuments(this.statuses, {this.queued});
  @override
  Future<QueuedUpload> upload(
    SelectedDocument file,
    String session, {
    required void Function(int, int) onProgress,
    required DocumentCancellation cancellation,
  }) async {
    uploads++;
    uploadedSession = session;
    this.cancellation = cancellation;
    onProgress(24, 100);
    return queued == null
        ? const QueuedUpload(taskId: 'task', fileId: 'file')
        : queued!.future;
  }

  @override
  Future<ProcessingStatus> status(
    String task, {
    required DocumentCancellation cancellation,
  }) async {
    polls++;
    this.cancellation = cancellation;
    if (statusError != null) throw statusError!;
    return statuses[(polls - 1).clamp(0, statuses.length - 1)];
  }

  @override
  Future<List<AuditoDocument>> list(
    String session, {
    required DocumentCancellation cancellation,
  }) async => [];
}

Future<ProviderContainer> setup(FakeDocuments docs, {int limit = 10}) async {
  final container = ProviderContainer(
    overrides: [
      authRepositoryProvider.overrideWithValue(
        FakeAuth(
          user: const AuditoUser(id: 7, name: 'Sam', email: 'sam@example.com'),
        ),
      ),
      chatRepositoryProvider.overrideWithValue(FakeChat()),
      documentRepositoryProvider.overrideWithValue(docs),
      pollIntervalProvider.overrideWithValue(const Duration(milliseconds: 1)),
      pollLimitProvider.overrideWithValue(limit),
    ],
  );
  addTearDown(container.dispose);
  await container.read(authProvider.future);
  container.listen(uploadProvider, (_, next) {});
  container.listen(chatProvider, (_, next) {});
  return container;
}

Future<void> phase(ProviderContainer container, UploadPhase expected) async {
  final done = Completer<void>();
  final sub = container.listen(uploadProvider, (_, next) {
    if (next.phase == expected && !done.isCompleted) done.complete();
  }, fireImmediately: true);
  try {
    await done.future.timeout(const Duration(seconds: 3));
  } finally {
    sub.close();
  }
}

void main() {
  test('queued receipt requires task and file ids', () {
    final receipt = QueuedUpload.fromJson({
      'status': 'queued',
      'task_id': 'celery-id',
      'file_id': '42',
    });
    expect(receipt.taskId, 'celery-id');
    expect(receipt.fileId, '42');
    expect(
      () => QueuedUpload.fromJson({'status': 'queued'}),
      throwsFormatException,
    );
  });
  test(
    'all status states parse; worker failure inside SUCCESS is a failure',
    () {
      for (final entry in {
        'PENDING': ProcessingStage.pending,
        'PARSING': ProcessingStage.parsing,
        'EMBEDDING': ProcessingStage.embedding,
        'SUCCESS': ProcessingStage.success,
        'FAILURE': ProcessingStage.failure,
        'STARTED': ProcessingStage.unknown,
      }.entries) {
        expect(
          ProcessingStatus.fromJson({'state': entry.key}).stage,
          entry.value,
        );
      }
      final ready = ProcessingStatus.fromJson({
        'state': 'SUCCESS',
        'status': 'success',
        'file_name': 'sample.pdf',
        'total_chunks_indexed': 123,
      });
      expect(ready.chunks, 123);
      expect(ready.fileName, 'sample.pdf');
      expect(ready.terminal, isTrue);
      final failure = ProcessingStatus.fromJson({
        'state': 'SUCCESS',
        'status': 'failed',
        'detail': 'No text could be extracted.',
      });
      expect(failure.stage, ProcessingStage.failure);
      expect(failure.detail, 'No text could be extracted.');
    },
  );
  test('empty, legacy DOC and oversized files are rejected', () {
    expect(
      SelectedDocument(
        name: 'empty.txt',
        size: 0,
        bytes: Uint8List(0),
      ).validationError,
      'Uploaded file is empty.',
    );
    expect(
      const SelectedDocument(
        name: 'old.doc',
        size: 4,
        path: '/old.doc',
      ).validationError,
      contains('Convert legacy DOC'),
    );
    expect(
      const SelectedDocument(
        name: 'huge.pdf',
        size: SelectedDocument.maxBytes + 1,
        path: '/huge.pdf',
      ).validationError,
      contains('200 MB'),
    );
    expect(fixture().validationError, isNull);
  });
  test('HTTP backend detail preserved for chat/upload, including string JSON and 500', () {
    for (final status in [401, 404, 413, 422, 500]) {
      final error = DioException(
        requestOptions: RequestOptions(),
        response: Response(
          requestOptions: RequestOptions(),
          statusCode: status,
          data: {'detail': 'Uploaded file is empty.'},
        ),
      );
      expect(ApiException.from(error).message, 'Uploaded file is empty.');
    }
    final chatError = DioException(
      requestOptions: RequestOptions(),
      response: Response(
        requestOptions: RequestOptions(),
        statusCode: 404,
        data: '{"detail":"No documents are available in this conversation. Upload a document before asking a question."}',
      ),
    );
    expect(
      ApiException.from(chatError).message,
      startsWith('No documents are available'),
    );
    final network = DioException(
      requestOptions: RequestOptions(),
      type: DioExceptionType.connectionTimeout,
    );
    expect(
      ApiException.from(network).message,
      startsWith('Could not reach Audito'),
    );
    final http = DioException(
      requestOptions: RequestOptions(),
      response: Response(
        requestOptions: RequestOptions(),
        statusCode: 413,
        data: '<html>too large</html>',
      ),
    );
    expect(ApiException.from(http).message, contains('too large'));
  });
  test(
    'upload uses bearer, multipart file/session and actual API paths',
    () async {
      final storage = MemoryStorage()..token = 'jwt';
      final dio = createDio(storage, storage.clear);
      addTearDown(dio.close);
      dio.httpClientAdapter = Adapter((options) {
        expect(options.headers['Authorization'], 'Bearer jwt');
        if (options.path == '/api/upload') {
          final form = options.data as FormData;
          expect(Map.fromEntries(form.fields), {'session_id': 'real-session'});
          expect(form.files.single.key, 'file');
          expect(form.files.single.value.filename, 'sample.txt');
          expect(form.files.single.value.length, 4);
          return jsonResponse({
            'status': 'queued',
            'task_id': 'task/1',
            'file_id': '1',
          });
        }
        if (options.path == '/api/upload/status/task%2F1') {
          return jsonResponse({
            'state': 'SUCCESS',
            'total_chunks_indexed': 123,
          });
        }
        expect(options.path, '/api/conversations/real-session/files');
        return jsonResponse({
          'files': [
            {
              'id': '1',
              'name': 'sample.txt',
              'status': 'indexed',
              'total_chunks_indexed': 123,
              'created_at': null,
            },
          ],
        });
      });
      final repo = ApiDocumentRepository(DocumentApiService(dio));
      final cancellation = DocumentCancellation();
      final receipt = await repo.upload(
        fixture(),
        'real-session',
        onProgress: (_, total) {},
        cancellation: cancellation,
      );
      expect(
        (await repo.status(receipt.taskId, cancellation: cancellation)).chunks,
        123,
      );
      expect(
        (await repo.list(
          'real-session',
          cancellation: cancellation,
        )).single.ready,
        isTrue,
      );
    },
  );
  test('progress transitions to processing and success without changing active conversation', () async {
    final queued = Completer<QueuedUpload>();
    final docs = FakeDocuments([
      const ProcessingStatus(ProcessingStage.pending),
      const ProcessingStatus(ProcessingStage.parsing),
      const ProcessingStatus(ProcessingStage.embedding),
      const ProcessingStatus(ProcessingStage.success, chunks: 123),
    ], queued: queued);
    final container = await setup(docs);
    final chat = container.read(chatProvider.notifier);
    await chat.send('Existing question');
    final original = container.read(chatProvider);
    final upload = container.read(uploadProvider.notifier);
    upload.select(fixture(), original.session);
    final operation = upload.upload();
    expect(container.read(uploadProvider).progress, .24);
    expect(container.read(uploadProvider).label, 'Uploading 24%');
    queued.complete(const QueuedUpload(taskId: 'task', fileId: 'file'));
    await operation;
    await phase(container, UploadPhase.ready);
    expect(docs.uploadedSession, original.session);
    expect(docs.polls, 4);
    expect(container.read(uploadProvider).processing!.chunks, 123);
    chat.activateSession(original.session);
    expect(container.read(chatProvider).messages, original.messages);
    expect(container.read(chatProvider).session, original.session);
  });
  test('FAILURE is terminal and preserves backend detail', () async {
    final docs = FakeDocuments([
      const ProcessingStatus(
        ProcessingStage.failure,
        detail: 'Parser rejected document',
      ),
    ]);
    final container = await setup(docs);
    final upload = container.read(uploadProvider.notifier)
      ..select(fixture(), container.read(chatProvider).session);
    await upload.upload();
    expect(container.read(uploadProvider).phase, UploadPhase.failed);
    expect(container.read(uploadProvider).error, 'Parser rejected document');
    expect(docs.polls, 1);
  });
  test('poll outage resumes same receipt without uploading again', () async {
    final docs = FakeDocuments([
      const ProcessingStatus(ProcessingStage.success),
    ])..statusError = const ApiException('Temporary outage');
    final container = await setup(docs);
    final upload = container.read(uploadProvider.notifier)
      ..select(fixture(), container.read(chatProvider).session);
    await upload.upload();
    expect(container.read(uploadProvider).phase, UploadPhase.paused);
    expect(container.read(uploadProvider).receipt!.taskId, 'task');
    docs.statusError = null;
    await upload.resume();
    expect(container.read(uploadProvider).phase, UploadPhase.ready);
    expect(docs.uploads, 1);
  });
  test('polling has a bounded limit and disposal cancels transport', () async {
    final docs = FakeDocuments([
      const ProcessingStatus(ProcessingStage.pending),
    ]);
    final container = await setup(docs, limit: 2);
    final upload = container.read(uploadProvider.notifier)
      ..select(fixture(), container.read(chatProvider).session);
    await upload.upload();
    await phase(container, UploadPhase.paused);
    expect(docs.polls, 2);
    container.invalidate(uploadProvider);
    expect(docs.cancellation!.isCancelled, isTrue);
  });
  test('late queued response after reset cannot start polling', () async {
    final queued = Completer<QueuedUpload>();
    final docs = FakeDocuments([
      const ProcessingStatus(ProcessingStage.success),
    ], queued: queued);
    final container = await setup(docs);
    final upload = container.read(uploadProvider.notifier)
      ..select(fixture(), container.read(chatProvider).session);
    final pending = upload.upload();
    upload.reset();
    queued.complete(const QueuedUpload(taskId: 'late', fileId: 'late'));
    await pending;
    expect(docs.polls, 0);
    expect(container.read(uploadProvider).phase, UploadPhase.selecting);
  });
}
