import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:pdfx/pdfx.dart';

class PdfViewerScreen extends StatefulWidget {
  const PdfViewerScreen({
    super.key,
    required this.pdfUrl,
    required this.initialPage,
    required this.title,
  });

  final String pdfUrl;
  final int initialPage;
  final String title;

  @override
  State<PdfViewerScreen> createState() => _PdfViewerScreenState();
}

class _PdfViewerScreenState extends State<PdfViewerScreen> {
  PdfControllerPinch? _controller;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPdf();
  }

  Future<void> _loadPdf() async {
    try {
      final dir = await getTemporaryDirectory();
      final fileName = Uri.parse(widget.pdfUrl).pathSegments.last;
      final file = File('${dir.path}/$fileName');

      if (!file.existsSync()) {
        await Dio().download(widget.pdfUrl, file.path);
      }

      _controller = PdfControllerPinch(
        document: PdfDocument.openFile(file.path),
        initialPage: widget.initialPage,
      );
      setState(() => _loading = false);
    } catch (e) {
      setState(() {
        _loading = false;
        _error = 'No se pudo cargar el PDF: $e';
      });
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title, overflow: TextOverflow.ellipsis),
        actions: [
          if (!_loading && _error == null)
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: Center(
                child: Text(
                  'p. ${widget.initialPage}',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
            ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
              : PdfViewPinch(controller: _controller!),
    );
  }
}
