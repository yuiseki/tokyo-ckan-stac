"""Where a publisher's data can be, as rectangles.

The catalog does not say where any dataset is. It does say who published it,
and a ward publishes about the ward. The footprint of an Item is therefore
the administrative area of its publisher, from 国土数値情報 N03 行政区域. It
is where the data can be, not where it was measured.

One rectangle around Tokyo would run from 沖ノ鳥島 at 20N to the Okutama
hills, most of it sea. Each polygon's rectangle is taken instead, and
rectangles closer than `gap` degrees are merged, so the mainland is a few
boxes and each island group is its own.
"""

import math
from typing import Dict, List, Sequence, Tuple

Box = Tuple[float, float, float, float]


def polygon_boxes(geometry: Dict) -> List[Box]:
    polys = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    out = []
    for poly in polys:
        xs = [p[0] for p in poly[0]]
        ys = [p[1] for p in poly[0]]
        out.append((min(xs), min(ys), max(xs), max(ys)))
    return out


def _near(a: Box, b: Box, gap: float) -> bool:
    return not (a[2] + gap < b[0] or b[2] + gap < a[0] or a[3] + gap < b[1] or b[3] + gap < a[1])


def merge_boxes(boxes: Sequence[Box], gap: float) -> List[Box]:
    """Merge until no two boxes are within `gap` of each other."""
    out = list(boxes)
    changed = True
    while changed:
        changed = False
        merged: List[Box] = []
        for b in out:
            for i, m in enumerate(merged):
                if _near(m, b, gap):
                    merged[i] = (min(m[0], b[0]), min(m[1], b[1]), max(m[2], b[2]), max(m[3], b[3]))
                    changed = True
                    break
            else:
                merged.append(b)
        out = merged
    return out


def rounded_outward(b: Box, places: int = 4) -> Box:
    """Round so the box still contains what it was computed from."""
    f = 10 ** places
    return (math.floor(b[0] * f) / f, math.floor(b[1] * f) / f,
            math.ceil(b[2] * f) / f, math.ceil(b[3] * f) / f)


def geometry_of(boxes: Sequence[Box]) -> Dict:
    return {
        "type": "MultiPolygon",
        "coordinates": [
            [[[w, s], [e, s], [e, n], [w, n], [w, s]]] for w, s, e, n in boxes
        ],
    }


def outer_bbox(boxes: Sequence[Box]) -> List[float]:
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]
