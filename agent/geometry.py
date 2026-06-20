from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# A rect is (x, y, width, height) in logical pixels, with x/y measured from the
# root frame's top-left so the Figma target and the Flutter render share an
# origin and can be compared directly.
Rect = tuple[float, float, float, float]


def collect_target_rects(figma_json: dict) -> dict[str, Rect]:
    """Walk a raw Figma node tree, returning {node id -> rect}.

    Each rect comes straight from the node's `absoluteBoundingBox`, normalized
    to the root node's top-left so it matches the Flutter render's coordinate
    space. Nodes without a bounding box or id are skipped. First occurrence of
    an id wins, keeping the mapping deterministic.
    """
    root_box = figma_json.get("absoluteBoundingBox") or {}
    ox = float(root_box.get("x", 0.0))
    oy = float(root_box.get("y", 0.0))
    out: dict[str, Rect] = {}
    _walk(figma_json, ox, oy, out)
    return out


def collect_names(figma_json: dict) -> dict[str, str]:
    """Return {node id -> name} for nicer deviation reporting."""
    out: dict[str, str] = {}
    _walk_names(figma_json, out)
    return out


def _walk(node: dict, ox: float, oy: float, out: dict[str, Rect]) -> None:
    box = node.get("absoluteBoundingBox")
    nid = node.get("id")
    if box and nid and "x" in box and "y" in box:
        out.setdefault(
            nid,
            (
                float(box["x"]) - ox,
                float(box["y"]) - oy,
                float(box.get("width", 0.0)),
                float(box.get("height", 0.0)),
            ),
        )
    for child in node.get("children") or []:
        _walk(child, ox, oy, out)


def _walk_names(node: dict, out: dict[str, str]) -> None:
    nid = node.get("id")
    name = node.get("name")
    if nid and name:
        out.setdefault(nid, name)
    for child in node.get("children") or []:
        _walk_names(child, out)


@dataclass(frozen=True)
class Deviation:
    """One node whose rendered rect differs from its Figma target beyond tol.

    `kinds` lists which of x/y/w/h exceeded the tolerance; the signed deltas
    (actual - target) give magnitude and direction; `max_abs` is the largest
    absolute delta and is used to rank deviations.
    """

    id: str
    name: str | None
    kinds: tuple[str, ...]
    target: Rect
    actual: Rect
    dx: float
    dy: float
    dw: float
    dh: float
    max_abs: float

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "kinds": list(self.kinds),
            "target": list(self.target),
            "actual": list(self.actual),
            "dx": round(self.dx, 2),
            "dy": round(self.dy, 2),
            "dw": round(self.dw, 2),
            "dh": round(self.dh, 2),
            "max_abs": round(self.max_abs, 2),
        }


@dataclass(frozen=True)
class GeometryReport:
    """Result of diffing Figma target rects against rendered rects.

    Only nodes present in both sets are compared (`matched`). `deviations`
    holds those past the tolerance, ranked worst-first; `max_offset`/
    `mean_offset` summarize the largest per-node delta across all matches.
    """

    tolerance: float
    matched: int
    target_total: int
    actual_total: int
    deviations: tuple[Deviation, ...]
    max_offset: float
    mean_offset: float

    def to_dict(self) -> dict:
        return {
            "tolerance": self.tolerance,
            "matched": self.matched,
            "target_total": self.target_total,
            "actual_total": self.actual_total,
            "max_offset": round(self.max_offset, 2),
            "mean_offset": round(self.mean_offset, 2),
            "deviation_count": len(self.deviations),
            "deviations": [d.to_dict() for d in self.deviations],
        }


_AXES = ("x", "y", "w", "h")


def diff_rects(
    target: dict[str, Rect],
    actual: dict[str, Rect],
    tolerance: float = 1.0,
    names: dict[str, str] | None = None,
) -> GeometryReport:
    """Compare rendered rects against Figma targets node-by-node.

    For each shared id the signed deltas (actual - target) are computed; a node
    is a deviation when any of x/y/w/h exceeds `tolerance` logical pixels.
    """
    names = names or {}
    deviations: list[Deviation] = []
    offsets: list[float] = []
    for nid in target:
        if nid not in actual:
            continue
        tx, ty, tw, th = target[nid]
        ax, ay, aw, ah = actual[nid]
        deltas = (ax - tx, ay - ty, aw - tw, ah - th)
        max_abs = max(abs(d) for d in deltas)
        offsets.append(max_abs)
        if max_abs > tolerance:
            kinds = tuple(
                ax_name for ax_name, d in zip(_AXES, deltas) if abs(d) > tolerance
            )
            deviations.append(
                Deviation(
                    id=nid,
                    name=names.get(nid),
                    kinds=kinds,
                    target=target[nid],
                    actual=actual[nid],
                    dx=deltas[0],
                    dy=deltas[1],
                    dw=deltas[2],
                    dh=deltas[3],
                    max_abs=max_abs,
                )
            )
    deviations.sort(key=lambda d: d.max_abs, reverse=True)
    return GeometryReport(
        tolerance=tolerance,
        matched=len(offsets),
        target_total=len(target),
        actual_total=len(actual),
        deviations=tuple(deviations),
        max_offset=max(offsets, default=0.0),
        mean_offset=(sum(offsets) / len(offsets)) if offsets else 0.0,
    )


def load_rects(data: dict[str, Any]) -> dict[str, Rect]:
    """Coerce a JSON {id -> [x, y, w, h]} dump into {id -> Rect}."""
    out: dict[str, Rect] = {}
    for nid, vals in data.items():
        if isinstance(vals, (list, tuple)) and len(vals) == 4:
            out[nid] = (float(vals[0]), float(vals[1]), float(vals[2]), float(vals[3]))
    return out
