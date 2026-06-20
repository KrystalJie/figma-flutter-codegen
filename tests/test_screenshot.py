from __future__ import annotations

from agent import screenshot


def test_build_golden_test_embeds_class_size_and_paths() -> None:
    src = screenshot.build_golden_test("ProfilePosts", 375, 812)
    assert "import 'package:flutter_app/generated_screen.dart';" in src
    assert "const Size(375, 812)" in src
    assert "home: ProfilePosts()" in src
    assert "find.byType(ProfilePosts)" in src
    assert "matchesGoldenFile('visual_golden/actual.png')" in src
    # Network images can't load under flutter_test; capture must not fail.
    assert "while (tester.takeException() != null)" in src


def test_build_golden_test_respects_custom_screen_file() -> None:
    src = screenshot.build_golden_test("Home", 320, 640, screen_file="screen.dart")
    assert "import 'package:flutter_app/screen.dart';" in src
    assert "const Size(320, 640)" in src

def test_build_rect_dump_test_embeds_class_size_and_output() -> None:
    src = screenshot.build_rect_dump_test("ProfilePosts", 375, 812)
    assert "import 'package:flutter_app/generated_screen.dart';" in src
    assert "const Size(375, 812)" in src
    assert "home: ProfilePosts()" in src
    assert "find.byType(KeyedSubtree)" in src
    assert "putIfAbsent" in src  # first occurrence wins for deduped components
    assert "test/visual_rects/rects.json" in src
    # Network images can't load under flutter_test; capture must not fail.
    assert "while (tester.takeException() != null)" in src


def test_build_rect_dump_test_respects_custom_screen_file() -> None:
    src = screenshot.build_rect_dump_test("Home", 320, 640, screen_file="screen_keyed.dart")
    assert "import 'package:flutter_app/screen_keyed.dart';" in src
