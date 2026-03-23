import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/curriculum_providers.dart';
import '../../../../core/widgets/pdf_reference_badge.dart';

class ContentDetailScreen extends ConsumerWidget {
  const ContentDetailScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final contenido = ref.watch(selectedContenidoProvider) ?? '';
    final asyncDetails = ref.watch(contenidoDetailsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Detalle del Contenido'),
      ),
      body: asyncDetails.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (details) {
          if (details.isEmpty) {
            return const Center(child: Text('Sin detalles disponibles.'));
          }
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              // Contenido header
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.menu_book, color: Color(0xFF1565C0)),
                          const SizedBox(width: 8),
                          const Text(
                            'Contenido',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: Color(0xFF1565C0),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(contenido),
                      // PDF reference badge if available
                      if (details.first['pagina'] != null) ...[
                        const SizedBox(height: 8),
                        PdfReferenceBadge(
                          pdfFuente: details.first['pdf_fuente'] as String? ?? '',
                          pagina: (details.first['pagina'] as num).toInt(),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 8),

              // Per CE detail
              ...details.map((d) => _CeCard(data: d)),
            ],
          );
        },
      ),
    );
  }
}

class _CeCard extends StatelessWidget {
  const _CeCard({required this.data});
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final criterios = List<String>.from(data['criterios'] ?? []);
    final mcns = List<String>.from(data['mcns'] ?? []);
    final ejes = List<String>.from(data['ejes'] ?? []);

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // CE header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: const Color(0xFF2E7D32),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    data['ce_id'] ?? '',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                ),
              ],
            ),
            if (data['ce_enunciado'] != null) ...[
              const SizedBox(height: 8),
              Text(
                data['ce_enunciado'] as String,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ],
            if (data['ce_desarrollo'] != null && (data['ce_desarrollo'] as String).isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                data['ce_desarrollo'] as String,
                style: const TextStyle(fontSize: 13, color: Colors.black87),
              ),
            ],

            // Criterios de logro
            if (criterios.isNotEmpty) ...[
              const SizedBox(height: 12),
              const _SectionTitle(icon: Icons.check_circle_outline, label: 'Criterios de Logro', color: Color(0xFF2E7D32)),
              ...criterios.map((c) => _BulletItem(text: c)),
            ],

            // MCN
            if (mcns.isNotEmpty) ...[
              const SizedBox(height: 12),
              const _SectionTitle(icon: Icons.star_outline, label: 'Competencias MCN', color: Color(0xFF1565C0)),
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: mcns.map((m) => Chip(label: Text(m, style: const TextStyle(fontSize: 11)))).toList(),
              ),
            ],

            // Ejes
            if (ejes.isNotEmpty) ...[
              const SizedBox(height: 12),
              const _SectionTitle(icon: Icons.account_tree_outlined, label: 'Ejes Temáticos', color: Colors.deepOrange),
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: ejes.map((e) => Chip(label: Text(e, style: const TextStyle(fontSize: 11)))).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.icon, required this.label, required this.color});
  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 6),
          Text(label, style: TextStyle(fontWeight: FontWeight.bold, color: color, fontSize: 13)),
        ],
      ),
    );
  }
}

class _BulletItem extends StatelessWidget {
  const _BulletItem({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 8, bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('• ', style: TextStyle(fontWeight: FontWeight.bold)),
          Expanded(child: Text(text, style: const TextStyle(fontSize: 13))),
        ],
      ),
    );
  }
}
