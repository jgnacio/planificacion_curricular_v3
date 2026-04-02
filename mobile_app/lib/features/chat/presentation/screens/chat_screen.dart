import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/chat_providers.dart';
import '../../../../core/widgets/pdf_reference_badge.dart';

// [[Opción]] → single-select: tap sends immediately.
final _optionRegex = RegExp(r'\[\[(?!REF:)([^\]]+)\]\]');

// [[REF:archivo.pdf:42]] → legacy inline badge (fallback for old responses).
final _refRegex = RegExp(r'\[\[REF:([^:]+):(\d+)\]\]');

// ((Opción)) → multi-select: user picks several, then confirms.
final _multiOptionRegex = RegExp(r'\(\(([^)]+)\)\)');

List<String> _parseOptions(String text) =>
    _optionRegex.allMatches(text).map((m) => m.group(1)!).toList();

List<String> _parseMultiOptions(String text) =>
    _multiOptionRegex.allMatches(text).map((m) => m.group(1)!).toList();

class _PdfRef {
  const _PdfRef(this.pdfFuente, this.pagina, {this.label = ''});
  final String pdfFuente;
  final int pagina;
  final String label;
}

// Parses the agent response, which may be:
//   (a) JSON: {"text": "...", "refs": [{"filename": "...", "page": 23, "label": "..."}]}
//   (b) Legacy plain text with [[REF:...]] inline tokens
({String text, List<_PdfRef> refs}) _parseContent(String raw) {
  try {
    final decoded = jsonDecode(raw);
    if (decoded is Map && decoded['text'] is String) {
      final text = decoded['text'] as String;
      final refsRaw = decoded['refs'];
      final refs = <_PdfRef>[];
      if (refsRaw is List) {
        for (final r in refsRaw) {
          if (r is Map && r['filename'] is String && r['page'] is num) {
            refs.add(_PdfRef(
              r['filename'] as String,
              (r['page'] as num).toInt(),
              label: r['label'] as String? ?? '',
            ));
          }
        }
      }
      return (text: text, refs: refs);
    }
  } catch (_) {}
  // Fallback: legacy format — refs were [[REF:...]] tokens in the text
  final legacyRefs = _refRegex
      .allMatches(raw)
      .map((m) => _PdfRef(m.group(1)!, int.parse(m.group(2)!)))
      .toList();
  return (text: raw, refs: legacyRefs);
}

String _stripTokens(String text) => text
    .replaceAll(_refRegex, '')
    .replaceAll(_optionRegex, '')
    .replaceAll(_multiOptionRegex, '')
    .replaceAll(RegExp(r'BADGE_REF:.*'), '')
    .replaceAll(RegExp(r'FUENTE_PDF:.*'), '')
    .replaceAll(RegExp(r'\n{3,}'), '\n\n')
    .trim();

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();

  static const _quickPrompts = [
    ('Validar actividad', Icons.fact_check_outlined),
    ('Planificar clase', Icons.edit_note_outlined),
    ('Explorar programa', Icons.school_outlined),
  ];

  void _send(String text) {
    if (text.trim().isEmpty) return;
    _controller.clear();
    ref.read(chatProvider.notifier).sendMessage(text);
    Future.delayed(const Duration(milliseconds: 300), _scrollToBottom);
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final messages = ref.watch(chatProvider);
    final isTyping = ref.watch(chatProvider.notifier).isTyping;

    // Auto-scroll on new messages
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());

    return Scaffold(
      appBar: AppBar(
        title: const Text('Facilitador Docente EBI'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Nueva sesión',
            onPressed: () => showDialog(
              context: context,
              builder: (_) => AlertDialog(
                title: const Text('Nueva sesión'),
                content: const Text('Se reiniciará la conversación con el agente.'),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Cancelar'),
                  ),
                  FilledButton(
                    onPressed: () {
                      Navigator.pop(context);
                      // Invalidate providers to force new session
                      ref.invalidate(chatProvider);
                      ref.invalidate(sessionIdProvider);
                    },
                    child: const Text('Reiniciar'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          // Message list
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: messages.length + (isTyping ? 1 : 0),
              itemBuilder: (context, index) {
                if (isTyping && index == messages.length) {
                  return const _TypingIndicator();
                }
                return _MessageBubble(
                  message: messages[index],
                  onOptionTap: _send,
                );
              },
            ),
          ),

          // Quick prompts (only while list is short / at start)
          if (messages.length <= 1)
            _QuickPrompts(
              prompts: _quickPrompts,
              onTap: _send,
            ),

          // Input bar
          _InputBar(
            controller: _controller,
            isTyping: isTyping,
            onSend: _send,
          ),
        ],
      ),
    );
  }
}

