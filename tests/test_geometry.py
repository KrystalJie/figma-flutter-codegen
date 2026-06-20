from agent import geometry


def _box(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def test_collect_target_rects_normalizes_to_root_origin():
    figma = {
        "id": "0:1",
        "name": "Screen",
        "absoluteBoundingBox": _box(100, 200, 375, 800),
        "children": [
            {"id": "1:1", "name": "Header", "absoluteBoundingBox": _box(110, 210, 355, 44)},
            {
                "id": "1:2",
                "name": "Body",
                "absoluteBoundingBox": _box(100, 300, 375, 500),
                "children": [
                    {"id": "2:1", "name": "Text", "absoluteBoundingBox": _box(120, 320, 200, 20)},
                ],
            },
        ],
    }
    rects = geometry.collect_target_rects(figma)
    assert rects["0:1"] == (0.0, 0.0, 375.0, 800.0)
    assert rects["1:1"] == (10.0, 10.0, 355.0, 44.0)
    assert rects["2:1"] == (20.0, 120.0, 200.0, 20.0)


def test_collect_target_rects_skips_nodes_without_box():
    figma = {
        "id": "0:1",
        "absoluteBoundingBox": _box(0, 0, 10, 10),
        "children": [{"id": "1:1"}, {"name": "no id", "absoluteBoundingBox": _box(1, 1, 2, 2)}],
    }
    rects = geometry.collect_target_rects(figma)
    assert set(rects) == {"0:1"}


def test_collect_names():
    figma = {
        "id": "0:1",
        "name": "Screen",
        "children": [{"id": "1:1", "name": "Header"}],
    }
    assert geometry.collect_names(figma) == {"0:1": "Screen", "1:1": "Header"}


def test_diff_rects_flags_only_over_tolerance():
    target = {"a": (0, 0, 100, 50), "b": (0, 60, 100, 50)}
    actual = {"a": (0.5, 0, 100, 50), "b": (0, 60, 100, 70)}  # a within tol, b height off
    report = geometry.diff_rects(target, actual, tolerance=1.0)
    assert report.matched == 2
    assert len(report.deviations) == 1
    dev = report.deviations[0]
    assert dev.id == "b"
    assert dev.kinds == ("h",)
    assert dev.dh == 20


def test_diff_rects_ranks_worst_first_and_reports_kinds():
    target = {"a": (0, 0, 100, 50), "b": (0, 0, 100, 50)}
    actual = {"a": (5, 0, 100, 50), "b": (0, 0, 130, 90)}  # a: x+5; b: w+30,h+40
    report = geometry.diff_rects(target, actual, tolerance=1.0)
    assert [d.id for d in report.deviations] == ["b", "a"]
    assert report.deviations[0].kinds == ("w", "h")
    assert report.max_offset == 40
    assert report.mean_offset == (5 + 40) / 2


def test_diff_rects_ignores_unmatched_ids():
    target = {"a": (0, 0, 10, 10), "only_target": (0, 0, 5, 5)}
    actual = {"a": (0, 0, 10, 10), "only_actual": (0, 0, 5, 5)}
    report = geometry.diff_rects(target, actual)
    assert report.matched == 1
    assert report.target_total == 2
    assert report.actual_total == 2
    assert report.deviations == ()


def test_report_to_dict_is_json_friendly():
    target = {"a": (0, 0, 100, 50)}
    actual = {"a": (0, 0, 100, 70)}
    d = geometry.diff_rects(target, actual, names={"a": "Box"}).to_dict()
    assert d["matched"] == 1
    assert d["deviation_count"] == 1
    assert d["deviations"][0]["name"] == "Box"
    assert d["deviations"][0]["target"] == [0.0, 0.0, 100.0, 50.0]


def test_load_rects_coerces_lists():
    out = geometry.load_rects({"a": [1, 2, 3, 4], "bad": [1, 2]})
    assert out == {"a": (1.0, 2.0, 3.0, 4.0)}
