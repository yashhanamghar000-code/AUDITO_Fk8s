import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/network/api_exception.dart';
import '../../../shared/widgets/content_frame.dart';
import '../../chat/presentation/chat_controller.dart';
import '../domain/document_models.dart';
import 'conversation_selector.dart';
import 'document_controller.dart';
import 'upload_document_sheet.dart';

class DocumentsScreen extends ConsumerStatefulWidget {
  final String? initialSession;
  const DocumentsScreen({super.key, this.initialSession});
  @override
  ConsumerState<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends ConsumerState<DocumentsScreen> {
  late String session = widget.initialSession ?? ref.read(chatProvider).session;
  @override
  void didUpdateWidget(covariant DocumentsScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initialSession != null &&
        widget.initialSession != oldWidget.initialSession) {
      session = widget.initialSession!;
    }
  }

  @override
  Widget build(BuildContext context) {
    final documents = ref.watch(documentsProvider(session));
    return Scaffold(
      appBar: AppBar(
        title: const Text('My documents'),
        actions: [
          IconButton(
            tooltip: 'Refresh documents',
            onPressed: () => ref.invalidate(documentsProvider(session)),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: ContentFrame(
        child: RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(conversationsProvider);
            ref.invalidate(documentsProvider(session));
            try {
              await ref.read(documentsProvider(session).future);
            } catch (_) {
              /* The provider renders the error with retry. */
            }
          },
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(24),
            children: [
              ConversationSelector(
                selected: session,
                onChanged: (value) => setState(() => session = value),
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: () =>
                    showUploadDocumentSheet(context, ref, session: session),
                icon: const Icon(Icons.upload_file),
                label: const Text('Upload document'),
              ),
              const SizedBox(height: 24),
              documents.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (e, _) => Column(
                  children: [
                    Text(ApiException.from(e).message),
                    TextButton(
                      onPressed: () =>
                          ref.invalidate(documentsProvider(session)),
                      child: const Text('Retry'),
                    ),
                  ],
                ),
                data: (files) => files.isEmpty
                    ? const Card(
                        child: Padding(
                          padding: EdgeInsets.all(24),
                          child: Text(
                            'No documents in this conversation yet. Upload a document to begin.',
                          ),
                        ),
                      )
                    : Column(
                        children: files
                            .map(
                              (file) => Padding(
                                padding: const EdgeInsets.only(bottom: 12),
                                child: Card(
                                  child: ListTile(
                                    leading: Icon(
                                      file.ready
                                          ? Icons.task_alt
                                          : file.status == 'failed'
                                          ? Icons.error_outline
                                          : Icons.hourglass_top,
                                      color: file.status == 'failed'
                                          ? Theme.of(context).colorScheme.error
                                          : Theme.of(context)
                                                .colorScheme
                                                .primary,
                                    ),
                                    title: Text(file.name),
                                    subtitle: Text(
                                      '${file.label}${file.ready ? ' · ${file.chunks} chunks' : ''}',
                                    ),
                                    trailing: const Icon(Icons.chevron_right),
                                    onTap: () => details(file),
                                  ),
                                ),
                              ),
                            )
                            .toList(),
                      ),
              ),
              const SizedBox(height: 20),
              const Text(
                'Documents are grouped by conversation. Pull to refresh processing status.',
              ),
            ],
          ),
        ),
      ),
    );
  }

  void details(AuditoDocument file) => showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    builder: (sheetContext) => SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(file.name, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            Text(file.label),
            Text('${file.chunks} chunks indexed'),
            if (file.createdAt != null)
              Text(
                'Added ${file.createdAt!.toLocal().toString().split('.').first}',
              ),
            const SizedBox(height: 20),
            if (file.ready)
              FilledButton(
                onPressed: () {
                  Navigator.pop(sheetContext);
                  ref.read(chatProvider.notifier).activateSession(session);
                  context.go('/chat');
                },
                child: const Text('Ask Audito'),
              ),
          ],
        ),
      ),
    ),
  );
}