// ──────────────────────────────────────────────
// Message Bubble
// ──────────────────────────────────────────────

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message, this.onOptionTap});

  final ChatMessage message;
  final void Function(String)? onOptionTap;

  void _copyAll(BuildContext context, String text) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Mensaje copiado'),
        duration: Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isUser = message.sender == MessageSender.user;
    final theme = Theme.of(context);

    // Parse structured JSON response (or fall back to legacy regex)
    final content = isUser
        ? (text: message.text, refs: <_PdfRef>[])
        : _parseContent(message.text);
    final bodyText = isUser ? message.text : _stripTokens(content.text);
    final options = isUser ? <String>[] : _parseOptions(content.text);
    final multiOptions = isUser ? <String>[] : _parseMultiOptions(content.text);
    final refs = content.refs;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.82,
        ),
        margin: EdgeInsets.only(
          left: isUser ? 48 : 12,
          right: isUser ? 12 : 48,
          top: 4,
          bottom: 4,
        ),
        child: Column(
          crossAxisAlignment:
              isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            // ── Bubble ────────────────────────────────────────────────
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: isUser
                    ? theme.colorScheme.primary
                    : message.isError
                        ? theme.colorScheme.errorContainer
                        : theme.colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(18),
                  topRight: const Radius.circular(18),
                  bottomLeft: Radius.circular(isUser ? 18 : 4),
                  bottomRight: Radius.circular(isUser ? 4 : 18),
                ),
              ),
              child: isUser
                  ? SelectableText(
                      bodyText,
                      style:
                          TextStyle(color: theme.colorScheme.onPrimary),
                    )
                  // SelectionArea: long-press → text handles → system copy menu
                  : SelectionArea(
                      child: MarkdownBody(
                        data: bodyText,
                        styleSheet: MarkdownStyleSheet(
                          p: TextStyle(color: theme.colorScheme.onSurface),
                          strong: TextStyle(
                            color: theme.colorScheme.onSurface,
                            fontWeight: FontWeight.bold,
                          ),
                          code: TextStyle(
                            backgroundColor: theme.colorScheme.surface,
                            fontFamily: 'monospace',
                          ),
                        ),
                      ),
                    ),
            ),

            // ── Copy-all button (all messages) ────────────────────────
            Padding(
              padding: EdgeInsets.only(
                top: 2,
                left: isUser ? 0 : 0,
              ),
              child: IconButton(
                icon: const Icon(Icons.copy, size: 15),
                tooltip: 'Copiar mensaje',
                visualDensity: VisualDensity.compact,
                style: IconButton.styleFrom(
                  padding: const EdgeInsets.all(4),
                  minimumSize: const Size(28, 28),
                  foregroundColor: theme.colorScheme.onSurfaceVariant,
                ),
                onPressed: () => _copyAll(context, bodyText),
              ),
            ),

            // ── Single-select options ──────────────────────────────────
            if (options.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Wrap(
                  spacing: 8,
                  runSpacing: 6,
                  children: options
                      .map(
                        (opt) => ActionChip(
                          label: Text(opt),
                          onPressed: () => onOptionTap?.call(opt),
                        ),
                      )
                      .toList(),
                ),
              ),

            // ── Multi-select options ───────────────────────────────────
            if (multiOptions.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: _MultiSelectOptions(
                  options: multiOptions,
                  onConfirm: onOptionTap,
                ),
              ),

            // ── PDF reference badges ───────────────────────────────────
            if (refs.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: refs
                      .map((r) => PdfReferenceBadge(
                            pdfFuente: r.pdfFuente,
                            pagina: r.pagina,
                          ))
                      .toList(),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

// ──────────────────────────────────────────────
// Multi-select options widget
// ──────────────────────────────────────────────

class _MultiSelectOptions extends StatefulWidget {
  const _MultiSelectOptions({required this.options, this.onConfirm});

  final List<String> options;
  final void Function(String)? onConfirm;

  @override
  State<_MultiSelectOptions> createState() => _MultiSelectOptionsState();
}

class _MultiSelectOptionsState extends State<_MultiSelectOptions> {
  final _selected = <String>{};

  void _toggle(String opt) {
    setState(() {
      if (_selected.contains(opt)) {
        _selected.remove(opt);
      } else {
        _selected.add(opt);
      }
    });
  }

  void _confirm() {
    if (_selected.isEmpty) return;
    // Send selected options in the order they appeared in the original list
    final ordered = widget.options.where(_selected.contains).join(', ');
    widget.onConfirm?.call(ordered);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 6,
          children: widget.options.map((opt) {
            final isSelected = _selected.contains(opt);
            return FilterChip(
              label: Text(opt),
              selected: isSelected,
              onSelected: (_) => _toggle(opt),
              checkmarkColor: theme.colorScheme.onSecondaryContainer,
            );
          }).toList(),
        ),
        if (_selected.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: FilledButton.tonal(
              onPressed: _confirm,
              child: Text('Confirmar (${_selected.length})'),
            ),
          ),
      ],
    );
  }
}

