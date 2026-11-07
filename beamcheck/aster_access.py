"""Liest den aktuellen AsterStudy-Fall.

Die laufende Studie hängt an ``ASTERSTUDYGUI.get_aster_gui()`` (Attribut
``aster_gui``). ``AsterGui.instance()`` gibt es in aktuellen Ständen nicht.
Dateien der Stufe liegen in ``stage.handle2info`` (Einheit → Dateiname).
"""

from __future__ import annotations

import os


def _unwrap(value):
    """Eigenschaft oder Methode ohne Argumente."""
    if not callable(value):
        return value
    try:
        return value()
    except TypeError:
        return value
    except Exception:
        return None


def _live_gui(modules):
    """Bereits erzeugtes AsterStudy-GUI. Legt kein zweites leeres an."""
    found = []
    for mod in modules:
        if mod is None:
            continue
        getter = getattr(mod, "get_aster_gui", None)
        if not callable(getter) or not hasattr(getter, "aster_gui"):
            continue
        try:
            gui = getter()
        except Exception:
            continue
        if gui is not None:
            found.append(gui)
    for gui in found:
        if _unwrap(getattr(gui, "study", None)) is not None:
            return gui
    return found[0] if found else None


def _import_live_gui():
    import sys

    gui = _live_gui(list(sys.modules.values()))
    if gui is not None:
        return gui
    try:
        import ASTERSTUDYGUI
    except ImportError:
        ASTERSTUDYGUI = None
    if ASTERSTUDYGUI is not None:
        gui = _live_gui([ASTERSTUDYGUI])
        if gui is not None:
            return gui
    errors = []
    for import_path in ("asterstudy.gui.astergui", "asterstudy.gui"):
        try:
            module = __import__(import_path, fromlist=["AsterGui"])
        except ImportError as exc:
            errors.append(str(exc))
            continue
        cls = getattr(module, "AsterGui", None)
        if cls is None:
            continue
        for attr in ("instance", "gui"):
            factory = getattr(cls, attr, None)
            if not callable(factory):
                continue
            try:
                gui = factory()
            except Exception as exc:
                errors.append(str(exc))
                continue
            if gui is not None and _unwrap(getattr(gui, "study", None)) is not None:
                return gui
    detail = "; ".join(errors[:3])
    raise RuntimeError(
        "AsterStudy GUI was not found. The module must be open"
        + (" ({})".format(detail) if detail else ".")
    )


def stage_text(stage):
    text = None
    getter = getattr(stage, "get_text", None)
    if callable(getter):
        try:
            text = getter()
        except TypeError:
            try:
                text = getter(pretty=False)
            except Exception:
                text = None
        except Exception:
            text = None
    if isinstance(text, str) and text.strip():
        return text
    dataset = _unwrap(getattr(stage, "dataset", None))
    if dataset is not None:
        raw = getattr(dataset, "text", None)
        if isinstance(raw, str) and raw.strip():
            return raw
    for attr in ("text", "comm"):
        value = getattr(stage, attr, None)
        if isinstance(value, str) and value.strip():
            return value
    commands = None
    for attr in ("commands", "sorted_commands"):
        value = _unwrap(getattr(stage, attr, None))
        if value:
            try:
                commands = list(value)
            except TypeError:
                commands = None
            if commands:
                break
    parts = []
    for cmd in commands or []:
        piece = None
        cmd_get = getattr(cmd, "get_text", None)
        if callable(cmd_get):
            try:
                piece = cmd_get()
            except Exception:
                piece = None
        if not isinstance(piece, str):
            piece = getattr(cmd, "text", None)
        if isinstance(piece, str) and piece.strip():
            parts.append(piece)
    if parts:
        return "\n".join(parts)
    return None


def _abs_path(path, history):
    path = str(path).strip()
    if not path:
        return None
    if os.path.isabs(path) or os.path.isfile(path):
        return path
    roots = []
    for attr in ("folder", "tmpdir"):
        root = getattr(history, attr, None) if history is not None else None
        if isinstance(root, str) and root:
            roots.append(root)
    for root in roots:
        candidate = path if os.path.isabs(path) else os.path.join(root, path)
        if os.path.isfile(candidate):
            return candidate
        base = os.path.basename(path)
        embedded = os.path.join(root, base)
        if base and os.path.isfile(embedded):
            return embedded
    return path


