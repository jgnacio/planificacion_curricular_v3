import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/api_client.dart';
import 'create_alumno_screen.dart';

final alumnosProvider = FutureProvider.autoDispose<List<dynamic>>((ref) async {
  final res = await ApiClient.instance.dio.get('/alumnos/');
  return res.data as List;
});

class AlumnosListScreen extends ConsumerWidget {
  const AlumnosListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(alumnosProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Mis Alumnos')),
      floatingActionButton: FloatingActionButton.extended(
        icon: const Icon(Icons.person_add),
        label: const Text('Agregar'),
        onPressed: () async {
          await Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const CreateAlumnoScreen()),
          );
          ref.invalidate(alumnosProvider);
        },
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (items) => items.isEmpty
            ? const Center(
                child: Text(
                  'No hay alumnos registrados.\nAgregá uno con el botón +.',
                  textAlign: TextAlign.center,
                ),
              )
            : ListView.builder(
                itemCount: items.length,
                itemBuilder: (context, i) {
                  final a = items[i] as Map<String, dynamic>;
                  final nombre = a['nombre_completo'] as String? ?? '';
                  return Card(
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: const Color(0xFF2E7D32),
                        child: Text(
                          nombre.isNotEmpty ? nombre[0].toUpperCase() : '?',
                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                        ),
                      ),
                      title: Text(nombre),
                      subtitle: Text(
                        [a['nivel'], a['grado']]
                            .whereType<String>()
                            .join(' · '),
                      ),
                    ),
                  );
                },
              ),
      ),
    );
  }
}
