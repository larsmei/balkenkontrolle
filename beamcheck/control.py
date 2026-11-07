"""Kontrolle der aktiven Studie, ohne Dialog.

Der Schalter in der Befehlsleiste liest den offenen AsterStudy-Fall und das
dazu geladene Netz. Dateien sind nur der Ausweg, wenn kein passendes
SMESH-Netz in der Studie liegt.
"""

from __future__ import annotations

import os

from beamcheck.mesh_io import MeshError, edges_from_smesh, read_mail_file, read_med
from beamcheck.parser import CommError, parse_comm
from beamcheck.report import build_report
from beamcheck.smeshview import is_control_name


class ControlError(Exception):
    pass


def group_names(mesh):
    names = []
    try:
        groups = mesh.GetGroups() or []
    except Exception:
        return names
    for group in groups:
        try:
            names.append(group.GetName() or "")
        except Exception:
            continue
    return names


def needed_groups(parsed):
    names = set(parsed.beam_groups or ())
    for target in list(parsed.sections) + list(parsed.orientations):
        names.update(group for group in target.groups if group)
    return names


def rank_meshes(meshes, needed):
    """Bestes Netz zuerst. Kontrollnetze zählen nicht."""
    ranked = []
    for name, mesh in meshes:
        if is_control_name(name):
            continue
        present = set(group_names(mesh))
        score = len(needed & present) if needed else 0
        ranked.append((score, name, mesh))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [(name, mesh, score) for score, name, mesh in ranked]


def _read_mesh_file(path, mesh_format):
    ext = os.path.splitext(path)[1].lower()
    fmt = (mesh_format or "").upper()
    if fmt == "ASTER" or ext in (".mail", ".dat", ".txt"):
        try:
            return read_mail_file(path)
        except MeshError:
            if fmt == "ASTER":
                raise
    return read_med(path)


def _file_from_refs(parsed, file_refs):
    if not file_refs:
        return ""
    if parsed.mesh_unite is not None:
        for unit, candidate in file_refs:
            if unit == parsed.mesh_unite and os.path.isfile(candidate):
                return candidate
    for _unit, candidate in file_refs:
        if os.path.isfile(candidate) and os.path.splitext(candidate)[1].lower() in (
            ".med",
            ".mail",
            ".msh",
        ):
            return candidate
    return ""


def _edges_of_mesh(name, mesh):
    try:
        edges = edges_from_smesh(mesh)
    except MeshError:
        return None
    if not edges:
        return None
    return edges, "SMESH:" + name


def resolve_edges(parsed, file_refs, meshes, mesh_path=""):
    """Kanten der aktiven Studie. ``meshes`` ist eine Liste (Name, Netz)."""
    path = (mesh_path or "").strip()
    ranked = rank_meshes(meshes, needed_groups(parsed))
    if not path:
        usable = []
        for name, mesh, score in ranked:
            found = _edges_of_mesh(name, mesh)
            if found is None:
                continue
            usable.append((score, found))
        if usable:
            usable.sort(key=lambda item: -item[0])
            if len(usable) == 1 or usable[0][0] > 0 or len(ranked) == 1:
                return usable[0][1]
        path = _file_from_refs(parsed, file_refs)
    if path:
        if not os.path.isfile(path):
            from beamcheck.aster_access import mesh_from_entry

            mesh = mesh_from_entry(path)
            if mesh is not None:
                found = _edges_of_mesh(os.path.basename(path) or path, mesh)
                if found is not None:
                    return found
        return _read_mesh_file(path, parsed.mesh_format), path
    raise MeshError("No mesh found. The beam mesh must be loaded in SMESH.")


def visualize_active(meshes=None):
    """Zeichnet die Balken der aktiven Studie. Liefert die Hinweise."""
    from beamcheck.aster_access import current_case, list_smesh_meshes
    from beamcheck.smeshview import publish

    try:
        case = current_case()
    except Exception as exc:
        raise ControlError("The active study could not be read: {}".format(exc)) from exc
    try:
        parsed = parse_comm(case["text"])
    except CommError as exc:
        raise ControlError(str(exc)) from exc
    if not parsed.beam_groups and not parsed.all_edges_are_beams and not parsed.sections:
        raise ControlError("The active study has no beams (POU_D_*).")
    if meshes is None:
        try:
            meshes = list_smesh_meshes()
        except Exception as exc:
            raise ControlError("SMESH meshes could not be read: {}".format(exc)) from exc
    try:
        edges, origin = resolve_edges(parsed, case.get("files") or [], meshes)
    except MeshError as exc:
        raise ControlError(str(exc)) from exc
    report = build_report(parsed, edges)
    notes = publish(
        None,
        report,
        show_sections=True,
        show_axes=True,
        axis_fraction=0.22,
        solid=True,
        fit=True,
    )
    notes.insert(0, "Mesh: {} ({} edges).".format(origin, len(edges)))
    return notes
