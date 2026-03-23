import 'package:flutter/material.dart';
import '../../../../core/network/api_client.dart';

class CreateAlumnoScreen extends StatefulWidget {
  const CreateAlumnoScreen({super.key});

  @override
  State<CreateAlumnoScreen> createState() => _CreateAlumnoScreenState();
}

class _CreateAlumnoScreenState extends State<CreateAlumnoScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nombreCtrl = TextEditingController();
  final _nacimientoCtrl = TextEditingController();
  final _notasCtrl = TextEditingController();
  String? _nivel;
  String? _grado;
  bool _saving = false;

  static const _niveles = ['Inicial', 'Primaria', 'Secundaria'];
  static const _grados = [
    'Nivel 3 años', 'Nivel 4 años', 'Nivel 5 años',
    '1.er grado', '2.do grado', '3.er grado',
    '4.to grado', '5.to grado', '6.to grado',
  ];

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      await ApiClient.instance.dio.post('/alumnos/', data: {
        'nombre_completo': _nombreCtrl.text.trim(),
        'fecha_nacimiento': _nacimientoCtrl.text.trim().isEmpty ? null : _nacimientoCtrl.text.trim(),
        'nivel': _nivel,
        'grado': _grado,
        'notas': _notasCtrl.text.trim().isEmpty ? null : _notasCtrl.text.trim(),
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
    _nacimientoCtrl.dispose();
    _notasCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Nuevo Alumno')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextFormField(
              controller: _nombreCtrl,
              decoration: const InputDecoration(labelText: 'Nombre completo *'),
              validator: (v) => (v == null || v.trim().isEmpty) ? 'Requerido' : null,
              textCapitalization: TextCapitalization.words,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _nacimientoCtrl,
              decoration: const InputDecoration(labelText: 'Fecha de nacimiento (dd/mm/aaaa)'),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    decoration: const InputDecoration(labelText: 'Nivel'),
                    value: _nivel,
                    items: _niveles.map((n) => DropdownMenuItem(value: n, child: Text(n))).toList(),
                    onChanged: (v) => setState(() => _nivel = v),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    decoration: const InputDecoration(labelText: 'Grado'),
                    value: _grado,
                    items: _grados.map((g) => DropdownMenuItem(value: g, child: Text(g))).toList(),
                    onChanged: (v) => setState(() => _grado = v),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _notasCtrl,
              decoration: const InputDecoration(
                labelText: 'Singularidades / Notas',
                hintText: 'Estilos de aprendizaje, necesidades, fortalezas...',
              ),
              maxLines: 4,
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _saving ? null : _save,
              child: _saving
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('Guardar Alumno'),
            ),
          ],
        ),
      ),
    );
  }
}
