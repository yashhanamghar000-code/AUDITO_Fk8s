import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../shared/widgets/brand_mark.dart';
import '../../shared/widgets/content_frame.dart';
import '../auth/presentation/auth_controller.dart';
import '../history/history_screen.dart';
import '../documents/presentation/upload_document_sheet.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).asData?.value;
    final hour = DateTime.now().hour;
    final greeting = hour < 12
        ? 'Good morning'
        : hour < 18
        ? 'Good afternoon'
        : 'Good evening';
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            BrandMark(size: 32),
            SizedBox(width: 10),
            Flexible(
              child: Text('Solo Audito', overflow: TextOverflow.ellipsis),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Profile',
            onPressed: () => context.go('/profile'),
            icon: const Icon(Icons.account_circle_outlined),
          ),
        ],
      ),
      body: ContentFrame(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const SizedBox(height: 20),
            Text(
              '$greeting${user == null ? '' : ', ${user.name.split(' ').first}'}',
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'What can I help\nyou with?',
              style: Theme.of(context).textTheme.headlineLarge
                  ?.copyWith(fontWeight: FontWeight.w700, height: 1.15),
            ),
            const SizedBox(height: 28),
            Card(
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: () => context.go('/chat'),
                child: Ink(
                  decoration: const BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Color(0xFF7160DC), Color(0xFF47348F)],
                    ),
                  ),
                  padding: const EdgeInsets.all(26),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Icon(
                            Icons.auto_awesome_rounded,
                            color: Colors.white,
                            size: 32,
                          ),
                          Icon(Icons.north_east, color: Colors.white70),
                        ],
                      ),
                      const SizedBox(height: 30),
                      Text(
                        'Ask Audito',
                        style: Theme.of(context).textTheme.headlineSmall
                            ?.copyWith(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                            ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Turn your documents into understanding.',
                        style: TextStyle(color: Colors.white, height: 1.5),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: _QuickAction(
                    icon: Icons.upload_file_rounded,
                    title: 'Upload document',
                    subtitle: 'Build your knowledge',
                    onTap: () => showUploadDocumentSheet(context, ref),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: _QuickAction(
                    icon: Icons.folder_open_rounded,
                    title: 'My documents',
                    subtitle: 'Your knowledge',
                    onTap: () => context.go('/documents'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 30),
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Recent conversations',
                    style: Theme.of(context).textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold),
                  ),
                ),
                TextButton(
                  onPressed: () => context.push('/history'),
                  child: const Text('View all'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            const ConversationList(limit: 3),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}

class _QuickAction extends StatelessWidget {
  final IconData icon;
  final String title, subtitle;
  final VoidCallback onTap;
  const _QuickAction({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });
  @override
  Widget build(BuildContext context) => Card(
    clipBehavior: Clip.antiAlias,
    child: InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: Theme.of(context).colorScheme.primary, size: 28),
            const SizedBox(height: 20),
            Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    ),
  );
}
