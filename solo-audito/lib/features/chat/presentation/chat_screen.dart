import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../shared/widgets/brand_mark.dart';
import '../../../shared/widgets/content_frame.dart';
import 'chat_controller.dart';
import '../../documents/presentation/upload_document_sheet.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});
  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final input = TextEditingController();
  final scroll = ScrollController();
  @override
  void dispose() {
    input.dispose();
    scroll.dispose();
    super.dispose();
  }

  void send() {
    final text = input.text.trim();
    if (text.isEmpty || ref.read(chatProvider).busy) return;
    input.clear();
    ref.read(chatProvider.notifier).send(text);
  }

  @override
  Widget build(BuildContext context) {
    final chat = ref.watch(chatProvider);
    ref.listen(
      chatProvider,
      (_, next) => WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && scroll.hasClients) {
          scroll.animateTo(
            scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 250),
            curve: Curves.easeOut,
          );
        }
      }),
    );
    return Scaffold(
      appBar: AppBar(
        title: const Text('Ask Audito'),
        actions: [
          IconButton(
            tooltip: 'Upload document',
            onPressed: () => showUploadDocumentSheet(context, ref),
            icon: const Icon(Icons.upload_file),
          ),
          IconButton(
            tooltip: 'Chat history',
            onPressed: () => context.push('/history'),
            icon: const Icon(Icons.history_rounded),
          ),
          IconButton(
            tooltip: 'New chat',
            onPressed: () {
              input.clear();
              ref.read(chatProvider.notifier).newChat();
            },
            icon: const Icon(Icons.edit_square),
          ),
        ],
      ),
      body: ContentFrame(
        child: Column(
          children: [
            Expanded(
              child: chat.messages.isEmpty && !chat.busy
                  ? SingleChildScrollView(
                      padding: const EdgeInsets.all(28),
                      child: Column(
                        children: [
                          const SizedBox(height: 48),
                          const BrandMark(size: 72),
                          const SizedBox(height: 24),
                          Text(
                            'Make room for clarity.',
                            style: Theme.of(context).textTheme.headlineSmall,
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 12),
                          const Text(
                            'Ask a question about the documents in your conversation.',
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 28),
                          const Card(
                            child: Padding(
                              padding: EdgeInsets.all(20),
                              child: Text(
                                'Upload a document here or open an existing conversation. Once the document is ready, ask Audito a question.',
                              ),
                            ),
                          ),
                          const SizedBox(height: 16),
                          OutlinedButton.icon(
                            onPressed: () => context.push('/history'),
                            icon: const Icon(Icons.history),
                            label: const Text('Open a conversation'),
                          ),
                        ],
                      ),
                    )
                  : ListView.builder(
                      controller: scroll,
                      padding: const EdgeInsets.all(20),
                      itemCount: chat.messages.length + (chat.busy ? 1 : 0),
                      itemBuilder: (context, index) {
                        if (index == chat.messages.length) {
                          return const Padding(
                            padding: EdgeInsets.all(20),
                            child: Row(
                              children: [
                                SizedBox.square(
                                  dimension: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                ),
                                SizedBox(width: 12),
                                Text('Audito is thinking…'),
                              ],
                            ),
                          );
                        }
                        final message = chat.messages[index];
                        return Align(
                          alignment: message.isUser
                              ? Alignment.centerRight
                              : Alignment.centerLeft,
                          child: Container(
                            constraints: const BoxConstraints(maxWidth: 560),
                            margin: const EdgeInsets.only(bottom: 16),
                            padding: const EdgeInsets.all(18),
                            decoration: BoxDecoration(
                              color: message.isUser
                                  ? Theme.of(context)
                                        .colorScheme
                                        .primaryContainer
                                  : Theme.of(context)
                                        .colorScheme
                                        .surfaceContainer,
                              borderRadius: BorderRadius.circular(22),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  message.isUser ? 'YOU' : 'AUDITO',
                                  style: Theme.of(context).textTheme.labelSmall,
                                ),
                                const SizedBox(height: 8),
                                SelectableText(message.text),
                                if (message.citations.isNotEmpty) ...[
                                  const SizedBox(height: 14),
                                  Wrap(
                                    spacing: 8,
                                    runSpacing: 8,
                                    children: message.citations
                                        .map(
                                          (c) => ActionChip(
                                            avatar: const Icon(
                                              Icons.description_outlined,
                                              size: 16,
                                            ),
                                            label: Text(
                                              '${c.source}${c.page == null ? '' : ' · p. ${c.page}'}',
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                            onPressed: () =>
                                                showModalBottomSheet<void>(
                                                  context: context,
                                                  isScrollControlled: true,
                                                  builder: (context) => SafeArea(
                                                    child: SingleChildScrollView(
                                                      padding:
                                                          const EdgeInsets.all(
                                                            24,
                                                          ),
                                                      child: Column(
                                                        mainAxisSize:
                                                            MainAxisSize.min,
                                                        crossAxisAlignment:
                                                            CrossAxisAlignment
                                                                .start,
                                                        children: [
                                                          Text(
                                                            c.source,
                                                            style:
                                                                Theme.of(
                                                                      context,
                                                                    )
                                                                    .textTheme
                                                                    .titleLarge,
                                                          ),
                                                          if (c.page != null)
                                                            Text(
                                                              'Page ${c.page}',
                                                            ),
                                                          const SizedBox(
                                                            height: 12,
                                                          ),
                                                          SelectableText(
                                                            c.snippet ?? 'No source excerpt was returned.',
                                                          ),
                                                          const SizedBox(
                                                            height: 16,
                                                          ),
                                                          const Text(
                                                            'PDF viewing will be available in a later phase.',
                                                          ),
                                                        ],
                                                      ),
                                                    ),
                                                  ),
                                                ),
                                          ),
                                        )
                                        .toList(),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        );
                      },
                    ),
            ),
            if (chat.error != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Column(
                  children: [
                    Semantics(
                      liveRegion: true,
                      child: Text(
                        chat.error!,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    ),
                    if (chat.failedQuery != null)
                      TextButton(
                        onPressed: () async {
                          final retry = await showDialog<bool>(
                            context: context,
                            builder: (context) => AlertDialog(
                              title: const Text('Retry question?'),
                              content: const Text(
                                'If the previous request reached Audito, retrying may save the question twice.',
                              ),
                              actions: [
                                TextButton(
                                  onPressed: () =>
                                      Navigator.pop(context, false),
                                  child: const Text('Cancel'),
                                ),
                                FilledButton(
                                  onPressed: () => Navigator.pop(context, true),
                                  child: const Text('Retry'),
                                ),
                              ],
                            ),
                          );
                          if (retry == true && mounted) {
                            ref
                                .read(chatProvider.notifier)
                                .send(chat.failedQuery!, retry: true);
                          }
                        },
                        child: const Text('Retry'),
                      ),
                  ],
                ),
              ),
            SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Expanded(
                      child: TextField(
                        controller: input,
                        minLines: 1,
                        maxLines: 5,
                        textCapitalization: TextCapitalization.sentences,
                        decoration: const InputDecoration(
                          hintText: 'Ask about your documents…',
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    IconButton.filled(
                      tooltip: 'Send message',
                      onPressed: chat.busy ? null : send,
                      icon: const Icon(Icons.arrow_upward_rounded),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
