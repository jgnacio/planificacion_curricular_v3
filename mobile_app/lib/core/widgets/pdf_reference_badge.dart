import 'package:flutter/material.dart';
import '../../features/curriculum/presentation/screens/pdf_viewer_screen.dart';
import '../config/app_config.dart';

class PdfReferenceBadge extends StatelessWidget {
  const PdfReferenceBadge({
    super.key,
    required this.pdfFuente,
    required this.pagina,
  });

  final String pdfFuente;
  final int pagina;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => PdfViewerScreen(
          pdfUrl: '${AppConfig.apiBaseUrl}/pdfs/${Uri.encodeComponent(pdfFuente)}',
          initialPage: pagina,
          title: pdfFuente,
        ),
      )),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: const Color(0xFF1565C0).withAlpha(20),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: const Color(0xFF1565C0).withAlpha(80)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.picture_as_pdf, size: 12, color: Color(0xFF1565C0)),
            const SizedBox(width: 4),
            Text(
              'p. $pagina',
              style: const TextStyle(
                fontSize: 11,
                color: Color(0xFF1565C0),
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