// ──────────────────────────────────────────────
// Typing Indicator
// ──────────────────────────────────────────────

class _TypingIndicator extends StatelessWidget {
  const _TypingIndicator();

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(left: 12, top: 4, bottom: 4),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(18),
            topRight: Radius.circular(18),
            bottomRight: Radius.circular(18),
            bottomLeft: Radius.circular(4),
          ),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _Dot(delay: 0),
            SizedBox(width: 4),
            _Dot(delay: 200),
            SizedBox(width: 4),
            _Dot(delay: 400),
          ],
        ),
      ),
    );
  }
}

class _Dot extends StatefulWidget {
  const _Dot({required this.delay});
  final int delay;

  @override
  State<_Dot> createState() => _DotState();
}

class _DotState extends State<_Dot> with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    )..repeat(reverse: true);
    _anim = CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut);
    Future.delayed(Duration(milliseconds: widget.delay), () {
      if (mounted) _ctrl.forward();
    });
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _anim,
      child: Container(
        width: 8,
        height: 8,
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.onSurfaceVariant,
          shape: BoxShape.circle,
        ),
      ),
    );
  }
}

// ──────────────────────────────────────────────
// Quick Prompts
// ──────────────────────────────────────────────

class _QuickPrompts extends StatelessWidget {
  const _QuickPrompts({required this.prompts, required this.onTap});

  final List<(String, IconData)> prompts;
  final ValueChanged<String> onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 4, 12, 4),
      child: Wrap(
        spacing: 8,
        runSpacing: 6,
        children: prompts
            .map((p) => ActionChip(
                  avatar: Icon(p.$2, size: 16),
                  label: Text(p.$1),
                  onPressed: () => onTap(p.$1),
                ))
            .toList(),
      ),
    );
  }
}

// ──────────────────────────────────────────────
// Input Bar
// ──────────────────────────────────────────────

class _InputBar extends StatelessWidget {
  const _InputBar({
    required this.controller,
    required this.isTyping,
    required this.onSend,
  });

  final TextEditingController controller;
  final bool isTyping;
  final ValueChanged<String> onSend;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 6, 12, 10),
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: controller,
                enabled: !isTyping,
                maxLines: null,
                textInputAction: TextInputAction.send,
                onSubmitted: onSend,
                decoration: const InputDecoration(
                  hintText: 'Escribí tu consulta...',
                  isDense: true,
                ),
              ),
            ),
            const SizedBox(width: 8),
            FilledButton(
              onPressed: isTyping ? null : () => onSend(controller.text),
              style: FilledButton.styleFrom(
                padding: const EdgeInsets.all(14),
                shape: const CircleBorder(),
              ),
              child: const Icon(Icons.send, size: 20),
            ),
          ],
        ),
      ),
    );
  }
}
