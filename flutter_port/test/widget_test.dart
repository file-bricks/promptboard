import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:promptboard/main.dart';

void main() {
  testWidgets('Demo-Bibliothek lädt und Suche filtert mobil', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const PromptBoardCompanionApp());

    expect(find.text('Demo laden'), findsOneWidget);
    expect(find.text('Noch keine Bibliothek geladen'), findsOneWidget);

    await tester.tap(find.text('Demo laden'));
    await tester.pumpAndSettle();

    expect(find.text('Einträge'), findsOneWidget);
    expect(find.text('Typen'), findsOneWidget);

    final verticalScrollable = find.byWidgetPredicate(
      (widget) =>
          widget is Scrollable && widget.axisDirection == AxisDirection.down,
    );
    expect(verticalScrollable, findsOneWidget);

    await tester.enterText(
      find.byWidgetPredicate(
        (widget) =>
            widget is TextField &&
            widget.decoration?.hintText ==
                'Suche nach Name, Inhalt, Tags oder Quelle',
      ),
      'Checkliste',
    );
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.textContaining('CHECKLISTE'),
      250,
      scrollable: verticalScrollable,
    );

    expect(find.textContaining('CHECKLISTE'), findsOneWidget);
    expect(
      find.text('Keine Einträge für diesen Filter gefunden.'),
      findsNothing,
    );
  });

  testWidgets(
    'Bug-1-Regression: manueller Import öffnet, lädt und schließt ohne Fehler',
    (WidgetTester tester) async {
      await tester.pumpWidget(const PromptBoardCompanionApp());

      await tester.tap(find.text('JSON eingeben'));
      await tester.pumpAndSettle();

      expect(find.text('PromptBoard-JSON einfügen'), findsOneWidget);

      await tester.enterText(
        find.byWidgetPredicate(
          (widget) =>
              widget is TextField &&
              widget.decoration?.hintText == '{ "items": [ ... ] }',
        ),
        '{"items":[{"id":"t1","item_type":"PROMPT","name":"Test","content":"Inhalt","category":"","tags":[],"source":""}]}',
      );

      await tester.tap(find.text('Bibliothek laden'));
      await tester.pumpAndSettle();

      expect(find.text('PromptBoard-JSON einfügen'), findsNothing);
      expect(find.text('Einträge'), findsOneWidget);
    },
  );

  testWidgets(
    'Bug-2-Regression: Zwischenablage lädt PromptBoard-JSON ohne Fehler',
    (WidgetTester tester) async {
      const testJson =
          '{"items":[{"id":"c1","item_type":"PROMPT","name":"ClipTest","content":"Clip","category":"","tags":[],"source":""}]}';

      tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        SystemChannels.platform,
        (MethodCall methodCall) async {
          if (methodCall.method == 'Clipboard.getData') {
            return <String, dynamic>{'text': testJson};
          }
          return null;
        },
      );

      await tester.pumpWidget(const PromptBoardCompanionApp());
      await tester.tap(find.text('Zwischenablage'));
      await tester.pumpAndSettle();

      expect(find.text('Einträge'), findsOneWidget);
      expect(
        find.text('Keine Einträge für diesen Filter gefunden.'),
        findsNothing,
      );

      tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        SystemChannels.platform,
        null,
      );
    },
  );

  testWidgets('Detailansicht zeigt Copy-Button', (WidgetTester tester) async {
    await tester.pumpWidget(const PromptBoardCompanionApp());
    await tester.tap(find.text('Demo laden'));
    await tester.pumpAndSettle();

    final verticalScrollable = find.byWidgetPredicate(
      (widget) =>
          widget is Scrollable && widget.axisDirection == AxisDirection.down,
    );
    await tester.scrollUntilVisible(
      find.textContaining('BUGTRIAGE'),
      250,
      scrollable: verticalScrollable,
    );
    await tester.tap(find.textContaining('BUGTRIAGE'));
    await tester.pumpAndSettle();

    expect(find.text('In Zwischenablage kopieren'), findsOneWidget);
    expect(find.textContaining('Erfasse Repro'), findsWidgets);
  });
}
