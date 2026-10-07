import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_exception.dart';
import '../../shared/widgets/brand_mark.dart';
import '../auth/presentation/auth_controller.dart';

class SplashScreen extends ConsumerWidget {
  const SplashScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TweenAnimationBuilder<double>(
                tween: Tween(begin: .75, end: 1),
                duration: const Duration(milliseconds: 800),
                builder: (context, value, child) =>
                    Transform.scale(scale: value, child: child),
                child: const BrandMark(size: 88),
              ),
              const SizedBox(height: 24),
              Text(
                'Solo Audito',
                style: Theme.of(context).textTheme.headlineLarge,
              ),
              const SizedBox(height: 8),
              const Text('Powered by AuditoAI'),
              const SizedBox(height: 32),
              if (auth.hasError) ...[
                Text(
                  ApiException.from(auth.error!).message,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: () => ref.invalidate(authProvider),
                  child: const Text('Retry connection'),
                ),
              ] else
                const CircularProgressIndicator(),
            ],
          ),
        ),
      ),
    );
  }
}
