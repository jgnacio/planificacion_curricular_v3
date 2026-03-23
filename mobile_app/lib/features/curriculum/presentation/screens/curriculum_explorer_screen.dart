import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/curriculum_providers.dart';
import 'content_detail_screen.dart';

class CurriculumExplorerScreen extends ConsumerWidget {
  const CurriculumExplorerScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Explorador Curricular')),
      body: const SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _CicloSelector(),
            SizedBox(height: 12),
            _EspacioSelector(),
            SizedBox(height: 12),
            _UnidadSelector(),
            SizedBox(height: 12),
            _GradoSelector(),
            SizedBox(height: 12),
            _ContenidoSelector(),
          ],
        ),
      ),
    );
  }
}

// ──────────────────────────────────────────────
// Reusable async dropdown
// ──────────────────────────────────────────────

class _AsyncDropdown extends ConsumerWidget {
  const _AsyncDropdown({
    required this.label,
    required this.provider,
    required this.valueProvider,
    required this.onChanged,
    this.enabled = true,
  });

  final String label;
  final FutureProvider<List<String>> provider;
  final StateProvider<String?> valueProvider;
  final void Function(String?) onChanged;
  final bool enabled;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncItems = ref.watch(provider);
    final selected = ref.watch(valueProvider);

    return asyncItems.when(
      loading: () => DropdownButtonFormField<String>(
        decoration: InputDecoration(labelText: label),
        items: const [],
        onChanged: null,
        hint: const Row(
          children: [
            SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            SizedBox(width: 8),
            Text('Cargando...'),
          ],
        ),
      ),
      error: (e, _) => Text('Error: $e'),
      data: (items) => DropdownButtonFormField<String>(
        decoration: InputDecoration(labelText: label),
        value: items.contains(selected) ? selected : null,
        items: items
            .map((i) => DropdownMenuItem(value: i, child: Text(i, overflow: TextOverflow.ellipsis)))
            .toList(),
        onChanged: enabled ? onChanged : null,
        hint: Text('Seleccioná $label'),
      ),
    );
  }
}

// ──────────────────────────────────────────────
// Selectors
// ──────────────────────────────────────────────

class _CicloSelector extends ConsumerWidget {
  const _CicloSelector();
  @override
  Widget build(BuildContext context, WidgetRef ref) => _AsyncDropdown(
        label: 'Ciclo',
        provider: ciclosProvider,
        valueProvider: selectedCicloProvider,
        onChanged: (v) {
          ref.read(selectedCicloProvider.notifier).state = v;
          ref.read(selectedEspacioProvider.notifier).state = null;
          ref.read(selectedUnidadProvider.notifier).state = null;
          ref.read(selectedGradoProvider.notifier).state = null;
          ref.read(selectedContenidoProvider.notifier).state = null;
        },
      );
}

class _EspacioSelector extends ConsumerWidget {
  const _EspacioSelector();
  @override
  Widget build(BuildContext context, WidgetRef ref) => _AsyncDropdown(
        label: 'Espacio Curricular',
        provider: espaciosProvider,
        valueProvider: selectedEspacioProvider,
        enabled: ref.watch(selectedCicloProvider) != null,
        onChanged: (v) {
          ref.read(selectedEspacioProvider.notifier).state = v;
          ref.read(selectedUnidadProvider.notifier).state = null;
          ref.read(selectedContenidoProvider.notifier).state = null;
        },
      );
}

class _UnidadSelector extends ConsumerWidget {
  const _UnidadSelector();
  @override
  Widget build(BuildContext context, WidgetRef ref) => _AsyncDropdown(
        label: 'Unidad Curricular',
        provider: unidadesProvider,
        valueProvider: selectedUnidadProvider,
        enabled: ref.watch(selectedEspacioProvider) != null,
        onChanged: (v) {
          ref.read(selectedUnidadProvider.notifier).state = v;
          ref.read(selectedContenidoProvider.notifier).state = null;
        },
      );
}

class _GradoSelector extends ConsumerWidget {
  const _GradoSelector();
  @override
  Widget build(BuildContext context, WidgetRef ref) => _AsyncDropdown(
        label: 'Grado / Tramo (opcional)',
        provider: gradosProvider,
        valueProvider: selectedGradoProvider,
        enabled: ref.watch(selectedCicloProvider) != null,
        onChanged: (v) {
          ref.read(selectedGradoProvider.notifier).state = v;
          ref.read(selectedContenidoProvider.notifier).state = null;
        },
      );
}

class _ContenidoSelector extends ConsumerWidget {
  const _ContenidoSelector();
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncItems = ref.watch(contenidosProvider);
    final selected = ref.watch(selectedContenidoProvider);
    final enabled = ref.watch(selectedUnidadProvider) != null;

    return Column(
      children: [
        asyncItems.when(
          loading: () => DropdownButtonFormField<String>(
            decoration: const InputDecoration(labelText: 'Contenido'),
            items: const [],
            onChanged: null,
            hint: const Text('Cargando...'),
          ),
          error: (e, _) => Text('Error: $e'),
          data: (items) => DropdownButtonFormField<String>(
            decoration: const InputDecoration(labelText: 'Contenido'),
            value: items.contains(selected) ? selected : null,
            items: items
                .map((i) => DropdownMenuItem(
                      value: i,
                      child: Text(i, overflow: TextOverflow.ellipsis),
                    ))
                .toList(),
            onChanged: enabled
                ? (v) => ref.read(selectedContenidoProvider.notifier).state = v
                : null,
            hint: const Text('Seleccioná un contenido'),
          ),
        ),
        if (selected != null) ...[
          const SizedBox(height: 16),
          FilledButton.icon(
            icon: const Icon(Icons.open_in_new),
            label: const Text('Ver detalle del contenido'),
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const ContentDetailScreen()),
            ),
          ),
        ],
      ],
    );
  }
}
