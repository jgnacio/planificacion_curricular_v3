import 'package:dio/dio.dart';
import '../config/app_config.dart';

class ApiClient {
  ApiClient._()
      : _dio = Dio(BaseOptions(
          baseUrl: AppConfig.apiBaseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 30),
        ));

  static final ApiClient instance = ApiClient._();

  final Dio _dio;

  Dio get dio => _dio;
}
