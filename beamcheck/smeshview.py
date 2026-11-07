"""Zeigt die Kontrolle als SMESH-Netz in der Ansicht von AsterStudy.

GEOM wird nicht geöffnet. Das Netz heißt ``Balkenkontrolle`` und ersetzt
einen früheren Lauf. Querschnitte sind Flächengruppen, die Achsen
gefärbte Pfeile: X rot, Y grün, Z blau.
"""

from __future__ import annotations

from beamcheck.surface import axis_arrow, extrude_shell

MESH_NAME = "BeamCheck"
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
                "Section_" + beam.section_group,
                extrude_shell(origin, beam.ex, beam.ey, beam.ez, span, beam.profile.outer, beam.profile.holes),
            )
        if show_axes:
            mid = tuple((beam.p1[i] + beam.p2[i]) * 0.5 for i in range(3))
            alen = max(beam.length * axis_fraction, radius * 8)
            sides = {"X": beam.ey, "Y": beam.ez, "Z": beam.ey}
            for key, direction in (("X", beam.ex), ("Y", beam.ey), ("Z", beam.ez)):
                add(key, axis_arrow(mid, direction, alen, radius * 2.4, _normalize(sides[key])))
    return [(name, grouped[name]) for name in order]


def is_control_name(name):
    text = name or ""
    for prefix in (MESH_NAME, "Balkenkontrolle"):
        if text == prefix or text.startswith(prefix + "_"):
            return True
    return False


def choose_roots(nodes):
    """Welche Objekte weg müssen.

    ``nodes`` sind ``(entry, name, father_entry, father_is_component, sibling_names)``.
    Ein Netz, das nur Kontrollgruppen trägt, wird ganz entfernt, auch wenn es
    nicht ``Balkenkontrolle`` heißt. Einzelne Gruppen in einem fremden Netz bleiben
    einzeln. Komponenten (Mesh, Geometry) werden nie entfernt.
    """
    roots = []
    seen = set()
    for entry, name, father, father_is_component, siblings in nodes:
        if not is_control_name(name):
            continue
        target = entry
        if (
            not father_is_component
            and father
            and siblings
            and all(is_control_name(item) for item in siblings)
        ):
            target = father
        if target in seen:
            continue
        seen.add(target)
        roots.append(target)
    return roots


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


def _refresh_view(fit):
    import salome

    sg = getattr(salome, "sg", None)
    if sg is None:
        return
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
    _refresh_view(fit)


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
        notes.append("Nothing to draw.")
        return notes
    faces = collect_faces(report, show_sections, show_axes, axis_fraction, solid)
    if not faces:
        notes.append("No faces to draw.")
        return notes
    try:
        from salome.smesh import smeshBuilder
        import SMESH
    except Exception as exc:
        raise RuntimeError(
            "SMESH is not available ({}). The view stays in AsterStudy and needs the mesh module.".format(
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
            notes.append("{}: no face was created.".format(name))
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
        "AsterStudy: mesh {} with {} face groups (X red, Y green, Z blue).".format(MESH_NAME, len(entries)),
    )
    return notes


def _child_sobjects(study, sobj, recursive):
    iterator = study.NewChildIterator(sobj)
    iterator.InitEx(recursive)
    found = []
    while iterator.More():
        found.append(iterator.Value())
        iterator.Next()
    return found


def _sobj_name(sobj):
    try:
        return sobj.GetName() or ""
    except Exception:
        return ""


def _sobj_entry(sobj):
    try:
        return sobj.GetID() or ""
    except Exception:
        return ""


def clear():
    """Entfernt das Kontrollnetz aus Studie und Ansicht. AsterStudy bleibt aktiv."""
    import salome

    study = salome.myStudy
    notes = []
    entries_to_erase = []
    described = []
    by_entry = {}
    for component_name in ("SMESH", "GEOM"):
        component = study.FindComponent(component_name)
        if component is None:
            continue
        component_entry = _sobj_entry(component)
        for sobj in _child_sobjects(study, component, True):
            name = _sobj_name(sobj)
            if not is_control_name(name):
                continue
            entry = _sobj_entry(sobj)
            if not entry:
                continue
            by_entry[entry] = sobj
            entries_to_erase.append(entry)
            father = None
            try:
                father = sobj.GetFather()
            except Exception:
                father = None
            father_entry = _sobj_entry(father) if father is not None else ""
            father_is_component = father_entry == component_entry or not father_entry
            siblings = []
            if father is not None and not father_is_component:
                siblings = [_sobj_name(child) for child in _child_sobjects(study, father, False)]
                if father_entry:
                    by_entry.setdefault(father_entry, father)
            described.append((entry, name, father_entry, father_is_component, siblings))
    roots = choose_roots(described)
    for entry in roots:
        if entry not in entries_to_erase:
            entries_to_erase.append(entry)
    sg = getattr(salome, "sg", None)
    if sg is not None:
        for entry in entries_to_erase:
            for method, args in (("Erase", (entry,)), ("erase", (entry,)), ("SetVisibility", (entry, False))):
                fn = getattr(sg, method, None)
                if fn is None:
                    continue
                try:
                    fn(*args)
                except Exception:
                    continue
    removed = 0
    builder = study.NewBuilder()
    for entry in roots:
        sobj = by_entry.get(entry)
        if sobj is None:
            try:
                sobj = study.FindObjectID(entry)
            except Exception:
                sobj = None
        if sobj is None:
            continue
        name = _sobj_name(sobj) or MESH_NAME
        done = False
        obj = None
        try:
            obj = sobj.GetObject()
        except Exception:
            obj = None
        if obj is not None:
            try:
                from salome.smesh import smeshBuilder

                try:
                    smesh = smeshBuilder.New()
                except TypeError:
                    smesh = smeshBuilder.New(study)
                wrapped = obj
                try:
                    wrapped = smesh.Mesh(obj)
                except Exception:
                    wrapped = obj
                smesh.RemoveMesh(wrapped)
                done = True
            except Exception:
                done = False
        if not done:
            try:
                builder.RemoveObjectWithChildren(sobj)
                done = True
            except Exception as exc:
                notes.append("{} was not removed: {}".format(name, exc))
                continue
        removed += 1
    try:
        study.Modified()
    except Exception:
        pass
    _refresh_view(False)
    if removed:
        notes.insert(0, "Check display removed ({} objects).".format(removed))
    else:
        notes.append("No check display found.")
    return notes
