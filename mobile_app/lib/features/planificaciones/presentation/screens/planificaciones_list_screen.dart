import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/api_client.dart';
import 'create_planificacion_screen.dart';
import 'planificacion_detail_screen.dart';

final planificacionesProvider =
    FutureProvider.autoDispose<List<dynamic>>((ref) async {
  final res = await ApiClient.instance.dio.get('/planificaciones/');
  return res.data as List;
});

class PlanificacionesListScreen extends ConsumerWidget {
  const PlanificacionesListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(planificacionesProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Mis Planificaciones')),
      floatingActionButton: FloatingActionButton.extended(
        icon: const Icon(Icons.add),
        label: const Text('Nueva'),
        onPressed: () async {
          await Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const CreatePlanificacionScreen()),
          );
          ref.invalidate(planificacionesProvider);
        },
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.wifi_off, size: 48, color: Colors.grey),
              const SizedBox(height: 12),
              Text('No se pudo conectar con la API.\n$e', textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton(
                onPressed: () => ref.invalidate(planificacionesProvider),
                child: const Text('Reintentar'),
              ),
            ],
          ),
        ),
        data: (items) => items.isEmpty
            ? const Center(child: Text('No hay planificaciones aún.\nCreá una nueva con el botón +.', textAlign: TextAlign.center))
            : ListView.builder(
                itemCount: items.length,
                itemBuilder: (context, i) {
                  final p = items[i] as Map<String, dynamic>;
                  return Card(
                    child: ListTile(
                      leading: const CircleAvatar(
                        backgroundColor: Color(0xFF1565C0),
                        child: Icon(Icons.description, color: Colors.white, size: 20),
                      ),
                      title: Text(p['nombre'] as String? ?? ''),
                      subtitle: Text(
                        [p['nivel'], p['periodo_inicio']]
                            .whereType<String>()
                            .join(' · '),
                      ),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () async {
                        await Navigator.of(context).push(MaterialPageRoute(
                          builder: (_) => PlanificacionDetailScreen(id: p['id'] as int),
                        ));
                        ref.invalidate(planificacionesProvider);
                      },
                    ),
                  );
                },
              ),
      ),
    );
  }
}
