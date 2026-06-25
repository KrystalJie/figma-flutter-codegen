// Smoke test: every generated screen must actually build and lay out without
// throwing (a RenderFlex overflow or null-deref surfaces as a test exception).
// This is the runtime counterpart to `flutter analyze` — analyze proves the
// generated Dart is valid; this proves it renders.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle, FontLoader;
import 'package:flutter_test/flutter_test.dart';

import 'package:flutter_app/main.dart';

void main() {
  // Load the design font so text metrics match production. Without it,
  // flutter_test substitutes a placeholder font whose taller line box can
  // trip spurious overflows that never occur on a real device.
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    await (FontLoader('Inter')..addFont(rootBundle.load('fonts/Inter.ttf')))
        .load();
  });

  /// Give each screen its mobile-portrait canvas so fixed-size frames don't
  /// overflow a smaller default test viewport. Resets after the test.
  Future<void> useMobileCanvas(WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(400, 940));
    addTearDown(() => tester.binding.setSurfaceSize(null));
  }

  testWidgets('gallery renders every demo entry', (tester) async {
    await useMobileCanvas(tester);
    await tester.pumpWidget(const MyApp());

    expect(find.text('Figma2Flutter Demos'), findsOneWidget);
    expect(find.byType(ListTile), findsNWidgets(demos.length));
    expect(tester.takeException(), isNull);
  });

  for (final demo in demos) {
    testWidgets('renders without error: ${demo.title}', (tester) async {
      await useMobileCanvas(tester);
      await tester.pumpWidget(
        MaterialApp(home: Builder(builder: demo.builder)),
      );
      await tester.pump();

      // The only tolerated exception is the network-image 400 that
      // flutter_test forces for `Image.network` (no real device hits this);
      // a layout overflow or any other error must fail the smoke test.
      final exception = tester.takeException();
      final tolerated =
          exception == null ||
          exception.runtimeType.toString() == 'NetworkImageLoadException';
      expect(tolerated, isTrue, reason: '${demo.title} threw: $exception');
    });
  }
}
