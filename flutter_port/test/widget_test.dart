import 'package:flutter/material.dart';
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
