"""Liest den aktuellen AsterStudy-Fall, soweit die jeweilige Version das hergibt.

AsterStudy hat keine stabile Skript-API. Es werden mehrere bekannte Zugriffe
versucht. Schlägt das fehl, bleiben Dateiauswahl und SMESH-Netz übrig.
"""

from __future__ import annotations


def _gui():
    try:
        from asterstudy.gui.astergui import AsterGui
    except ImportError:
        from asterstudy.gui import AsterGui
    for attr in ("instance", "gui"):
        factory = getattr(AsterGui, attr, None)
        if callable(factory):
            return factory()
    raise RuntimeError("AsterGui hat weder instance() noch gui().")


def _call(obj, name, variants):
    fn = getattr(obj, name, None)
    if fn is None:
        return None
    if not callable(fn):
        return fn
    for args, kwargs in variants:
        try:
            return fn(*args, **kwargs)
        except TypeError:
            continue
        except Exception:
            return None
    return None


def stage_text(stage):
    text = _call(stage, "get_text", [((), {}), ((), {"pretty": True}), ((), {"sort": True})])
    if isinstance(text, str) and text.strip():
        return text
    for attr in ("text", "comm"):
        value = getattr(stage, attr, None)
        if isinstance(value, str) and value.strip():
            return value
    commands = None
    for attr in ("commands", "sorted_commands"):
        value = getattr(stage, attr, None)
        if value:
            commands = list(value)
            break
    if commands is None:
        try:
            commands = list(stage)
        except Exception:
            commands = []
    parts = []
    for cmd in commands:
        piece = _call(cmd, "get_text", [((), {}), ((), {"pretty": True})])
        if not isinstance(piece, str):
            piece = getattr(cmd, "text", None)
        if isinstance(piece, str) and piece.strip():
            parts.append(piece)
    if parts:
        return "\n".join(parts)
    return None


def stage_files(stage):
    found = []
    bags = []
    for attr in ("files", "datafiles", "units", "file_dict"):
        value = getattr(stage, attr, None)
        if value:
            bags.append(value)
    for bag in bags:
        items = bag.items() if isinstance(bag, dict) else None
        if items is None:
            try:
                seq = list(bag)
            except Exception:
                continue
            items = [(getattr(entry, "unit", None), entry) for entry in seq]
        for key, entry in items:
            if isinstance(entry, str):
                path = entry
                unit = key if isinstance(key, int) else None
            else:
                path = (
                    getattr(entry, "filename", None)
                    or getattr(entry, "path", None)
                    or getattr(entry, "server_path", None)
                )
                unit = getattr(entry, "unit", None)
                if unit is None and isinstance(key, int):
                    unit = key
            if path:
                try:
                    unit = int(unit) if unit is not None else None
                except (TypeError, ValueError):
                    unit = None
                found.append((unit, str(path)))
    return found


def current_case():
    """Text aller Stufen und bekannte Dateien (unit, path).

    Wirft RuntimeError, wenn AsterStudy nicht geladen ist.
    """
    gui = _gui()
    study = _call(gui, "study", [((), {})])
    if study is None:
        study = getattr(gui, "study", None)
    history = getattr(study, "history", None)
    case = getattr(history, "current_case", None) if history is not None else None
    if case is None:
        raise RuntimeError("Kein aktueller AsterStudy-Fall.")
    stages = list(getattr(case, "stages", []) or [])
    texts = []
    files = []
    for stage in stages:
        text = stage_text(stage)
        if text:
            texts.append(text)
        files.extend(stage_files(stage))
    if not texts:
        raise RuntimeError(
            "Der Fall enthält keinen lesbaren Kommando-Text. "
            "Bitte die Stufe im Textmodus exportieren und als Datei wählen."
        )
    return {"text": "\n\n".join(texts), "files": files}


def list_smesh_meshes():
    """Liste (Name, Mesh-Wrapper) aller SMESH-Netze im Study."""
    import salome
    from salome.smesh import smeshBuilder

    smesh = smeshBuilder.New()
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
        name = sobj.GetName() or "Netz"
        key = (name, count, mesh.GetId() if hasattr(mesh, "GetId") else id(mesh))
        if key in seen:
            continue
        seen.add(key)
        found.append((name, mesh))
    return found
