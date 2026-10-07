import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'app.dart';
import 'core/config/api_config.dart';
import 'core/theme/app_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    ApiConfig.validate();
    final preferences = await SharedPreferences.getInstance();
    runApp(
      ProviderScope(
        overrides: [preferencesProvider.overrideWithValue(preferences)],
        child: const SoloAuditoApp(),
      ),
    );
  } catch (_) {
    runApp(
      const MaterialApp(
        home: Scaffold(
          body: Center(
            child: Padding(
              padding: EdgeInsets.all(24),
              child: Text(
                'Solo Audito could not start. Check API_BASE_URL and local storage access, then restart.',
              ),
            ),
          ),
        ),
      ),
    );
  }
}
