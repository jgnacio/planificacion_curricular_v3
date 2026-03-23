import '../../../core/network/api_client.dart';

class CurriculumRepository {
  CurriculumRepository();

  final _dio = ApiClient.instance.dio;

  Future<List<String>> getCiclos() async {
    final res = await _dio.get('/ciclos');
    return List<String>.from(res.data as List);
  }

  Future<List<String>> getEspacios(String ciclo) async {
    final res = await _dio.get('/espacios', queryParameters: {'ciclo': ciclo});
    return List<String>.from(res.data as List);
  }

  Future<List<String>> getUnidades(String espacio) async {
    final res = await _dio.get('/unidades', queryParameters: {'espacio': espacio});
    return List<String>.from(res.data as List);
  }

  Future<List<String>> getGrados(String ciclo) async {
    final res = await _dio.get('/grados', queryParameters: {'ciclo': ciclo});
    return List<String>.from(res.data as List);
  }

  Future<List<String>> getContenidos(String unidad, {String grado = ''}) async {
    final res = await _dio.get('/contenidos', queryParameters: {
      'unidad': unidad,
      if (grado.isNotEmpty) 'grado': grado,
    });
    return List<String>.from(res.data as List);
  }

  Future<List<Map<String, dynamic>>> getContenidoDetails(
    String contenido,
    String unidad,
  ) async {
    final res = await _dio.get('/contenido-details', queryParameters: {
      'contenido': contenido,
      'unidad': unidad,
    });
    return List<Map<String, dynamic>>.from(res.data as List);
  }
}
