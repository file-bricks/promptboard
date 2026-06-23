// Regressionstests fuer den Mobile-Bugsweep 2026-06-23 (PromptBoard/flutter_port, RE-SWEEP).
//
// Statische Quelltext-Assertions, da `flutter`/`dart` auf der Workstation nicht im
// PATH ist (kein Laufzeit-Harness). Laut /bugsweep-Skill sind statische Assertions
// in diesem Fall valide. Jeder Test ist "red on revert" gegen das PRE-Backup.
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final l10nSrc = File('lib/l10n/app_localizations.dart').readAsStringSync();
  final mainSrc = File('lib/main.dart').readAsStringSync();

  test('B1: itemsLoaded pluralisiert korrekt (1 = Singular)', () {
    expect(l10nSrc.contains("count == 1 ? 'Eintrag' : 'Einträge'"), isTrue);
    expect(l10nSrc.contains("count == 1 ? 'entry' : 'entries'"), isTrue);
  });

  test('B2: _loadFromClipboard faengt Clipboard-Fehler ab (kein stiller Ausfall)',
      () {
    final idx = mainSrc.indexOf('_loadFromClipboard');
    expect(idx, greaterThan(-1));
    final end = mainSrc.indexOf('_applyLibrary(text', idx);
    final block = mainSrc.substring(idx, end > idx ? end : idx + 600);
    expect(block.contains('try {') && block.contains('catch'), isTrue,
        reason: 'Clipboard.getData muss gegen PlatformException abgesichert sein');
  });
}
