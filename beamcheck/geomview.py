"""Erzeugt die Kontrolle als GEOM-Körper im aktiven SALOME-Study.

Querschnitte werden als Prisma entlang des Stabes veröffentlicht, die lokalen
Achsen als Zylinder mit Kegel: X rot, Y grün, Z blau. Alles liegt unter
Namen mit dem Präfix ``Balkenkontrolle_`` und ersetzt einen früheren Lauf.
"""

from __future__ import annotations

PREFIX = "BeamCheck_"

# Gedämpfte Gruppenfarben, Achsen fest im RGB-Sinn der lokalen Basis.
_PALETTE = (
    (176, 122, 74),
    (150, 162, 172),
    (111, 143, 122),
    (168, 146, 120),
    (120, 132, 146),
    (186, 154, 112),
)
_AXIS_RGB = {"X": (196, 72, 58), "Y": (46, 140, 78), "Z": (46, 108, 186)}


def _normalize(v):
    n = (v[0] ** 2 + v[1] ** 2 + v[2] ** 2) ** 0.5
    if n < 1e-15:
        return (0.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def _place(origin, ey, ez, y, z):
    return (
        origin[0] + ey[0] * y + ez[0] * z,
        origin[1] + ey[1] * y + ez[1] * z,
        origin[2] + ey[2] * y + ez[2] * z,
    )


def _study_of(context):
    study = getattr(context, "study", None) if context is not None else None
    if study is not None:
        return study
    import salome

    return salome.myStudy


def _geompy(study):
    import salome
    from salome.geom import geomBuilder

    try:
        geompy = geomBuilder.New()
    except TypeError:
        geompy = geomBuilder.New(study)
    if hasattr(geompy, "init_geom"):
        try:
            geompy.init_geom(study)
        except Exception:
            pass
    return geompy


def _remove_previous(study):
    try:
        builder = study.NewBuilder()
    except Exception:
        return
    comp = None
    try:
        comp = study.FindComponent("GEOM")
    except Exception:
        return
    if comp is None:
        return
    doomed = []
    try:
        iterator = study.NewChildIterator(comp)
        iterator.InitEx(True)
        while iterator.More():
            sobj = iterator.Value()
            name = sobj.GetName() or ""
            if name.startswith(PREFIX):
                doomed.append(sobj)
            iterator.Next()
    except Exception:
        return
    for sobj in doomed:
        try:
            builder.RemoveObjectWithChildren(sobj)
        except Exception:
            try:
                builder.RemoveObject(sobj)
            except Exception:
                pass


def _extrude(geompy, face, origin, direction, span):
    """Prisma der Fläche entlang direction um span.

    SALOME 9: MakePrism(base, point1, point2).
    Ältere Stände nehmen MakePrismVecH(base, vector, höhe) oder MakePrism(base, vector).
    """
    end = tuple(origin[i] + direction[i] * span for i in range(3))
    p1 = geompy.MakeVertex(*origin)
    p2 = geompy.MakeVertex(*end)
    try:
        return geompy.MakePrism(face, p1, p2)
    except TypeError:
        pass
    vec_h = getattr(geompy, "MakePrismVecH", None)
    if callable(vec_h):
        try:
            return vec_h(face, geompy.MakeVectorDXDYDZ(*direction), span)
        except TypeError:
            pass
    return geompy.MakePrism(face, geompy.MakeVector(p1, p2))


def _wire(geompy, points):
    vertices = [geompy.MakeVertex(*point) for point in points]
    edges = []
    count = len(vertices)
    for index in range(count):
        edges.append(geompy.MakeEdge(vertices[index], vertices[(index + 1) % count]))
    return geompy.MakeWire(edges)


def _face(geompy, outer, holes):
    outer_wire = _wire(geompy, outer)
    if not holes:
        return geompy.MakeFace(outer_wire, True)
    wires = [outer_wire] + [_wire(geompy, hole) for hole in holes]
    try:
        return geompy.MakeFaceWires(wires, True)
    except Exception:
        face = geompy.MakeFace(outer_wire, True)
        for hole in holes:
            inner = geompy.MakeFace(_wire(geompy, hole), True)
            face = geompy.MakeCut(face, inner)
        return face


def _arrow(geompy, origin, direction, length, radius):
    direction = _normalize(direction)
    axis = geompy.MakeVectorDXDYDZ(*direction)
    start = geompy.MakeVertex(*origin)
    shaft = length * 0.78
    head = length - shaft
    cylinder = geompy.MakeCylinder(start, axis, radius, shaft)
    tip = (
        origin[0] + direction[0] * shaft,
        origin[1] + direction[1] * shaft,
        origin[2] + direction[2] * shaft,
    )
    cone = geompy.MakeCone(geompy.MakeVertex(*tip), axis, radius * 2.4, 0.0, head)
    return geompy.MakeCompound([cylinder, cone])


def _publish(geompy, shape, name):
    entry = geompy.addToStudy(shape, name)
    return entry


def _paint(entry, rgb, transparency):
    if not entry:
        return
    import salome

    targets = []
    sg = getattr(salome, "sg", None)
    if sg is not None:
        targets.append(sg)
    try:
        targets.append(salome.ImportComponentGUI("GEOM"))
    except Exception:
        pass
    for target in targets:
        done = False
        for args in ((rgb[0], rgb[1], rgb[2]), (rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)):
            try:
                target.SetColor(entry, *args)
                done = True
                break
            except Exception:
                continue
        if done:
            break
    for target in targets:
        try:
            target.SetDisplayMode(entry, 1)
            break
        except Exception:
            continue
    if transparency:
        for target in targets:
            try:
                target.SetTransparency(entry, float(transparency))
                break
            except Exception:
                continue
    for target in targets:
        for meth in ("Display", "display"):
            fn = getattr(target, meth, None)
            if fn is None:
                continue
            try:
                fn(entry)
                return
            except Exception:
                continue


def _refresh(activate):
    import salome

    sg = getattr(salome, "sg", None)
    if sg is None:
        return
    for meth in ("updateObjBrowser", "UpdateObjBrowser"):
        fn = getattr(sg, meth, None)
        if fn is None:
            continue
        try:
            fn(True)
        except TypeError:
            try:
                fn()
            except Exception:
                pass
        except Exception:
            pass
        break
    if activate:
        for meth in ("activateModule", "ActivateModule"):
            fn = getattr(sg, meth, None)
            if fn is None:
                continue
            try:
                fn("GEOM")
            except Exception:
                continue
            break
    for meth in ("FitAll", "fitAll"):
        fn = getattr(sg, meth, None)
        if fn is None:
            continue
        try:
            fn()
        except Exception:
            pass
        break


def publish(context, report, show_sections=True, show_axes=True, axis_fraction=0.22, solid=True, activate_geom=True):
    """Baut die GEOM-Darstellung. Gibt eine Liste von Protokollzeilen zurück."""
    study = _study_of(context)
    geompy = _geompy(study)
    _remove_previous(study)
    notes = []
    if not report.beams:
        notes.append("Nothing to draw.")
        return notes

    lengths = [beam.length for beam in report.beams]
    reach = max(lengths) if lengths else 1.0
    radius = max(reach * axis_fraction * 0.035, reach * 0.004)

    section_shapes = {}
    axis_shapes = {"X": [], "Y": [], "Z": []}
    palette_index = {}

    for beam in report.beams:
        if show_sections and beam.profile.outer:
            span = beam.length if solid else min(beam.length * 0.05, max(beam.length * 0.02, radius * 4))
            if solid:
                origin = beam.p1
            else:
                mid = tuple((beam.p1[i] + beam.p2[i]) * 0.5 for i in range(3))
                origin = tuple(mid[i] - beam.ex[i] * span * 0.5 for i in range(3))
            outer = [_place(origin, beam.ey, beam.ez, y, z) for y, z in beam.profile.outer]
            holes = [
                [_place(origin, beam.ey, beam.ez, y, z) for y, z in hole] for hole in beam.profile.holes
            ]
            try:
                face = _face(geompy, outer, holes)
                prism = _extrude(geompy, face, origin, beam.ex, span)
            except Exception as exc:
                notes.append("{}: section was not created ({})".format(beam.name, exc))
                prism = None
            if prism is not None:
                section_shapes.setdefault(beam.section_group, []).append(prism)
                if beam.section_group not in palette_index:
                    palette_index[beam.section_group] = len(palette_index)
        if show_axes:
            mid = tuple((beam.p1[i] + beam.p2[i]) * 0.5 for i in range(3))
            alen = max(beam.length * axis_fraction, radius * 8)
            for key, direction in (("X", beam.ex), ("Y", beam.ey), ("Z", beam.ez)):
                try:
                    axis_shapes[key].append(_arrow(geompy, mid, direction, alen, radius))
                except Exception as exc:
                    notes.append("{}: axis {} was not created ({})".format(beam.name, key, exc))

    for group, shapes in section_shapes.items():
        compound = shapes[0] if len(shapes) == 1 else geompy.MakeCompound(shapes)
        name = PREFIX + "Section_" + group
        entry = _publish(geompy, compound, name)
        color = _PALETTE[palette_index[group] % len(_PALETTE)]
        _paint(entry, color, 0.28)
    for key, shapes in axis_shapes.items():
        if not shapes:
            continue
        compound = shapes[0] if len(shapes) == 1 else geompy.MakeCompound(shapes)
        entry = _publish(geompy, compound, PREFIX + "Axis_" + key)
        _paint(entry, _AXIS_RGB[key], 0.0)
    _refresh(activate_geom)
    notes.insert(
        0,
        "GEOM updated: {} section groups, axes {}.".format(
            len(section_shapes),
            "on" if show_axes else "off",
        ),
    )
    return notes
