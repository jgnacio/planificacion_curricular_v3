import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'features/dashboard/presentation/screens/dashboard_screen.dart';

void main() {
  runApp(const ProviderScope(child: EbiApp()));
}

class EbiApp extends StatelessWidget {
  const EbiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Facilitador Docente EBI',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      home: const DashboardScreen(),
    );
  }
}
