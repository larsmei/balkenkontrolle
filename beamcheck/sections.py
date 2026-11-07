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
        warnings.append("HY und HZ müssen positiv sein.")
        return Profile("RECTANGLE", [], warnings=warnings, label="Rechteck ungültig")
    holes = []
    area = hy * hz
    iy = hy * hz**3 / 12.0
    iz = hz * hy**3 / 12.0
    hollow = epy is not None or epz is not None
    if hollow:
        epy_v = 0.0 if epy is None else float(epy)
        epz_v = 0.0 if epz is None else float(epz)
        if epy_v < 0 or epz_v < 0:
            warnings.append("Wanddicken dürfen nicht negativ sein.")
        inner_y = hy - 2.0 * epy_v
        inner_z = hz - 2.0 * epz_v
        if inner_y <= 1e-9 or inner_z <= 1e-9:
            warnings.append(
                "Die Wanddicke füllt den Rechteckquerschnitt. Dargestellt wird der Vollquerschnitt."
            )
        else:
            holes.append(_rect(inner_y, inner_z, clockwise=True))
            area = hy * hz - inner_y * inner_z
            iy = (hy * hz**3 - inner_y * inner_z**3) / 12.0
            iz = (hz * hy**3 - inner_z * inner_y**3) / 12.0
    label = "Rechteck HY={:.4g} HZ={:.4g}".format(hy, hz)
    if hollow and holes:
        label += " hohl"
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
        warnings.append("R muss positiv sein.")
        return Profile("CERCLE", [], warnings=warnings, label="Kreis ungültig")
    holes = []
    area = math.pi * radius**2
    inertia = math.pi * radius**4 / 4.0
    label = "Kreis R={:.4g}".format(radius)
    if ep is not None:
        ep_v = float(ep)
        if ep_v < 0:
            warnings.append("EP darf nicht negativ sein.")
        elif ep_v > radius + 1e-9:
            warnings.append("EP > R. Dargestellt wird der Vollkreis.")
        elif ep_v < radius - 1e-12:
            ri = radius - ep_v
            holes.append(_ring(ri, count, clockwise=True))
            area = math.pi * (radius**2 - ri**2)
            inertia = math.pi * (radius**4 - ri**4) / 4.0
            label = "Rohr R={:.4g} EP={:.4g}".format(radius, ep_v)
    return Profile("CERCLE", _ring(radius, count), holes, warnings, area, inertia, inertia, label)


def general_profile(ry, rz, count=48):
    """Hüllellipse aus den Faserabständen RY, RZ. Kein echtes Profil."""
    warnings = [
        "SECTION='GENERALE' hat keine Kontur. Gezeigt wird die Hülle ±RY, ±RZ, nicht das Fertigprofil."
    ]
    if ry is None or rz is None or float(ry) <= 0 or float(rz) <= 0:
        warnings.append("Ohne positive RY und RZ kann keine Hülle gezeichnet werden. Nur die Achsen erscheinen.")
        return Profile("GENERALE", [], warnings=warnings, label="GENERALE ohne Hülle")
    ry = float(ry)
    rz = float(rz)
    outer = []
    for i in range(count):
        ang = 2.0 * math.pi * i / count
        outer.append((ry * math.cos(ang), rz * math.sin(ang)))
    return Profile(
        "GENERALE",
        outer,
        [],
        warnings,
        label="Hülle RY={:.4g} RZ={:.4g}".format(ry, rz),
    )


def profile_from_cara(section, values):
    """values ist das Dict CARA → VALE eines POUTRE-Faktors."""
    section = (section or "").upper()
    if section == "RECTANGLE":
        if "HY" not in values or "HZ" not in values:
            return Profile("RECTANGLE", [], warnings=["RECTANGLE ohne HY/HZ."], label="Rechteck unvollständig")
        return rectangle_profile(values["HY"], values["HZ"], values.get("EPY"), values.get("EPZ"))
    if section == "CERCLE":
        if "R" not in values:
            return Profile("CERCLE", [], warnings=["CERCLE ohne R."], label="Kreis unvollständig")
        return circle_profile(values["R"], values.get("EP"))
    if section == "GENERALE":
        return general_profile(values.get("RY"), values.get("RZ"))
    if section == "COUDE":
        warnings_prefix = "COUDE: Ovalisierung wird nicht dargestellt, nur die Nenngeometrie."
        if "R" in values:
            prof = circle_profile(values["R"], values.get("EP"))
        elif "HY" in values and "HZ" in values:
            prof = rectangle_profile(values["HY"], values["HZ"], values.get("EPY"), values.get("EPZ"))
        else:
            prof = Profile("COUDE", [], warnings=[], label="COUDE ohne Maße")
        prof.warnings.insert(0, warnings_prefix)
        return prof
    return Profile(section or "?", [], warnings=["Unbekannte SECTION '{}'.".format(section)], label=section or "?")
