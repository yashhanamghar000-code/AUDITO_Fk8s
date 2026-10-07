import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/auth_controller.dart';
import '../../features/auth/presentation/auth_screen.dart';
import '../../features/chat/presentation/chat_controller.dart';
import '../../features/chat/presentation/chat_screen.dart';
import '../../features/documents/presentation/documents_screen.dart';
import '../../features/history/history_screen.dart';
import '../../features/home/home_screen.dart';
import '../../features/profile/profile_screen.dart';
import '../../features/splash/splash_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier(0);
  ref.listen(authProvider, (_, next) => refresh.value++);
  final router = GoRouter(
    initialLocation: '/splash',
    refreshListenable: refresh,
    redirect: (context, state) {
      final auth = ref.read(authProvider);
      final path = state.uri.path;
      if (auth.isLoading || auth.hasError) {
        return path == '/splash' ? null : '/splash';
      }
      final signedIn = auth.asData?.value != null;
      final public = path == '/login' || path == '/register';
      if (!signedIn) return public ? null : '/login';
      if (public || path == '/splash') return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, state) => const SplashScreen()),
      GoRoute(path: '/login', builder: (_, state) => const AuthScreen()),
      GoRoute(
        path: '/register',
        builder: (_, state) => const AuthScreen(register: true),
      ),
      ShellRoute(
        builder: (_, state, child) =>
            _MobileShell(path: state.uri.path, child: child),
        routes: [
          GoRoute(path: '/home', builder: (_, state) => const HomeScreen()),
          GoRoute(path: '/chat', builder: (_, state) => const ChatScreen()),
          GoRoute(
            path: '/documents',
            builder: (_, state) => DocumentsScreen(
              initialSession: state.uri.queryParameters['session'],
            ),
          ),
          GoRoute(
            path: '/profile',
            builder: (_, state) => const ProfileScreen(),
          ),
          GoRoute(
            path: '/history',
            builder: (_, state) => const HistoryScreen(),
          ),
        ],
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(
        child: TextButton(
          onPressed: () => context.go('/home'),
          child: const Text('Return home'),
        ),
      ),
    ),
  );
  ref.onDispose(() {
    router.dispose();
    refresh.dispose();
  });
  return router;
});

class _MobileShell extends ConsumerWidget {
  final String path;
  final Widget child;
  const _MobileShell({required this.path, required this.child});
  static const paths = ['/home', '/chat', '/documents', '/profile'];
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(
      chatProvider,
    ); // Retain the active conversation across tabs; reset on logout.
    final index = paths.indexOf(path);
    return Scaffold(
      body: child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: index < 0 ? 1 : index,
        onDestinationSelected: (i) => context.go(paths[i]),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home_rounded),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline_rounded),
            selectedIcon: Icon(Icons.chat_bubble_rounded),
            label: 'Chat',
          ),
          NavigationDestination(
            icon: Icon(Icons.folder_outlined),
            selectedIcon: Icon(Icons.folder_rounded),
            label: 'Documents',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person_rounded),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}
