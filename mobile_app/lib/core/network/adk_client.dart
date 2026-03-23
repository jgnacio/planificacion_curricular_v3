import 'package:dio/dio.dart';
import '../config/app_config.dart';

class AdkClient {
  AdkClient._() : _dio = Dio(BaseOptions(baseUrl: AppConfig.adkBaseUrl));

  static final AdkClient instance = AdkClient._();

  final Dio _dio;

  /// Creates a session on the ADK server (idempotent — 409 is OK).
  Future<void> createSession(String userId, String sessionId) async {
    try {
      await _dio.post(
        '/apps/${AppConfig.adkAppName}/users/$userId/sessions',
        data: {'sessionId': sessionId},
      );
    } on DioException catch (e) {
      // 409 = already exists → fine
      if (e.response?.statusCode != 409) rethrow;
    }
  }

  /// Sends a message to the ADK agent and returns the parsed text response.
  Future<String> sendMessage({
    required String userId,
    required String sessionId,
    required String text,
  }) async {
    final response = await _dio.post('/run', data: {
      'appName': AppConfig.adkAppName,
      'userId': userId,
      'sessionId': sessionId,
      'newMessage': {
        'role': 'user',
        'parts': [
          {'text': text}
        ],
      },
      'stateDelta': {},
    });
    return _parseAdkResponse(response.data);
  }

  /// Parses the ADK event array/object and extracts text content.
  static String _parseAdkResponse(dynamic data) {
    final buffer = StringBuffer();

    void processMessage(dynamic msg) {
      if (msg == null) return;
      // 1. Direct text
      if (msg is Map && msg['text'] is String) {
        buffer.write(msg['text']);
        return;
      }
      // 2. parts array
      if (msg is Map && msg['parts'] is List) {
        for (final p in msg['parts'] as List) {
          if (p is String) buffer.write(p);
          if (p is Map && p['text'] is String) buffer.write(p['text']);
        }
        return;
      }
      // 3. Nested content
      if (msg is Map && msg['content'] is Map) {
        final content = msg['content'] as Map;
        if (content['parts'] is List) {
          for (final p in content['parts'] as List) {
            if (p is Map && p['text'] is String) buffer.write(p['text']);
          }
          return;
        }
        if (content['text'] is String) {
          buffer.write(content['text']);
        }
      }
    }

    if (data is List) {
      for (final event in data) {
        processMessage(event);
      }
    } else {
      processMessage(data);
    }

    return buffer.toString().trim();
  }
}
