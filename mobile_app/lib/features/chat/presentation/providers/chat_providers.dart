import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';
import '../../data/adk_chat_repository_impl.dart';
import '../../domain/adk_chat_repository.dart';
import '../../../../core/config/app_config.dart';

// ──────────────────────────────────────────────
// Repository
// ──────────────────────────────────────────────

final chatRepositoryProvider = Provider<AdkChatRepository>(
  (_) => const AdkChatRepositoryImpl(),
);

// ──────────────────────────────────────────────
// Session ID (generated once per app lifecycle)
// ──────────────────────────────────────────────

final sessionIdProvider = Provider<String>((_) => const Uuid().v4());

// ──────────────────────────────────────────────
// Chat message model
// ──────────────────────────────────────────────

enum MessageSender { user, ai }

class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.sender,
    required this.text,
    required this.timestamp,
    this.isError = false,
  });

  final String id;
  final MessageSender sender;
  final String text;
  final DateTime timestamp;
  final bool isError;
}

// ──────────────────────────────────────────────
// Chat state notifier
// ──────────────────────────────────────────────

class ChatNotifier extends StateNotifier<List<ChatMessage>> {
  ChatNotifier(this._repo, this._sessionId)
      : super([
          ChatMessage(
            id: 'welcome',
            sender: MessageSender.ai,
            text: 'Hola! Soy el Facilitador Docente EBI. Puedo ayudarte a planificar y gestionar tus clases basándome en el programa oficial de ANEP.\n\n¿En qué te ayudo hoy?\n\n[[Validar actividad]] [[Planificar clase nueva]] [[Ver mis planificaciones]]',
            timestamp: DateTime.now(),
          ),
        ]) {
    _initSession();
  }

  final AdkChatRepository _repo;
  final String _sessionId;
  bool _sessionCreated = false;
  bool _isTyping = false;

  bool get isTyping => _isTyping;

  Future<void> _initSession() async {
    try {
      await _repo.createSession(AppConfig.adkDefaultUserId, _sessionId);
      _sessionCreated = true;
    } catch (_) {
      // Will retry on first message
    }
  }

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) return;

    final userMsg = ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      sender: MessageSender.user,
      text: text,
      timestamp: DateTime.now(),
    );
    state = [...state, userMsg];
    _isTyping = true;
    state = state; // trigger rebuild

    try {
      if (!_sessionCreated) {
        await _repo.createSession(AppConfig.adkDefaultUserId, _sessionId);
        _sessionCreated = true;
      }

      final response = await _repo.sendMessage(
        userId: AppConfig.adkDefaultUserId,
        sessionId: _sessionId,
        text: text,
      );

      final aiText = response.isNotEmpty
          ? response
          : 'No pude generar una respuesta. ¿Podés reformular la consulta?';

      final aiMsg = ChatMessage(
        id: (DateTime.now().millisecondsSinceEpoch + 1).toString(),
        sender: MessageSender.ai,
        text: aiText,
        timestamp: DateTime.now(),
      );
      state = [...state, aiMsg];
    } catch (e) {
      final errMsg = ChatMessage(
        id: (DateTime.now().millisecondsSinceEpoch + 1).toString(),
        sender: MessageSender.ai,
        text: 'Hubo un error al comunicarme con el agente. Verificá que el servicio ADK esté activo en `${AppConfig.adkBaseUrl}`.',
        timestamp: DateTime.now(),
        isError: true,
      );
      state = [...state, errMsg];
    } finally {
      _isTyping = false;
      state = state;
    }
  }
}

final chatProvider =
    StateNotifierProvider<ChatNotifier, List<ChatMessage>>((ref) {
  final repo = ref.read(chatRepositoryProvider);
  final sessionId = ref.read(sessionIdProvider);
  return ChatNotifier(repo, sessionId);
});

final isTypingProvider = Provider<bool>((ref) {
  // Watch the notifier directly
  final notifier = ref.watch(chatProvider.notifier);
  return notifier.isTyping;
});
