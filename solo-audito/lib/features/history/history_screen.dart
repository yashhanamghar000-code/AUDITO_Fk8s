import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/network/api_exception.dart';
import '../../shared/widgets/content_frame.dart';
import '../chat/presentation/chat_controller.dart';

class ConversationList extends ConsumerWidget {
  final int? limit;
  const ConversationList({super.key, this.limit});
  @override
  Widget build(BuildContext context, WidgetRef ref) => ref
      .watch(conversationsProvider)
      .when(
        loading: () => const Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: CircularProgressIndicator(),
          ),
        ),
        error: (e, _) => Column(
          children: [
            Text(ApiException.from(e).message),
            TextButton(
              onPressed: () => ref.invalidate(conversationsProvider),
              child: const Text('Retry'),
            ),
          ],
        ),
        data: (items) => items.isEmpty
            ? const Card(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    'Your conversations will appear here. Start with a document in AuditoAI.',
                  ),
                ),
              )
            : Column(
                children: items
                    .take(limit ?? items.length)
                    .map(
                      (c) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Card(
                          child: ListTile(
                            contentPadding: const EdgeInsets.symmetric(
                              horizontal: 18,
                              vertical: 8,
                            ),
                            leading: const Icon(
                              Icons.chat_bubble_outline_rounded,
                            ),
                            title: Text(
                              c.title,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                            subtitle: const Text('Continue conversation'),
                            trailing: const Icon(Icons.chevron_right),
                            onTap: () {
                              ref.read(chatProvider.notifier).open(c);
                              context.go('/chat');
                            },
                          ),
                        ),
                      ),
                    )
                    .toList(),
              ),
      );
}

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Conversations')),
    body: const ContentFrame(
      child: SingleChildScrollView(
        padding: EdgeInsets.all(20),
        child: ConversationList(),
      ),
    ),
  );
}
