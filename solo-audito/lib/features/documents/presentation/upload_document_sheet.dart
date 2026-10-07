import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/network/api_exception.dart';
import '../../chat/presentation/chat_controller.dart';
import '../data/document_picker.dart';
import '../domain/document_models.dart';
import 'conversation_selector.dart';
import 'document_controller.dart';

final documentPickerProvider = Provider<DocumentPicker>(
  (ref) => NativeDocumentPicker(),
);

enum UploadDestination { chat, documents }

class UploadResult {
  final String session;
  final UploadDestination destination;
  const UploadResult(this.session, this.destination);
}

Future<void> showUploadDocumentSheet(
  BuildContext context,
  WidgetRef ref, {
  String? session,
}) async {
  final result = await showModalBottomSheet<UploadResult>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (_) => UploadDocumentSheet(
      initialSession: session ?? ref.read(chatProvider).session,
    ),
  );
  if (result == null || !context.mounted) return;
  if (result.destination == UploadDestination.chat) {
    ref.read(chatProvider.notifier).activateSession(result.session);
    context.go('/chat');
  } else {
    context.go(
      Uri(
        path: '/documents',
        queryParameters: {'session': result.session},
      ).toString(),
    );
  }
}

class UploadDocumentSheet extends ConsumerStatefulWidget {
  final String initialSession;
  const UploadDocumentSheet({super.key, required this.initialSession});
  @override
  ConsumerState<UploadDocumentSheet> createState() =>
      _UploadDocumentSheetState();
}

class _UploadDocumentSheetState extends ConsumerState<UploadDocumentSheet> {
  late String session = widget.initialSession;
  SelectedDocument? file;
  bool picking = false;
  String? selectionError;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) pick();
    });
  }

  Future<void> pick() async {
    if (picking) return;
    setState(() {
      picking = true;
      selectionError = null;
    });
    try {
      final selected = await ref.read(documentPickerProvider).pick();
      if (!mounted) return;
      if (selected == null) {
        setState(
          () => selectionError =
              'No file selected. Choose a document when you are ready.',
        );
      } else {
        file = selected;
        ref.read(uploadProvider.notifier).select(selected, session);
      }
    } catch (e) {
      if (mounted) {
        setState(() => selectionError = ApiException.from(e).message);
      }
    } finally {
      if (mounted) setState(() => picking = false);
    }
  }

  void finish(UploadDestination destination, String target) =>
      Navigator.pop(context, UploadResult(target, destination));
  @override
  Widget build(BuildContext context) {
    final upload = ref.watch(uploadProvider);
    final ready = upload.phase == UploadPhase.ready;
    final editable = upload.phase == UploadPhase.selecting;
    final scheme = Theme.of(context).colorScheme;
    return SafeArea(
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * .82,
        child: SingleChildScrollView(
          padding: EdgeInsets.fromLTRB(
            24,
            0,
            24,
            24 + MediaQuery.viewInsetsOf(context).bottom,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      ready ? 'Document ready' : 'Upload document',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                  ),
                  IconButton(
                    tooltip: 'Close upload',
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              if (editable) ...[
                const Text('PDF, TXT or DOCX · up to 200 MB'),
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  onPressed: picking ? null : pick,
                  icon: const Icon(Icons.attach_file),
                  label: Text(
                    picking
                        ? 'Opening files...'
                        : file == null
                        ? 'Choose document'
                        : 'Choose a different file',
                  ),
                ),
              ],
              if (file != null) ...[
                const SizedBox(height: 16),
                Card(
                  child: ListTile(
                    leading: Icon(
                      ready
                          ? Icons.check_circle_outline
                          : Icons.description_outlined,
                      color: scheme.primary,
                    ),
                    title: Text(file!.name),
                    subtitle: Text(file!.sizeLabel),
                  ),
                ),
              ],
              const SizedBox(height: 24),
              if (editable) ...[
                ConversationSelector(
                  selected: session,
                  enabled: !picking,
                  onChanged: (value) {
                    setState(() => session = value);
                    if (file != null) {
                      ref.read(uploadProvider.notifier).select(file!, session);
                    }
                  },
                  onNew: () {
                    ref.read(chatProvider.notifier).newChat();
                    setState(() => session = ref.read(chatProvider).session);
                    if (file != null) {
                      ref.read(uploadProvider.notifier).select(file!, session);
                    }
                  },
                ),
                const SizedBox(height: 8),
                const Text(
                  'Audito will use this document when you ask questions in the selected conversation.',
                ),
                const SizedBox(height: 24),
              ],
              if (upload.busy) ...[
                Semantics(
                  liveRegion: true,
                  child: Text(
                    upload.label,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                const SizedBox(height: 16),
                LinearProgressIndicator(
                  value: upload.phase == UploadPhase.uploading
                      ? upload.progress
                      : null,
                ),
                const SizedBox(height: 20),
                Text(
                  upload.phase == UploadPhase.uploading
                      ? 'Keep this sheet open until the upload is queued. Closing stops the transfer; check Documents before uploading again.'
                      : 'You can close this sheet. Processing continues on Audito; refresh Documents to check readiness.',
                ),
              ],
              if (selectionError != null || upload.error != null)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  child: Semantics(
                    liveRegion: true,
                    child: Text(
                      selectionError ?? upload.error!,
                      style: TextStyle(color: scheme.error),
                    ),
                  ),
                ),
              if (editable)
                FilledButton.icon(
                  onPressed:
                      picking || file == null || file!.validationError != null
                      ? null
                      : () => ref.read(uploadProvider.notifier).upload(),
                  icon: const Icon(Icons.cloud_upload_outlined),
                  label: const Text('Confirm upload'),
                ),
              if (upload.phase == UploadPhase.paused) ...[
                FilledButton(
                  onPressed: () => ref.read(uploadProvider.notifier).resume(),
                  child: const Text('Check status again'),
                ),
                TextButton(
                  onPressed: () =>
                      finish(UploadDestination.documents, upload.session!),
                  child: const Text('View Documents'),
                ),
              ],
              if (upload.phase == UploadPhase.failed) ...[
                Text(
                  upload.receipt != null
                      ? 'Processing failed'
                      : 'Upload did not complete',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 12),
                if (upload.receipt == null)
                  const Text(
                    'The server may have received the file before the connection failed. Check Documents before sending it again.',
                  ),
                TextButton(
                  onPressed: () =>
                      finish(UploadDestination.documents, upload.session!),
                  child: const Text('View Documents'),
                ),
                OutlinedButton(
                  onPressed: () {
                    ref.read(uploadProvider.notifier).reset();
                    setState(() {
                      file = null;
                      selectionError = null;
                    });
                    pick();
                  },
                  child: const Text('Choose another document'),
                ),
              ],
              if (ready) ...[
                Semantics(
                  liveRegion: true,
                  child: Text(
                    upload.processing?.chunks == null
                        ? 'Your document is indexed and ready for questions.'
                        : '${upload.processing!.chunks} chunks indexed',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                const SizedBox(height: 24),
                FilledButton.icon(
                  onPressed: () =>
                      finish(UploadDestination.chat, upload.session!),
                  icon: const Icon(Icons.auto_awesome),
                  label: const Text('Ask Audito'),
                ),
                const SizedBox(height: 12),
                OutlinedButton(
                  onPressed: () =>
                      finish(UploadDestination.documents, upload.session!),
                  child: const Text('View Documents'),
                ),
                TextButton(
                  onPressed: () {
                    ref.read(uploadProvider.notifier).reset();
                    setState(() {
                      file = null;
                      selectionError = null;
                    });
                    pick();
                  },
                  child: const Text('Upload Another'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
