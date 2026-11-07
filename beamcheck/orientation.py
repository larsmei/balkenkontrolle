"""Lokaler Balkenrahmen nach Code_Aster, Dokument U4.42.01.

Für ein gerades SEG2 gilt:

* lokale X-Achse: vom ersten zum zweiten Knoten
* ohne VECT_Y / VECT_Z: ANGL_VRIL, Standard 0
* Standardrahmen, Stab nicht parallel zu global Z:
  ey = normalize(ez_global × ex), ez = ex × ey
* Stab parallel zu global Z (Kreuzprodukt verschwindet):
  lokales Y liegt parallel zum globalen Y
* VECT_Y: Projektion des Vektors auf die Ebene senkrecht zu ex wird ey
* VECT_Z: dieselbe Projektion wird ez
* (ex, ey, ez) bleibt rechtshändig
* ANGL_VRIL dreht den Standardrahmen rechtshändig um ex (Grad)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_Z = (0.0, 0.0, 1.0)
_Y = (0.0, 1.0, 0.0)
# Unterhalb davon gilt der Stab als parallel zu Z (sin des Winkels).
_PARALLEL = 1e-10


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def _norm(a):
    return math.sqrt(_dot(a, a))


def _normalize(a):
    n = _norm(a)
    if n < 1e-15:
        return None
    return (a[0] / n, a[1] / n, a[2] / n)


@dataclass
class Orientation:
    """Eine ORIENTATION-Vorgabe. cara='DEFAULT' ist ANGL_VRIL = 0."""

    cara: str = "DEFAULT"
    angle: float = 0.0
    vector: tuple | None = None


def beam_axis(p1, p2):
    """Einheitsvektor und Länge. None, wenn der Stab zu kurz ist."""
    raw = _sub(p2, p1)
    length = _norm(raw)
    if length < 1e-12:
        return None, 0.0
    return _scale(raw, 1.0 / length), length


def default_axes(ex):
    """Standardrahmen (ANGL_VRIL = 0) und Hinweise."""
    warnings = []
    raw = _cross(_Z, ex)
    if _norm(raw) >= _PARALLEL:
        ey = _normalize(raw)
    else:
        warnings.append(
            "Beam is parallel to the global Z axis. "
            "Code_Aster puts local Y parallel to global Y (ANGL_VRIL = 0)."
        )
        ey = _normalize(_sub(_Y, _scale(ex, _dot(_Y, ex))))
        if ey is None:
            ey = (1.0, 0.0, 0.0)
    ez = _normalize(_cross(ex, ey))
    ey = _normalize(_cross(ez, ex))
    return ey, ez, warnings


def _rotate(ex, ey, ez, angle_deg):
    """Rechtshändige Drehung von ey/ez um ex, Winkel in Grad."""
    if abs(angle_deg) < 1e-15:
        return ey, ez
    a = math.radians(angle_deg)
    c = math.cos(a)
    s = math.sin(a)
    ey2 = _normalize(_add(_scale(ey, c), _scale(ez, s)))
    ez2 = _normalize(_add(_scale(ey, -s), _scale(ez, c)))
    return ey2, ez2


def local_frame(ex, orientation: Orientation):
    """Liefert (ey, ez, warnings) zum gegebenen ex."""
    ey, ez, warnings = default_axes(ex)
    cara = orientation.cara or "DEFAULT"

    if cara in ("DEFAULT", "ANGL_VRIL"):
        ey, ez = _rotate(ex, ey, ez, 0.0 if cara == "DEFAULT" else orientation.angle)
        return ey, ez, warnings

    if cara in ("VECT_Y", "VECT_Z", "VECT_MAIL_Y", "VECT_MAIL_Z"):
        vector = orientation.vector
        if not vector or len(vector) < 3:
            warnings.append(cara + " needs three VALE components. The default frame is kept.")
            return ey, ez, warnings
        vector = (float(vector[0]), float(vector[1]), float(vector[2]))
        tangential = _dot(vector, ex)
        projected = _sub(vector, _scale(ex, tangential))
        if _norm(projected) <= 1e-8 * max(_norm(vector), 1e-15):
            warnings.append(
                cara
                + " is parallel to the beam. Its projection onto the cross-section is zero. "
                "Code_Aster rejects that. The default frame is shown."
            )
            return ey, ez, warnings
        # VECT ersetzt den Standardrahmen, der Z-Hinweis gilt dann nicht.
        warnings = [w for w in warnings if "parallel to the global Z axis" not in w]
        if cara in ("VECT_Y", "VECT_MAIL_Y"):
            ey = _normalize(projected)
            ez = _normalize(_cross(ex, ey))
            ey = _normalize(_cross(ez, ex))
        else:
            ez = _normalize(projected)
            ey = _normalize(_cross(ez, ex))
            ez = _normalize(_cross(ex, ey))
        if cara.startswith("VECT_MAIL"):
            warnings.append(
                cara
                + ": the angle between the fibre mesh and the principal axes from MACR_CARA_POUTRE "
                "is not applied. The mesh axis of the given vector is shown."
            )
        return ey, ez, warnings

    warnings.append(
        "Orientation " + cara + " does not apply to SEG2 beams and is ignored."
    )
    return ey, ez, warnings
