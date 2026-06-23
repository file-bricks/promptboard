import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:promptboard/l10n/app_localizations.dart';

void main() {
  runApp(const PromptBoardCompanionApp());
}

enum _PromptBoardParseException { invalidRoot, invalidItems, invalidEntry }

const String sampleLibraryJson = '''
{
  "items": [
    {
      "id": "prompt-1",
      "item_type": "PROMPT",
      "name": "Meeting-Zusammenfassung",
      "content": "Fasse das Gespräch in fünf klaren Stichpunkten zusammen und schließe mit offenen Fragen ab.",
      "category": "Alltag",
      "tags": ["meeting", "zusammenfassung"],
      "source": "Desktop-Demo",
      "created_at": "2026-05-27T08:00:00Z",
      "updated_at": "2026-05-27T08:30:00Z"
    },
    {
      "id": "skill-1",
      "item_type": "SKILL",
      "name": "Release-Checkliste",
      "content": "Prüfe Tests, Release-Notizen, Screenshots, Store-Metadaten und Signaturstatus vor dem Versand.",
      "category": "Deployment",
      "tags": ["release", "check"],
      "source": "Desktop-Demo",
      "created_at": "2026-05-27T08:10:00Z",
      "updated_at": "2026-05-27T08:40:00Z"
    },
    {
      "id": "workflow-1",
      "item_type": "WORKFLOW",
      "name": "Bugtriage Mobil",
      "content": "Erfasse Repro, vermutete Plattform, betroffene Version und den schnellsten Rückweg zum letzten stabilen Stand.",
      "category": "Support",
      "tags": ["bug", "mobil"],
      "source": "Desktop-Demo",
      "created_at": "2026-05-27T08:20:00Z",
      "updated_at": "2026-05-27T08:50:00Z"
    }
  ]
}
''';

class PromptBoardCompanionApp extends StatelessWidget {
  const PromptBoardCompanionApp({super.key});

  @override
  Widget build(BuildContext context) {
    const seed = Color(0xFF0E7C66);
    final scheme = ColorScheme.fromSeed(
      seedColor: seed,
      brightness: Brightness.light,
    );

    return MaterialApp(
      onGenerateTitle: (ctx) => AppLocalizations.of(ctx).appTitle,
      debugShowCheckedModeBanner: false,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      theme: ThemeData(
        colorScheme: scheme,
        scaffoldBackgroundColor: const Color(0xFFF4EFE6),
        useMaterial3: true,
        splashFactory: InkRipple.splashFactory,
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(18),
            borderSide: BorderSide.none,
          ),
        ),
      ),
      home: const PromptBoardCompanionPage(),
    );
  }
}

class PromptBoardCompanionPage extends StatefulWidget {
  const PromptBoardCompanionPage({super.key});

  @override
  State<PromptBoardCompanionPage> createState() =>
      _PromptBoardCompanionPageState();
}

class _PromptBoardCompanionPageState extends State<PromptBoardCompanionPage> {
  PromptBoardLibrary? _library;
  String _searchQuery = '';
  // Interner Filterkey bleibt immer 'ALLE' (Vergleich in _visibleItems).
  String _activeType = 'ALLE';
  // null = noch nicht geladen; gesetzt auf l10n-String beim Laden.
  String? _importSource;

  List<PromptBoardItem> get _visibleItems {
    final library = _library;
    if (library == null) return const [];
    return library.items.where((item) {
      final matchesType =
          _activeType == 'ALLE' || item.itemType == _activeType;
      if (!matchesType) return false;
      if (_searchQuery.trim().isEmpty) return true;
      final query = _searchQuery.trim().toLowerCase();
      return item.searchText.contains(query);
    }).toList();
  }

  Future<void> _loadFromClipboard() async {
    String text;
    try {
      final data = await Clipboard.getData('text/plain');
      if (!mounted) return;
      text = data?.text?.trim() ?? '';
    } catch (_) {
      // Clipboard-Plattformkanal kann (selten) mit PlatformException scheitern
      // -> nicht stumm verschlucken, sondern Hinweis zeigen statt Snackbar-Ausfall.
      if (!mounted) return;
      _showMessage(AppLocalizations.of(context).clipboardInvalid);
      return;
    }
    final l10n = AppLocalizations.of(context);
    if (text.isEmpty) {
      _showMessage(l10n.clipboardInvalid);
      return;
    }
    _applyLibrary(text, source: l10n.sourceClipboard);
  }

