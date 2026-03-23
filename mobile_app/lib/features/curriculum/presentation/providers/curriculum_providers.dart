import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/curriculum_repository_impl.dart';

final curriculumRepoProvider = Provider((_) => CurriculumRepository());

final ciclosProvider = FutureProvider<List<String>>((ref) {
  return ref.read(curriculumRepoProvider).getCiclos();
});

final selectedCicloProvider = StateProvider<String?>((ref) => null);
final selectedEspacioProvider = StateProvider<String?>((ref) => null);
final selectedUnidadProvider = StateProvider<String?>((ref) => null);
final selectedGradoProvider = StateProvider<String?>((ref) => null);
final selectedContenidoProvider = StateProvider<String?>((ref) => null);

final espaciosProvider = FutureProvider<List<String>>((ref) {
  final ciclo = ref.watch(selectedCicloProvider);
  if (ciclo == null) return Future.value([]);
  return ref.read(curriculumRepoProvider).getEspacios(ciclo);
});

final unidadesProvider = FutureProvider<List<String>>((ref) {
  final espacio = ref.watch(selectedEspacioProvider);
  if (espacio == null) return Future.value([]);
  return ref.read(curriculumRepoProvider).getUnidades(espacio);
});

final gradosProvider = FutureProvider<List<String>>((ref) {
  final ciclo = ref.watch(selectedCicloProvider);
  if (ciclo == null) return Future.value([]);
  return ref.read(curriculumRepoProvider).getGrados(ciclo);
});

final contenidosProvider = FutureProvider<List<String>>((ref) {
  final unidad = ref.watch(selectedUnidadProvider);
  final grado = ref.watch(selectedGradoProvider) ?? '';
  if (unidad == null) return Future.value([]);
  return ref.read(curriculumRepoProvider).getContenidos(unidad, grado: grado);
});

final contenidoDetailsProvider =
    FutureProvider<List<Map<String, dynamic>>>((ref) {
  final contenido = ref.watch(selectedContenidoProvider);
  final unidad = ref.watch(selectedUnidadProvider);
  if (contenido == null || unidad == null) return Future.value([]);
  return ref.read(curriculumRepoProvider).getContenidoDetails(contenido, unidad);
});
