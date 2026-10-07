import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_exception.dart';
import '../../chat/presentation/chat_controller.dart';

class ConversationSelector extends ConsumerWidget {
  final String selected;
  final ValueChanged<String> onChanged;
  final bool enabled;
  final VoidCallback? onNew;
  const ConversationSelector({
    super.key,
    required this.selected,
    required this.onChanged,
    this.enabled = true,
    this.onNew,
  });
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final conversations = ref.watch(conversationsProvider);
    final options = <String, String>{
      selected: 'Current conversation (new)',
      for (final c in conversations.asData?.value ?? []) c.id: c.title,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DropdownButtonFormField<String>(
          key: ValueKey(selected),
          initialValue: selected,
          isExpanded: true,
          decoration: const InputDecoration(labelText: 'Conversation'),
          items: options.entries
              .map(
                (e) => DropdownMenuItem(
                  value: e.key,
                  child: Text(e.value, overflow: TextOverflow.ellipsis),
                ),
              )
              .toList(),
          onChanged: enabled
              ? (value) {
                  if (value != null) onChanged(value);
                }
              : null,
        ),
        if (conversations.isLoading)
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: LinearProgressIndicator(),
          ),
        if (conversations.hasError) ...[
          const SizedBox(height: 8),
          Text(ApiException.from(conversations.error!).message),
          TextButton(
            onPressed: () => ref.invalidate(conversationsProvider),
            child: const Text('Reload conversations'),
          ),
        ],
        if (onNew != null)
          TextButton.icon(
            onPressed: enabled ? onNew : null,
            icon: const Icon(Icons.add),
            label: const Text('New conversation'),
          ),
      ],
    );
  }
}