  Future<void> _openManualImport() async {
    final l10n = AppLocalizations.of(context);
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) => _ManualImportSheet(
        onApply: (text) => _applyLibrary(text, source: l10n.sourceManual),
      ),
    );
  }

  void _applyLibrary(String rawJson, {required String source}) {
    final l10n = AppLocalizations.of(context);
    try {
      final parsed = PromptBoardLibrary.fromJsonText(
        rawJson,
        unnamedEntry: l10n.unnamedEntry,
      );
      setState(() {
        _library = parsed;
        _importSource = source;
        _activeType = 'ALLE';
        _searchQuery = '';
      });
      _showMessage(l10n.itemsLoaded(parsed.items.length, source));
    } on _PromptBoardParseException catch (e) {
      _showMessage(_translateException(e, l10n));
    } on FormatException {
      _showMessage(l10n.parseErrorInvalidRoot);
    }
  }

  String _translateException(
    _PromptBoardParseException e,
    AppLocalizations l10n,
  ) =>
      switch (e) {
        _PromptBoardParseException.invalidRoot => l10n.parseErrorInvalidRoot,
        _PromptBoardParseException.invalidItems => l10n.parseErrorInvalidItems,
        _PromptBoardParseException.invalidEntry => l10n.parseErrorInvalidEntry,
      };

  void _showMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  void _openDetails(PromptBoardItem item) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (modalContext) {
        final l10n = AppLocalizations.of(modalContext);
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      Chip(label: Text(item.itemType)),
                      if (item.category.isNotEmpty)
                        Chip(label: Text(item.category)),
                      if (item.source.isNotEmpty)
                        Chip(label: Text(item.source)),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    item.name,
                    style: Theme.of(modalContext).textTheme.headlineSmall,
                  ),
                  if (item.tags.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Text(
                      l10n.tagsLabel(item.tags.join(', ')),
                      style: Theme.of(modalContext).textTheme.bodyMedium,
                    ),
                  ],
                  const SizedBox(height: 12),
                  SelectableText(
                    item.content,
                    style: Theme.of(
                      modalContext,
                    ).textTheme.bodyLarge?.copyWith(height: 1.45),
                  ),
                  const SizedBox(height: 20),
                  FilledButton.icon(
                    onPressed: () async {
                      await Clipboard.setData(
                        ClipboardData(text: item.content),
                      );
                      if (modalContext.mounted) {
                        Navigator.of(modalContext).pop();
                      }
                      _showMessage(l10n.copiedToClipboard(item.name));
                    },
                    icon: const Icon(Icons.content_copy),
                    label: Text(l10n.copyToClipboard),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final library = _library;
    final items = _visibleItems;
    final typeCounts = library?.typeCounts ?? const <String, int>{};
    final typeOptions = <String>['ALLE', ...typeCounts.keys];

    return Scaffold(
      appBar: AppBar(title: Text(l10n.appTitle)),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFFF4EFE6), Color(0xFFE7F3EE)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: Column(
              children: [
                _HeroPanel(
                  importSource: _importSource ?? l10n.notLoaded,
                  hasData: library != null,
                  onLoadDemo: () =>
                      _applyLibrary(sampleLibraryJson, source: l10n.sourceDemo),
                  onLoadClipboard: _loadFromClipboard,
                  onManualImport: _openManualImport,
                  onReset: () {
                    setState(() {
                      _library = null;
                      _searchQuery = '';
                      _activeType = 'ALLE';
                      _importSource = null;
                    });
                  },
                ),
                const SizedBox(height: 12),
                if (library == null)
                  const Expanded(child: _EmptyState())
                else
                  Expanded(
                    child: ListView(
                      children: [
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Wrap(
                            spacing: 10,
                            runSpacing: 10,
                            children: [
                              _StatCard(
                                title: l10n.statEntries,
                                value: '${library.items.length}',
                              ),
                              _StatCard(
                                title: l10n.statTypes,
                                value: '${typeCounts.length}',
                              ),
                              _StatCard(
                                title: l10n.statTagged,
                                value: '${library.taggedCount}',
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          onChanged: (value) =>
                              setState(() => _searchQuery = value),
                          decoration: InputDecoration(
                            prefixIcon: const Icon(Icons.search),
                            hintText: l10n.searchHint,
                          ),
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          height: 42,
                          child: ListView.separated(
                            scrollDirection: Axis.horizontal,
                            itemCount: typeOptions.length,
                            separatorBuilder: (_, _) =>
                                const SizedBox(width: 8),
                            itemBuilder: (context, index) {
                              final option = typeOptions[index];
                              // Nur die Anzeige lokalisieren; 'ALLE' bleibt interner Key.
                              final label =
                                  option == 'ALLE' ? l10n.typeAll : option;
                              return ChoiceChip(
                                label: Text(label),
                                selected: _activeType == option,
                                onSelected: (_) =>
                                    setState(() => _activeType = option),
                              );
                            },
                          ),
                        ),
                        const SizedBox(height: 12),
                        if (items.isEmpty)
                          const Padding(
                            padding: EdgeInsets.symmetric(vertical: 40),
                            child: _NoResultsState(),
                          )
                        else
                          ...items.map(
                            (item) => Padding(
                              padding: const EdgeInsets.only(bottom: 10),
                              child: Card(
                                color: Colors.white.withValues(alpha: 0.92),
                                elevation: 0,
                                child: ListTile(
                                  onTap: () => _openDetails(item),
                                  title: Text(item.name),
                                  subtitle: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      const SizedBox(height: 6),
                                      Wrap(
                                        spacing: 8,
                                        runSpacing: 8,
                                        children: [
                                          _InlineBadge(label: item.itemType),
                                          if (item.category.isNotEmpty)
                                            _InlineBadge(
                                              label: item.category,
                                            ),
                                        ],
                                      ),
                                      const SizedBox(height: 8),
                                      Text(
                                        item.preview,
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ],
                                  ),
                                  trailing: const Icon(Icons.chevron_right),
                                ),
                              ),
                            ),
                          ),
                        const SizedBox(height: 12),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class PromptBoardLibrary {
  PromptBoardLibrary({required this.items});

  final List<PromptBoardItem> items;

  factory PromptBoardLibrary.fromJsonText(
    String rawJson, {
    String unnamedEntry = 'UNBENANNTER EINTRAG',
  }) {
    final decoded = jsonDecode(rawJson);
    final dynamic rawItems;
    if (decoded is Map<String, dynamic>) {
      rawItems = decoded['items'];
    } else if (decoded is List<dynamic>) {
      rawItems = decoded;
    } else {
      throw _PromptBoardParseException.invalidRoot;
    }

    if (rawItems is! List<dynamic>) {
      throw _PromptBoardParseException.invalidItems;
    }

    final items = rawItems.map((entry) {
      if (entry is! Map<String, dynamic>) {
        throw _PromptBoardParseException.invalidEntry;
      }
      return PromptBoardItem.fromMap(entry, unnamedEntry: unnamedEntry);
    }).toList();

    return PromptBoardLibrary(items: items);
  }

  Map<String, int> get typeCounts {
    final counts = <String, int>{};
    for (final item in items) {
      counts.update(item.itemType, (value) => value + 1, ifAbsent: () => 1);
    }
    return counts;
  }

  int get taggedCount => items.where((item) => item.tags.isNotEmpty).length;
}

class PromptBoardItem {
  PromptBoardItem({
    required this.id,
    required this.itemType,
    required this.name,
    required this.content,
    required this.category,
    required this.tags,
    required this.source,
  });

  final String id;
  final String itemType;
  final String name;
  final String content;
  final String category;
  final List<String> tags;
  final String source;

  factory PromptBoardItem.fromMap(
    Map<String, dynamic> data, {
    String unnamedEntry = 'UNBENANNTER EINTRAG',
  }) {
    final rawTags = data['tags'];
    final tags = rawTags is List<dynamic>
        ? rawTags
              .map((tag) => tag.toString().trim())
              .where((tag) => tag.isNotEmpty)
              .toList()
        : <String>[];

    final rawName = data['name']?.toString().trim() ?? '';
    return PromptBoardItem(
      id: data['id']?.toString() ?? '',
      itemType: _normalizeType(data['item_type']?.toString()),
      name: rawName.isNotEmpty ? rawName.toUpperCase() : unnamedEntry,
      content: data['content']?.toString().trim() ?? '',
      category: data['category']?.toString().trim() ?? '',
      tags: tags,
      source: data['source']?.toString().trim() ?? '',
    );
  }

  String get searchText =>
      [name, content, category, source, tags.join(' ')].join(' ').toLowerCase();

  String get preview => content.replaceAll('\n', ' ').trim();

  static String _normalizeType(String? rawType) {
    final normalized = (rawType ?? 'PROMPT').trim().toUpperCase();
    return normalized.isEmpty ? 'PROMPT' : normalized;
  }
}

class _HeroPanel extends StatelessWidget {
  const _HeroPanel({
    required this.importSource,
    required this.hasData,
    required this.onLoadDemo,
    required this.onLoadClipboard,
    required this.onManualImport,
    required this.onReset,
  });

  final String importSource;
  final bool hasData;
  final VoidCallback onLoadDemo;
  final Future<void> Function() onLoadClipboard;
  final Future<void> Function() onManualImport;
  final VoidCallback onReset;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF14342B),
        borderRadius: BorderRadius.circular(28),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.heroTitle,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            l10n.heroDescription,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
              color: const Color(0xFFDCEBE5),
              height: 1.45,
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              FilledButton.tonal(
                onPressed: onLoadDemo,
                child: Text(l10n.loadDemo),
              ),
              FilledButton.tonalIcon(
                onPressed: onLoadClipboard,
                icon: const Icon(Icons.paste),
                label: Text(l10n.clipboardButton),
              ),
              FilledButton(
                onPressed: onManualImport,
                child: Text(l10n.enterJson),
              ),
              if (hasData)
                TextButton(
                  onPressed: onReset,
                  style: TextButton.styleFrom(foregroundColor: Colors.white),
                  child: Text(l10n.reset),
                ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            l10n.sourceLabel(importSource),
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: const Color(0xFFC5DDD5)),
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.library_books_outlined,
            size: 56,
            color: Theme.of(context).colorScheme.primary,
          ),
          const SizedBox(height: 12),
          Text(
            l10n.emptyTitle,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Text(l10n.emptyDescription, textAlign: TextAlign.center),
          ),
        ],
      ),
    );
  }
}

class _NoResultsState extends StatelessWidget {
  const _NoResultsState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        AppLocalizations.of(context).noResults,
        style: Theme.of(context).textTheme.titleMedium,
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({required this.title, required this.value});

  final String title;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 110,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.92),
        borderRadius: BorderRadius.circular(22),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 6),
          Text(
            value,
            style: Theme.of(
              context,
            ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}

class _ManualImportSheet extends StatefulWidget {
  const _ManualImportSheet({required this.onApply});

  final void Function(String text) onApply;

  @override
  State<_ManualImportSheet> createState() => _ManualImportSheetState();
}

class _ManualImportSheetState extends State<_ManualImportSheet> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: EdgeInsets.fromLTRB(
        16,
        8,
        16,
        MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.manualImportTitle,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(l10n.manualImportHint),
          const SizedBox(height: 12),
          TextField(
            controller: _controller,
            minLines: 10,
            maxLines: 16,
            decoration: const InputDecoration(
              hintText: '{ "items": [ ... ] }',
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: Text(l10n.cancel),
              ),
              const Spacer(),
              FilledButton(
                onPressed: () {
                  widget.onApply(_controller.text);
                  Navigator.of(context).pop();
                },
                child: Text(l10n.loadLibrary),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _InlineBadge extends StatelessWidget {
  const _InlineBadge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: const Color(0xFFE5F3EE),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: const Color(0xFF0E5B4A),
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
