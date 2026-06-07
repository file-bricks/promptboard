import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

class AppLocalizations {
  AppLocalizations(this.locale);

  final Locale locale;

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates = [
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ];

  static const List<Locale> supportedLocales = [
    Locale('de'),
    Locale('en'),
  ];

  static AppLocalizations of(BuildContext context) =>
      Localizations.of<AppLocalizations>(context, AppLocalizations)!;

  bool get _isEn => locale.languageCode == 'en';

  // ── App ─────────────────────────────────────────────────────────────
  String get appTitle => 'PromptBoard Companion';

  // ── Source labels ────────────────────────────────────────────────────
  String get notLoaded => _isEn ? 'Not loaded' : 'Noch nicht geladen';
  String get sourceClipboard => _isEn ? 'Clipboard' : 'Zwischenablage';
  String get sourceManual => _isEn ? 'Manual entry' : 'Manuelle Eingabe';
  String get sourceDemo => 'Demo';

  // ── Messages ─────────────────────────────────────────────────────────
  String get clipboardInvalid => _isEn
      ? 'Clipboard does not contain valid PromptBoard JSON.'
      : 'Die Zwischenablage enthält kein lesbares PromptBoard-JSON.';

  String itemsLoaded(int count, String source) => _isEn
      ? '$count entries from $source loaded.'
      : '$count Einträge aus $source geladen.';

  String tagsLabel(String tags) => 'Tags: $tags';

  String copiedToClipboard(String name) => _isEn
      ? '$name was copied to clipboard.'
      : '$name wurde in die Zwischenablage kopiert.';

  String get copyToClipboard =>
      _isEn ? 'Copy to clipboard' : 'In Zwischenablage kopieren';

  // ── Stat cards ───────────────────────────────────────────────────────
  String get statEntries => _isEn ? 'Entries' : 'Einträge';
  String get statTypes => _isEn ? 'Types' : 'Typen';
  String get statTagged => _isEn ? 'Tagged' : 'Mit Tags';

  // ── Search ───────────────────────────────────────────────────────────
  String get searchHint => _isEn
      ? 'Search by name, content, tags or source'
      : 'Suche nach Name, Inhalt, Tags oder Quelle';

  // ── Type filter ──────────────────────────────────────────────────────
  // 'ALLE' bleibt interner Filterkey; nur die Anzeige wird lokalisiert.
  String get typeAll => _isEn ? 'ALL' : 'ALLE';

  // ── Hero panel ───────────────────────────────────────────────────────
  String get heroTitle => _isEn
      ? 'Android/iOS Companion for PromptBoard'
      : 'Android/iOS-Companion für PromptBoard';

  String get heroDescription => _isEn
      ? 'Loads Desktop `library.json` read-only via Demo, Clipboard or manual JSON entry — no cloud required.'
      : 'Lädt Desktop-`library.json` read-only per Demo, Zwischenablage oder manueller JSON-Eingabe und bleibt damit ohne Cloud nutzbar.';

  // ── Buttons ──────────────────────────────────────────────────────────
  String get loadDemo => _isEn ? 'Load demo' : 'Demo laden';
  String get clipboardButton => _isEn ? 'Clipboard' : 'Zwischenablage';
  String get enterJson => _isEn ? 'Enter JSON' : 'JSON eingeben';
  String get reset => _isEn ? 'Reset' : 'Zurücksetzen';
  String sourceLabel(String src) => _isEn ? 'Source: $src' : 'Quelle: $src';

  // ── Empty states ─────────────────────────────────────────────────────
  String get emptyTitle =>
      _isEn ? 'No library loaded' : 'Noch keine Bibliothek geladen';

  String get emptyDescription => _isEn
      ? 'For the first mobile smoke test, the Desktop file `library.json` is enough. '
        'The companion shows types, search and detail view intentionally read-only.'
      : 'Für den ersten Mobile-Smoke reicht die Desktop-Datei `library.json`. '
        'Der Companion zeigt Typen, Suche und Detailansicht bewusst read-only.';

  String get noResults => _isEn
      ? 'No entries found for this filter.'
      : 'Keine Einträge für diesen Filter gefunden.';

  // ── Manual import sheet ──────────────────────────────────────────────
  String get manualImportTitle =>
      _isEn ? 'Paste PromptBoard JSON' : 'PromptBoard-JSON einfügen';

  String get manualImportHint => _isEn
      ? 'Expects the Desktop file `library.json` with an `items` array.'
      : 'Erwartet wird die Desktop-Datei `library.json` mit einem `items`-Array.';

  String get cancel => _isEn ? 'Cancel' : 'Abbrechen';
  String get loadLibrary => _isEn ? 'Load library' : 'Bibliothek laden';

  // ── Model fallbacks ──────────────────────────────────────────────────
  // Großschreibung laut CLAUDE.md Hard Rule.
  String get unnamedEntry => _isEn ? 'UNNAMED ENTRY' : 'UNBENANNTER EINTRAG';

  // ── Parse errors ─────────────────────────────────────────────────────
  String get parseErrorInvalidRoot => _isEn
      ? 'Invalid JSON: root must be object or list.'
      : 'Ungültiges JSON: Wurzel muss Objekt oder Liste sein.';

  String get parseErrorInvalidItems => _isEn
      ? 'Invalid PromptBoard format: `items` must be a list.'
      : 'Ungültiges PromptBoard-Format: `items` muss eine Liste sein.';

  String get parseErrorInvalidEntry => _isEn
      ? 'Invalid PromptBoard format: entry is not an object.'
      : 'Ungültiges PromptBoard-Format: Eintrag ist kein Objekt.';
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  bool isSupported(Locale locale) =>
      ['de', 'en'].contains(locale.languageCode);

  @override
  Future<AppLocalizations> load(Locale locale) =>
      SynchronousFuture(AppLocalizations(locale));

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}
