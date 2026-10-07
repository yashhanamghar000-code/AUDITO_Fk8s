import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_exception.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../chat/presentation/chat_controller.dart';
import '../data/api_document_repository.dart';
import '../data/document_api_service.dart';
import '../domain/document_models.dart';
import '../domain/document_repository.dart';

final documentRepositoryProvider = Provider<DocumentRepository>(
  (ref) => ApiDocumentRepository(DocumentApiService(ref.watch(dioProvider))),
);
final documentsProvider = FutureProvider.autoDispose
    .family<List<AuditoDocument>, String>((ref, session) {
      final user = ref.watch(authProvider).asData?.value;
      if (user == null) return [];
      final cancellation = DocumentCancellation();
      ref.onDispose(cancellation.cancel);
      return ref
          .watch(documentRepositoryProvider)
          .list(session, cancellation: cancellation);
    });
final pollIntervalProvider = Provider<Duration>(
  (ref) => const Duration(seconds: 2),
);
final pollLimitProvider = Provider<int>(
  (ref) => 600,
); // 20 minutes, plus request time.

enum UploadPhase { selecting, uploading, processing, ready, failed, paused }

class UploadState {
  final UploadPhase phase;
  final SelectedDocument? file;
  final String? session, error;
  final QueuedUpload? receipt;
  final ProcessingStatus? processing;
  final double progress;
  const UploadState({
    this.phase = UploadPhase.selecting,
    this.file,
    this.session,
    this.error,
    this.receipt,
    this.processing,
    this.progress = 0,
  });
  bool get busy =>
      phase == UploadPhase.uploading || phase == UploadPhase.processing;
  String get label => phase == UploadPhase.uploading
      ? 'Uploading ${(progress * 100).round()}%'
      : processing?.label ?? 'Choose a document';
}

final uploadProvider =
    NotifierProvider.autoDispose<UploadController, UploadState>(
      UploadController.new,
    );

class UploadController extends Notifier<UploadState> {
  DocumentCancellation? _cancellation;
  Timer? _timer;
  int _generation = 0, _polls = 0;
  @override
  UploadState build() {
    ref.watch(authProvider.select((auth) => auth.asData?.value?.id));
    ref.onDispose(_cancel);
    return const UploadState();
  }

  void _cancel() {
    _generation++;
    _timer?.cancel();
    _cancellation?.cancel();
  }

  bool _current(int generation) => ref.mounted && generation == _generation;
  void select(SelectedDocument file, String session) {
    if (state.busy) return;
    _cancel();
    state = UploadState(
      file: file,
      session: session,
      error: file.validationError,
    );
  }

  void reset() {
    _cancel();
    state = const UploadState();
  }

  Future<void> upload() async {
    if (state.busy || state.file == null || state.session == null) return;
    final file = state.file!;
    final session = state.session!;
    if (file.validationError != null) {
      state = UploadState(
        file: file,
        session: session,
        error: file.validationError,
      );
      return;
    }
    _cancel();
    final generation = _generation;
    final cancellation = _cancellation = DocumentCancellation();
    state = UploadState(
      phase: UploadPhase.uploading,
      file: file,
      session: session,
    );
    try {
      final receipt = await ref
          .read(documentRepositoryProvider)
          .upload(
            file,
            session,
            cancellation: cancellation,
            onProgress: (sent, total) {
              if (_current(generation)) {
                state = UploadState(
                  phase: UploadPhase.uploading,
                  file: file,
                  session: session,
                  progress: total > 0 ? (sent / total).clamp(0.0, 1.0) : 0,
                );
              }
            },
          );
      if (!_current(generation)) return;
      state = UploadState(
        phase: UploadPhase.processing,
        file: file,
        session: session,
        receipt: receipt,
        progress: 1,
        processing: const ProcessingStatus(ProcessingStage.pending),
      );
      ref.invalidate(conversationsProvider);
      ref.invalidate(documentsProvider(session));
      _polls = 0;
      await _poll(generation);
    } catch (e) {
      if (_current(generation)) {
        state = UploadState(
          phase: UploadPhase.failed,
          file: file,
          session: session,
          error: ApiException.from(e).message,
        );
      }
    }
  }

  Future<void> _poll(int generation) async {
    if (!_current(generation)) return;
    final before = state;
    try {
      final status = await ref
          .read(documentRepositoryProvider)
          .status(before.receipt!.taskId, cancellation: _cancellation!);
      if (!_current(generation)) return;
      state = UploadState(
        phase: status.stage == ProcessingStage.success
            ? UploadPhase.ready
            : status.stage == ProcessingStage.failure
            ? UploadPhase.failed
            : UploadPhase.processing,
        file: before.file,
        session: before.session,
        receipt: before.receipt,
        processing: status,
        progress: 1,
        error: status.stage == ProcessingStage.failure
            ? status.detail ?? 'Processing failed. Please try another document.'
            : null,
      );
      if (status.terminal) {
        ref.invalidate(documentsProvider(before.session!));
        ref.invalidate(conversationsProvider);
        return;
      }
      _polls++;
      if (_polls >= ref.read(pollLimitProvider)) {
        _pause(
          'Processing is taking longer than expected. Check again or view your documents.',
        );
        return;
      }
      // Schedule only after the previous request completes: no overlapping polls.
      _timer = Timer(
        ref.read(pollIntervalProvider),
        () => unawaited(_poll(generation)),
      );
    } catch (e) {
      if (_current(generation)) _pause(ApiException.from(e).message);
    }
  }

  void _pause(String message) {
    final previous = state;
    state = UploadState(
      phase: UploadPhase.paused,
      file: previous.file,
      session: previous.session,
      receipt: previous.receipt,
      processing: previous.processing,
      progress: 1,
      error: message,
    );
  }

  Future<void> resume() async {
    if (state.phase != UploadPhase.paused || state.receipt == null) return;
    _cancel();
    _cancellation = DocumentCancellation();
    _polls = 0;
    final previous = state;
    state = UploadState(
      phase: UploadPhase.processing,
      file: previous.file,
      session: previous.session,
      receipt: previous.receipt,
      processing: previous.processing,
      progress: 1,
    );
    await _poll(_generation);
  }
}
