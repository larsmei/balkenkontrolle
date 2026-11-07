"""Zeigt die Kontrolle als SMESH-Netz in der Ansicht von AsterStudy.

GEOM wird nicht geöffnet. Das Netz heißt ``Balkenkontrolle`` und ersetzt
einen früheren Lauf. Querschnitte sind Flächengruppen, die Achsen
gefärbte Pfeile: X rot, Y grün, Z blau.
"""

from __future__ import annotations

from beamcheck.surface import axis_arrow, extrude_shell

MESH_NAME = "Balkenkontrolle"
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


def collect_faces(report, show_sections=True, show_axes=True, axis_fraction=0.22, solid=True):
    """Gruppenname → Liste von Dreiecken. Reihenfolge der Gruppen bleibt stabil."""
    grouped = {}
    order = []

    def add(name, triangles):
        if not triangles:
            return
        if name not in grouped:
            grouped[name] = []
            order.append(name)
        grouped[name].extend(triangles)

    lengths = [beam.length for beam in report.beams]
    reach = max(lengths) if lengths else 1.0
    radius = max(reach * axis_fraction * 0.035, reach * 0.004)
    for beam in report.beams:
        if show_sections and beam.profile.outer:
            span = beam.length if solid else min(beam.length * 0.05, max(beam.length * 0.02, radius * 4))
            if solid:
                origin = beam.p1
            else:
                mid = tuple((beam.p1[i] + beam.p2[i]) * 0.5 for i in range(3))
                origin = tuple(mid[i] - beam.ex[i] * span * 0.5 for i in range(3))
            add(
                "Querschnitt_" + beam.section_group,
                extrude_shell(origin, beam.ex, beam.ey, beam.ez, span, beam.profile.outer, beam.profile.holes),
            )
        if show_axes:
            mid = tuple((beam.p1[i] + beam.p2[i]) * 0.5 for i in range(3))
            alen = max(beam.length * axis_fraction, radius * 8)
            sides = {"X": beam.ey, "Y": beam.ez, "Z": beam.ey}
            for key, direction in (("X", beam.ex), ("Y", beam.ey), ("Z", beam.ez)):
                add(key, axis_arrow(mid, direction, alen, radius * 2.4, _normalize(sides[key])))
    return [(name, grouped[name]) for name in order]


def _color_of(name, section_index):
    if name in _AXIS_RGB:
        return _AXIS_RGB[name], 0.0
    return _PALETTE[section_index % len(_PALETTE)], 0.28


def _new_mesh(smesh):
    mesh = None
    try:
        mesh = smesh.Mesh(None, MESH_NAME)
    except Exception:
        mesh = smesh.Mesh()
    for call in (
        lambda: mesh.SetName(MESH_NAME),
        lambda: smesh.SetName(mesh.GetMesh(), MESH_NAME),
    ):
        try:
            call()
            return mesh
        except Exception:
            continue
    return mesh


def _drop_previous(smesh):
    try:
        meshes = list(smesh.GetMeshes())
    except Exception:
        return
    for mesh in meshes:
        try:
            name = mesh.GetName()
        except Exception:
            continue
        if name == MESH_NAME or (name or "").startswith(MESH_NAME + "_"):
            try:
                smesh.RemoveMesh(mesh)
            except Exception:
                pass


def _add_face(mesh, triangle):
    ids = []
    for point in triangle:
        ids.append(mesh.AddNode(float(point[0]), float(point[1]), float(point[2])))
    face = mesh.AddFace(ids)
    try:
        if int(face) <= 0:
            return None
    except (TypeError, ValueError):
        pass
    return face


def _fill_group(group, ids):
    try:
        group.Add(list(ids))
        return
    except Exception:
        pass
    for element in ids:
        group.Add([element])


def _entry_of(obj):
    import salome

    for candidate in (obj, getattr(obj, "GetMesh", lambda: None)(), getattr(obj, "GetGroup", lambda: None)()):
        if candidate is None:
            continue
        try:
            sobj = salome.ObjectToSObject(candidate)
        except Exception:
            continue
        if sobj is not None:
            entry = sobj.GetID()
            if entry:
                return entry
    return None


