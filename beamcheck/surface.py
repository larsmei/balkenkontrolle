"""Dreiecke der Kontrollkörper, ohne SALOME.

Der Querschnitt wird als Schale extrudiert: Stirnflächen und Mantel.
Achsen sind flache Pfeile, damit sie in der schattierten SMESH-Ansicht
sichtbar bleiben. X rot, Y grün, Z blau setzt der Aufrufer über den Namen.
"""

from __future__ import annotations


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a):
    return _dot(a, a) ** 0.5


def _normalize(a):
    n = _norm(a)
    if n < 1e-15:
        return (0.0, 0.0, 0.0)
    return (a[0] / n, a[1] / n, a[2] / n)


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _place(origin, ey, ez, y, z):
    return (
        origin[0] + ey[0] * y + ez[0] * z,
        origin[1] + ey[1] * y + ez[1] * z,
        origin[2] + ey[2] * y + ez[2] * z,
    )


def _shift(point, direction, distance):
    return tuple(point[i] + direction[i] * distance for i in range(3))


def _area2(poly):
    area = 0.0
    count = len(poly)
    for index, point in enumerate(poly):
        nxt = poly[(index + 1) % count]
        area += point[0] * nxt[1] - nxt[0] * point[1]
    return area


def _ccw(poly):
    if len(poly) >= 3 and _area2(poly) < 0.0:
        return list(reversed(poly))
    return list(poly)


def _resample(poly, count):
    """Geschlossene Polylinie auf count Ecken, längentreu."""
    if count < 3 or len(poly) < 2:
        return list(poly)
    closed = list(poly) + [poly[0]]
    lengths = [0.0]
    for index in range(len(closed) - 1):
        step = (
            (closed[index + 1][0] - closed[index][0]) ** 2
            + (closed[index + 1][1] - closed[index][1]) ** 2
        ) ** 0.5
        lengths.append(lengths[-1] + step)
    total = lengths[-1]
    if total < 1e-15:
        return [poly[0]] * count
    out = []
    cursor = 1
    for index in range(count):
        target = total * index / count
        while cursor < len(lengths) - 1 and lengths[cursor] < target:
            cursor += 1
        span = lengths[cursor] - lengths[cursor - 1]
        ratio = 0.0 if span < 1e-15 else (target - lengths[cursor - 1]) / span
        a = closed[cursor - 1]
        b = closed[cursor]
        out.append((a[0] + (b[0] - a[0]) * ratio, a[1] + (b[1] - a[1]) * ratio))
    return out


def _align_start(outer, inner):
    origin = outer[0]
    best = min(
        range(len(inner)),
        key=lambda index: (inner[index][0] - origin[0]) ** 2 + (inner[index][1] - origin[1]) ** 2,
    )
    return inner[best:] + inner[:best]


def cap_triangles(outer, holes):
    """Dreiecke in der yz-Ebene. Ein Loch wird als Ring gefüllt, nicht zugeschüttet."""
    if len(outer) < 3:
        return []
    outer = _ccw(outer)
    if not holes:
        return [(outer[0], outer[index], outer[index + 1]) for index in range(1, len(outer) - 1)]
    if len(holes) != 1 or len(holes[0]) < 3:
        return []
    inner = _ccw(holes[0])
    if len(inner) != len(outer):
        inner = _resample(inner, len(outer))
    inner = _align_start(outer, inner)
    triangles = []
    count = len(outer)
    for index in range(count):
        o0 = outer[index]
        o1 = outer[(index + 1) % count]
        h0 = inner[index]
        h1 = inner[(index + 1) % count]
        triangles.append((o0, o1, h1))
        triangles.append((o0, h1, h0))
    return triangles


def extrude_shell(origin, ex, ey, ez, span, outer, holes):
    """Geschlossene Schale des extrudierten Schnitts, Liste von 3D-Dreiecken."""
    if span <= 0 or len(outer) < 3:
        return []

    def locate(point, along):
        return _shift(_place(origin, ey, ez, point[0], point[1]), ex, along)

    triangles = []
    for a, b, c in cap_triangles(outer, holes):
        triangles.append((locate(a, 0.0), locate(b, 0.0), locate(c, 0.0)))
        triangles.append((locate(a, span), locate(c, span), locate(b, span)))
    for loop in [outer] + list(holes):
        count = len(loop)
        for index in range(count):
            a = loop[index]
            b = loop[(index + 1) % count]
            a0, b0 = locate(a, 0.0), locate(b, 0.0)
            a1, b1 = locate(a, span), locate(b, span)
            triangles.append((a0, b0, b1))
            triangles.append((a0, b1, a1))
    return triangles


def axis_arrow(origin, direction, length, width, side):
    """Pfeil aus vier Dreiecken: Schaft und Spitze, doppelt gekreuzt."""
    forward = _normalize(direction)
    if forward == (0.0, 0.0, 0.0) or length <= 0:
        return []
    across = side
    if abs(_dot(_normalize(side), forward)) > 0.9:
        across = _cross(forward, (0.0, 0.0, 1.0))
        if _norm(across) < 1e-8:
            across = _cross(forward, (0.0, 1.0, 0.0))
    across = _normalize(across)
    up = _normalize(_cross(forward, across))
    arrows = []
    for lateral in (across, up):
        if lateral == (0.0, 0.0, 0.0):
            continue
        tip = _shift(origin, forward, length)
        neck = _shift(origin, forward, length * 0.72)
        tail_l = _add(origin, _scale(lateral, width * 0.22))
        tail_r = _add(origin, _scale(lateral, -width * 0.22))
        neck_l = _add(neck, _scale(lateral, width * 0.22))
        neck_r = _add(neck, _scale(lateral, -width * 0.22))
        head_l = _add(neck, _scale(lateral, width))
        head_r = _add(neck, _scale(lateral, -width))
        arrows.append((tail_l, tail_r, neck_r))
        arrows.append((tail_l, neck_r, neck_l))
        arrows.append((head_l, head_r, tip))
    return arrows
