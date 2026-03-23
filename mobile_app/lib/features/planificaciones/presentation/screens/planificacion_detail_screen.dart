import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/api_client.dart';

final _planificacionDetailProvider =
    FutureProvider.autoDispose.family<Map<String, dynamic>, int>((ref, id) async {
  final res = await ApiClient.instance.dio.get('/planificaciones/$id');
  return Map<String, dynamic>.from(res.data as Map);
});

class PlanificacionDetailScreen extends ConsumerWidget {
  const PlanificacionDetailScreen({super.key, required this.id});
  final int id;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(_planificacionDetailProvider(id));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Planificación'),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_outline),
            tooltip: 'Eliminar',
            onPressed: async.hasValue
                ? () async {
                    final ok = await showDialog<bool>(
                      context: context,
                      builder: (_) => AlertDialog(
                        title: const Text('Eliminar planificación'),
                        content: const Text('Esta acción no se puede deshacer.'),
                        actions: [
                          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancelar')),
                          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Eliminar')),
                        ],
                      ),
                    );
                    if (ok == true && context.mounted) {
                      await ApiClient.instance.dio.delete('/planificaciones/$id');
                      if (context.mounted) Navigator.of(context).pop();
                    }
                  }
                : null,
          ),
        ],
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (p) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _DetailRow(label: 'Nombre', value: p['nombre'] as String? ?? ''),
            if (p['descripcion'] != null) _DetailRow(label: 'Descripción', value: p['descripcion'] as String),
            if (p['nivel'] != null) _DetailRow(label: 'Nivel', value: p['nivel'] as String),
            if (p['periodo_inicio'] != null)
              _DetailRow(label: 'Período', value: '${p['periodo_inicio']} → ${p['periodo_fin'] ?? ''}'),
            if (p['chat_exportado'] != null) ...[
              const SizedBox(height: 16),
              const Text('Planificación generada por el agente:', style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(p['chat_exportado'] as String),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey, fontWeight: FontWeight.w600)),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(fontSize: 15)),
          const Divider(),
        ],
      ),
    );
  }
}