def _paint(entry, rgb, transparency):
    if not entry:
        return
    import salome

    targets = []
    sg = getattr(salome, "sg", None)
    if sg is not None:
        targets.append(sg)
    try:
        targets.append(salome.ImportComponentGUI("SMESH"))
    except Exception:
        pass
    channels = (
        (rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0),
        (float(rgb[0]), float(rgb[1]), float(rgb[2])),
    )
    for target in targets:
        for args in channels:
            try:
                target.SetColor(entry, *args)
                break
            except Exception:
                continue
        for mode in (1, 2):
            try:
                target.SetDisplayMode(entry, mode)
                break
            except Exception:
                continue
        if transparency:
            try:
                target.SetTransparency(entry, float(transparency))
            except Exception:
                pass


def _show_in_asterstudy(entries, fit):
    import salome

    sg = getattr(salome, "sg", None)
    if sg is None:
        return
    for entry in entries:
        try:
            sg.Display(entry)
        except Exception:
            pass
    for name in ("UpdateView", "updateView"):
        fn = getattr(sg, name, None)
        if fn is None:
            continue
        try:
            fn()
        except Exception:
            pass
        break
    if fit:
        for name in ("FitAll", "fitAll"):
            fn = getattr(sg, name, None)
            if fn is None:
                continue
            try:
                fn()
            except Exception:
                pass
            break
    for name in ("updateObjBrowser", "UpdateObjBrowser"):
        fn = getattr(sg, name, None)
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
    # Anzeige eines SMESH-Netzes darf AsterStudy nicht verlassen.
    for name in ("activateModule", "ActivateModule"):
        fn = getattr(sg, name, None)
        if fn is None:
            continue
        try:
            fn("ASTERSTUDY")
        except Exception:
            continue
        break
    _ping_asterstudy()


def _ping_asterstudy():
    try:
        from asterstudy.gui import AsterGui
    except Exception:
        return
    try:
        gui = AsterGui.instance()
    except Exception:
        return
    if gui is None:
        return
    for name in ("update", "Update"):
        fn = getattr(gui, name, None)
        if not callable(fn):
            continue
        try:
            fn()
        except Exception:
            pass


def publish(context, report, show_sections=True, show_axes=True, axis_fraction=0.22, solid=True, fit=True):
    """Baut das SMESH-Netz und zeigt es, ohne nach GEOM zu wechseln."""
    del context
    notes = []
    if not report.beams:
        notes.append("Nichts zu zeichnen.")
        return notes
    faces = collect_faces(report, show_sections, show_axes, axis_fraction, solid)
    if not faces:
        notes.append("Keine Flächen zu zeichnen.")
        return notes
    try:
        from salome.smesh import smeshBuilder
        import SMESH
    except Exception as exc:
        raise RuntimeError(
            "SMESH ist nicht verfügbar ({}). Die Ansicht liegt im AsterStudy-Modul und braucht das Mesh-Modul.".format(
                exc
            )
        ) from exc
    try:
        smesh = smeshBuilder.New()
    except TypeError:
        import salome

        smesh = smeshBuilder.New(salome.myStudy)
    _drop_previous(smesh)
    mesh = _new_mesh(smesh)
    entries = []
    section_index = 0
    try:
        import SALOMEDS
    except Exception:
        SALOMEDS = None
    for name, triangles in faces:
        ids = []
        for triangle in triangles:
            face = _add_face(mesh, triangle)
            if face is not None:
                ids.append(face)
        if not ids:
            notes.append("{}: keine Fläche erzeugt.".format(name))
            continue
        group_name = MESH_NAME + "_" + name
        group = mesh.CreateEmptyGroup(SMESH.FACE, group_name)
        _fill_group(group, ids)
        rgb, transparency = _color_of(name, section_index)
        if name not in _AXIS_RGB:
            section_index += 1
        if SALOMEDS is not None:
            try:
                group.SetColor(SALOMEDS.Color(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0))
            except Exception:
                pass
        entry = _entry_of(group)
        _paint(entry, rgb, transparency)
        if entry:
            entries.append(entry)
    if not entries:
        entry = _entry_of(mesh)
        if entry:
            entries.append(entry)
    _show_in_asterstudy(entries, fit)
    notes.insert(
        0,
        "AsterStudy: Netz {} mit {} Flächengruppen (X rot, Y grün, Z blau).".format(MESH_NAME, len(entries)),
    )
    return notes
