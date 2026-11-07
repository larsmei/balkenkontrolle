"""Querschnittskonturen in der lokalen yz-Ebene.

Der Ursprung ist der Schwerpunkt. Lokales Y nach rechts, lokales Z nach oben,
wenn man so auf den Schnitt sieht, dass lokales X auf einen zukommt.

RECTANGLE: HY in Y, HZ in Z. EPY ist die Wanddicke in Y (linke und rechte Wand),
EPZ die Wanddicke in Z (oben und unten). Fehlt die Dicke, ist der Schnitt voll.

CERCLE: R Außenradius. EP < R ist ein Rohr, EP fehlend oder EP = R ein Vollkreis.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Profile:
    kind: str
    outer: list
    holes: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    area: float | None = None
    iy: float | None = None
    iz: float | None = None
    label: str = ""


def _rect(width, height, clockwise=False):
    y = width * 0.5
    z = height * 0.5
    pts = [(-y, -z), (y, -z), (y, z), (-y, z)]
    if clockwise:
        pts.reverse()
    return pts


def _ring(radius, count, clockwise=False):
    pts = []
    for i in range(count):
        ang = 2.0 * math.pi * i / count
        if clockwise:
            ang = -ang
        pts.append((radius * math.cos(ang), radius * math.sin(ang)))
    return pts


def rectangle_profile(hy, hz, epy=None, epz=None):
    warnings = []
    hy = float(hy)
    hz = float(hz)
    if hy <= 0 or hz <= 0:
        warnings.append("HY and HZ must be positive.")
        return Profile("RECTANGLE", [], warnings=warnings, label="Invalid rectangle")
    holes = []
    area = hy * hz
    iy = hy * hz**3 / 12.0
    iz = hz * hy**3 / 12.0
    hollow = epy is not None or epz is not None
    if hollow:
        epy_v = 0.0 if epy is None else float(epy)
        epz_v = 0.0 if epz is None else float(epz)
        if epy_v < 0 or epz_v < 0:
            warnings.append("Wall thicknesses must not be negative.")
        inner_y = hy - 2.0 * epy_v
        inner_z = hz - 2.0 * epz_v
        if inner_y <= 1e-9 or inner_z <= 1e-9:
            warnings.append(
                "The wall thickness fills the rectangle. The solid section is shown."
            )
        else:
            holes.append(_rect(inner_y, inner_z, clockwise=True))
            area = hy * hz - inner_y * inner_z
            iy = (hy * hz**3 - inner_y * inner_z**3) / 12.0
            iz = (hz * hy**3 - inner_z * inner_y**3) / 12.0
    label = "Rectangle HY={:.4g} HZ={:.4g}".format(hy, hz)
    if hollow and holes:
        label += " hollow"
    return Profile(
        "RECTANGLE",
        _rect(hy, hz),
        holes,
        warnings,
        area,
        iy,
        iz,
        label,
    )


def circle_profile(radius, ep=None, count=48):
    warnings = []
    radius = float(radius)
    if radius <= 0:
        warnings.append("R must be positive.")
        return Profile("CERCLE", [], warnings=warnings, label="Invalid circle")
    holes = []
    area = math.pi * radius**2
    inertia = math.pi * radius**4 / 4.0
    label = "Circle R={:.4g}".format(radius)
    if ep is not None:
        ep_v = float(ep)
        if ep_v < 0:
            warnings.append("EP must not be negative.")
        elif ep_v > radius + 1e-9:
            warnings.append("EP > R. The solid circle is shown.")
        elif ep_v < radius - 1e-12:
            ri = radius - ep_v
            holes.append(_ring(ri, count, clockwise=True))
            area = math.pi * (radius**2 - ri**2)
            inertia = math.pi * (radius**4 - ri**4) / 4.0
            label = "Tube R={:.4g} EP={:.4g}".format(radius, ep_v)
    return Profile("CERCLE", _ring(radius, count), holes, warnings, area, inertia, inertia, label)


def ellipse_semiaxes(iy, iz):
    """Halbachsen einer Vollellipse mit diesen Biegeträgheiten.

    a liegt auf der lokalen Y-Achse, b auf der lokalen Z-Achse.
    IY = ∫ z² dA = π/4 · a · b³, IZ = ∫ y² dA = π/4 · a³ · b.
    """
    iy = float(iy)
    iz = float(iz)
    if not (iy > 0.0 and iz > 0.0):
        return None
    a = ((4.0 / math.pi) * math.sqrt(iz**3 / iy)) ** 0.25
    b = ((4.0 / math.pi) * math.sqrt(iy**3 / iz)) ** 0.25
    return a, b


def _ellipse(a, b, count):
    pts = []
    for i in range(count):
        ang = 2.0 * math.pi * i / count
        pts.append((a * math.cos(ang), b * math.sin(ang)))
    return pts


def general_profile(iy, iz, count=48):
    """Vollellipse mit denselben IY und IZ. Kein Fertigprofil."""
    warnings = [
        "SECTION='GENERALE' has no contour. A solid ellipse with the same IY and IZ is shown."
    ]
    try:
        axes = ellipse_semiaxes(iy, iz) if iy is not None and iz is not None else None
    except (TypeError, ValueError):
        axes = None
    if axes is None:
        warnings.append(
            "Without positive IY and IZ the ellipse cannot be drawn. Only the axes appear."
        )
        return Profile("GENERALE", [], warnings=warnings, label="GENERALE without IY/IZ")
    a, b = axes
    iy_v = math.pi / 4.0 * a * b**3
    iz_v = math.pi / 4.0 * a**3 * b
    return Profile(
        "GENERALE",
        _ellipse(a, b, count),
        [],
        warnings,
        math.pi * a * b,
        iy_v,
        iz_v,
        "Ellipse IY={:.4g} IZ={:.4g}".format(float(iy), float(iz)),
    )


def profile_from_cara(section, values):
    """values ist das Dict CARA → VALE eines POUTRE-Faktors."""
    section = (section or "").upper()
    if section == "RECTANGLE":
        if "HY" not in values or "HZ" not in values:
            return Profile("RECTANGLE", [], warnings=["RECTANGLE without HY/HZ."], label="Incomplete rectangle")
        return rectangle_profile(values["HY"], values["HZ"], values.get("EPY"), values.get("EPZ"))
    if section == "CERCLE":
        if "R" not in values:
            return Profile("CERCLE", [], warnings=["CERCLE without R."], label="Incomplete circle")
        return circle_profile(values["R"], values.get("EP"))
    if section == "GENERALE":
        folded = {str(key).upper(): value for key, value in values.items()}
        return general_profile(folded.get("IY"), folded.get("IZ"))
    if section == "COUDE":
        warnings_prefix = "COUDE: ovalisation is not shown, only the nominal geometry."
        if "R" in values:
            prof = circle_profile(values["R"], values.get("EP"))
        elif "HY" in values and "HZ" in values:
            prof = rectangle_profile(values["HY"], values["HZ"], values.get("EPY"), values.get("EPZ"))
        else:
            prof = Profile("COUDE", [], warnings=[], label="COUDE without dimensions")
        prof.warnings.insert(0, warnings_prefix)
        return prof
    return Profile(section or "?", [], warnings=["Unknown SECTION '{}'.".format(section)], label=section or "?")
