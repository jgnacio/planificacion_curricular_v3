import 'package:flutter/material.dart';
import '../../../../core/network/api_client.dart';

class CreatePlanificacionScreen extends StatefulWidget {
  const CreatePlanificacionScreen({super.key});

  @override
  State<CreatePlanificacionScreen> createState() =>
      _CreatePlanificacionScreenState();
}

class _CreatePlanificacionScreenState extends State<CreatePlanificacionScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nombreCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  final _periodoInicioCtrl = TextEditingController();
  final _periodoFinCtrl = TextEditingController();
  String? _nivel;
  bool _saving = false;

  static const _niveles = [
    'Tramo 1 | Niveles 3, 4 y 5 años',
    'Tramo 2 | Grados 1.º y 2.º',
    'Tramo 3 | Grados 3.º y 4.º',
    'Tramo 4 | Grados 5.º y 6.º',
    'Tramo 5 | Grados 7.º y 8.º',
    'Tramo 6 | Grado 9.º',
  ];

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      await ApiClient.instance.dio.post('/planificaciones/', data: {
        'nombre': _nombreCtrl.text.trim(),
        'descripcion': _descCtrl.text.trim().isEmpty ? null : _descCtrl.text.trim(),
        'nivel': _nivel,
        'periodo_inicio': _periodoInicioCtrl.text.trim().isEmpty ? null : _periodoInicioCtrl.text.trim(),
        'periodo_fin': _periodoFinCtrl.text.trim().isEmpty ? null : _periodoFinCtrl.text.trim(),
      });
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error al guardar: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  void dispose() {
    _nombreCtrl.dispose();
    _descCtrl.dispose();
    _periodoInicioCtrl.dispose();
    _periodoFinCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Nueva Planificación')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextFormField(
              controller: _nombreCtrl,
              decoration: const InputDecoration(labelText: 'Nombre *'),
              validator: (v) => (v == null || v.trim().isEmpty) ? 'Requerido' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _descCtrl,
              decoration: const InputDecoration(labelText: 'Descripción'),
              maxLines: 3,
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              decoration: const InputDecoration(labelText: 'Nivel / Tramo'),
              value: _nivel,
              items: _niveles
                  .map((n) => DropdownMenuItem(value: n, child: Text(n, overflow: TextOverflow.ellipsis)))
                  .toList(),
              onChanged: (v) => setState(() => _nivel = v),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _periodoInicioCtrl,
                    decoration: const InputDecoration(labelText: 'Inicio (ej: Marzo 2025)'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _periodoFinCtrl,
                    decoration: const InputDecoration(labelText: 'Fin (ej: Junio 2025)'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _saving ? null : _save,
              child: _saving
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('Guardar Planificación'),
            ),
          ],
        ),
      ),
    );
  }
}