def stage_files(stage, history=None):
    found = []
    seen = set()

    def add(unit, path):
        path = _abs_path(path, history)
        if not path:
            return
        try:
            unit = int(unit) if unit is not None and not isinstance(unit, int) else unit
        except (TypeError, ValueError):
            unit = None
        key = (unit, path)
        if key in seen:
            return
        seen.add(key)
        found.append((unit if isinstance(unit, int) else None, path))

    handle_map = _unwrap(getattr(stage, "handle2info", None))
    if isinstance(handle_map, dict):
        for key, entry in handle_map.items():
            if isinstance(entry, str):
                add(key, entry)
                continue
            path = (
                getattr(entry, "filename", None)
                or getattr(entry, "path", None)
                or getattr(entry, "server_path", None)
            )
            unit = getattr(entry, "unit", None)
            if unit is None:
                unit = key
            add(unit, path)
    for attr in ("files", "datafiles", "units", "file_dict"):
        bag = _unwrap(getattr(stage, attr, None))
        if not bag:
            continue
        items = bag.items() if isinstance(bag, dict) else None
        if items is None:
            try:
                seq = list(bag)
            except TypeError:
                continue
            items = [(getattr(entry, "unit", None), entry) for entry in seq]
        for key, entry in items:
            if isinstance(entry, str):
                add(key if isinstance(key, int) else None, entry)
                continue
            path = (
                getattr(entry, "filename", None)
                or getattr(entry, "path", None)
                or getattr(entry, "server_path", None)
            )
            unit = getattr(entry, "unit", None)
            if unit is None and isinstance(key, int):
                unit = key
            add(unit, path)
    return found


def _stages_of(case):
    stages = _unwrap(getattr(case, "stages", None))
    if stages:
        try:
            return list(stages)
        except TypeError:
            pass
    try:
        return list(case)
    except TypeError:
        return []


def read_case(gui):
    """``{text, files}`` aus einem bereits erzeugten AsterGui."""
    study = _unwrap(getattr(gui, "study", None))
    if study is None:
        raise RuntimeError("AsterStudy has no open study.")
    history = _unwrap(getattr(study, "history", None))
    if history is None:
        raise RuntimeError("The AsterStudy study has no history.")
    case = _unwrap(getattr(history, "current_case", None))
    if case is None:
        cases = _unwrap(getattr(history, "cases", None)) or []
        try:
            case = list(cases)[-1] if cases else None
        except TypeError:
            case = None
    if case is None:
        raise RuntimeError("There is no current AsterStudy case.")
    texts = []
    files = []
    for stage in _stages_of(case):
        text = stage_text(stage)
        if text:
            texts.append(text)
        files.extend(stage_files(stage, history))
    if not texts:
        raise RuntimeError(
            "The case has no readable command text. "
            "The stage must contain commands, graphical or as text."
        )
    return {"text": "\n\n".join(texts), "files": files}


def current_case():
    """Text aller Stufen und bekannte Dateien (unit, path)."""
    return read_case(_import_live_gui())


def mesh_from_entry(entry):
    """SMESH-Netz zu einer SALOME-Entry, sonst None."""
    try:
        import salome
        from salome.smesh import smeshBuilder
    except ImportError:
        return None
    try:
        sobj = salome.myStudy.FindObjectID(str(entry))
    except Exception:
        return None
    if sobj is None:
        return None
    try:
        obj = sobj.GetObject()
    except Exception:
        return None
    if obj is None:
        return None
    try:
        smesh = smeshBuilder.New()
    except TypeError:
        smesh = smeshBuilder.New(salome.myStudy)
    try:
        mesh = smesh.Mesh(obj)
        mesh.NbNodes()
    except Exception:
        return None
    return mesh


def list_smesh_meshes():
    """Liste (Name, Mesh-Wrapper) aller SMESH-Netze im Study."""
    import salome
    from salome.smesh import smeshBuilder

    try:
        smesh = smeshBuilder.New()
    except TypeError:
        smesh = smeshBuilder.New(salome.myStudy)
    study = salome.myStudy
    component = study.FindComponent("SMESH")
    if component is None:
        return []
    found = []
    seen = set()
    iterator = study.NewChildIterator(component)
    iterator.InitEx(True)
    while iterator.More():
        sobj = iterator.Value()
        iterator.Next()
        obj = sobj.GetObject()
        if obj is None:
            continue
        try:
            mesh = smesh.Mesh(obj)
            count = mesh.NbNodes()
        except Exception:
            continue
        if count <= 0:
            continue
        name = sobj.GetName() or "Mesh"
        key = (name, count, mesh.GetId() if hasattr(mesh, "GetId") else id(mesh))
        if key in seen:
            continue
        seen.add(key)
        found.append((name, mesh))
    return found
