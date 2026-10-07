import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_exception.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/content_frame.dart';
import '../auth/presentation/auth_controller.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});
  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  bool busy = false;
  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authProvider).asData?.value;
    return Scaffold(
      appBar: AppBar(title: const Text('Your profile')),
      body: ContentFrame(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const SizedBox(height: 20),
            const CircleAvatar(
              radius: 40,
              child: Icon(Icons.person_outline, size: 40),
            ),
            const SizedBox(height: 20),
            Text(
              user?.name ?? '',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(user?.email ?? '', textAlign: TextAlign.center),
            const SizedBox(height: 32),
            Card(
              child: ListTile(
                leading: const Icon(Icons.verified_user_outlined),
                title: const Text('AuditoAI account'),
                subtitle: Text('Account ID: ${user?.id ?? ''}'),
              ),
            ),
            const SizedBox(height: 24),
            Text('Appearance', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              children: ThemeMode.values
                  .map(
                    (mode) => ChoiceChip(
                      label: Text(
                        mode.name[0].toUpperCase() + mode.name.substring(1),
                      ),
                      selected: ref.watch(themeProvider) == mode,
                      onSelected: (_) async {
                        try {
                          await ref.read(themeProvider.notifier).setMode(mode);
                        } catch (_) {
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text(
                                  'Could not save appearance preference.',
                                ),
                              ),
                            );
                          }
                        }
                      },
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: 40),
            OutlinedButton.icon(
              onPressed: busy
                  ? null
                  : () async {
                      setState(() => busy = true);
                      try {
                        await ref.read(authProvider.notifier).logout();
                      } catch (e) {
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(ApiException.from(e).message),
                            ),
                          );
                        }
                      } finally {
                        if (mounted) setState(() => busy = false);
                      }
                    },
              icon: const Icon(Icons.logout),
              label: Text(busy ? 'Signing out…' : 'Logout'),
            ),
          ],
        ),
      ),
    );
  }
}
