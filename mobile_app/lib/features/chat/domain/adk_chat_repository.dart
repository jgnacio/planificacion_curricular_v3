abstract class AdkChatRepository {
  Future<void> createSession(String userId, String sessionId);
  Future<String> sendMessage({
    required String userId,
    required String sessionId,
    required String text,
  });
}
