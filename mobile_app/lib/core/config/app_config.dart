class AppConfig {
  AppConfig._();

  // Override at build time:
  //   flutter run --dart-define=ADK_URL=http://192.168.1.49:8000
  //   flutter run --dart-define=API_URL=http://192.168.1.49:8001
  static const String adkBaseUrl = String.fromEnvironment(
    'ADK_URL',
    defaultValue: 'http://192.168.1.49:8000',
  );

  static const String apiBaseUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://192.168.1.49:8001',
  );

  static const String adkAppName = 'teacher_agent';
  static const String adkDefaultUserId = 'docente_default';
}
