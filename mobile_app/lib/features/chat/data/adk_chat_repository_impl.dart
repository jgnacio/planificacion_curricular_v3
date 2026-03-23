import '../domain/adk_chat_repository.dart';
import '../../../core/network/adk_client.dart';

class AdkChatRepositoryImpl implements AdkChatRepository {
  const AdkChatRepositoryImpl();

  @override
  Future<void> createSession(String userId, String sessionId) {
    return AdkClient.instance.createSession(userId, sessionId);
  }

  @override
  Future<String> sendMessage({
    required String userId,
    required String sessionId,
    required String text,
  }) {
    return AdkClient.instance.sendMessage(
      userId: userId,
      sessionId: sessionId,
      text: text,
    );
  }
}
