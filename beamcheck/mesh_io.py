"""Kanten aus einer ASTER-mail, einer MED-Datei oder einem SMESH-Netz."""

from __future__ import annotations

from dataclasses import dataclass, field


class MeshError(Exception):
    pass


@dataclass
class Edge:
    name: str
    p1: tuple
    p2: tuple
    groups: tuple = field(default_factory=tuple)


def _fortran_float(token):
    return float(token.replace("D", "E").replace("d", "e"))


def read_mail(text):
    """Liest FORMAT='ASTER' (mail): COOR_3D, SEG2/SEG3, GROUP_MA."""
    nodes = {}
    elements = {}
    groups = {}
    mode = None
    current_group = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("%"):
            continue
        upper = line.upper()
        if upper in ("COOR_3D", "SEG2", "SEG3", "GROUP_MA", "GROUP_NO", "FINSF", "FIN", "TITRE"):
            if upper == "FINSF":
                mode = None
                current_group = None
            elif upper == "FIN":
                break
            elif upper == "GROUP_MA":
                mode = "GROUP_MA"
                current_group = None
                if "NOM=" in upper:
                    current_group = line.split("=", 1)[1].strip()
                    groups.setdefault(current_group, [])
            else:
                mode = upper
                current_group = None
            continue
        if mode == "TITRE":
            continue
        if mode == "COOR_3D":
            parts = line.split()
            if len(parts) < 4:
                raise MeshError("COOR_3D-Zeile unvollständig: {}".format(line))
            nodes[parts[0]] = (
                _fortran_float(parts[1]),
                _fortran_float(parts[2]),
                _fortran_float(parts[3]),
            )
        elif mode in ("SEG2", "SEG3"):
            parts = line.split()
            if len(parts) < 3:
                raise MeshError("{}-Zeile unvollständig: {}".format(mode, line))
            # Code_Aster: SEG3-Endknoten sind die beiden ersten Nummern.
            elements[parts[0]] = (parts[1], parts[2])
        elif mode == "GROUP_MA":
            parts = line.split()
            if current_group is None and len(parts) == 1 and parts[0] not in elements:
                current_group = parts[0]
                groups.setdefault(current_group, [])
                continue
            if current_group is None:
                raise MeshError("GROUP_MA ohne Gruppenname vor: {}".format(line))
            for token in parts:
                if token not in elements and len(parts) == 1:
                    current_group = token
                    groups.setdefault(current_group, [])
                else:
                    groups[current_group].append(token)
        elif mode == "GROUP_NO":
            continue
    if not elements:
        raise MeshError("Die mail-Datei enthält keine SEG2/SEG3.")
    membership = {}
    for gname, mails in groups.items():
        for mail in mails:
            membership.setdefault(mail, []).append(gname)
    edges = []
    missing = []
    for name, (n1, n2) in elements.items():
        if n1 not in nodes or n2 not in nodes:
            missing.append(name)
            continue
        edges.append(Edge(name, nodes[n1], nodes[n2], tuple(membership.get(name, ()))))
    if missing:
        raise MeshError("Knoten fehlen für Elemente: {}".format(", ".join(missing[:8])))
    return edges


def read_mail_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return read_mail(handle.read())


def _numpy(array):
    if hasattr(array, "toNumPyArray"):
        return array.toNumPyArray()
    return array


def read_med(path):
    """Liest Kanten der Dimension 1 über MEDLoader (nur innerhalb von SALOME)."""
    try:
        import MEDLoader as ml
    except ImportError as exc:
        raise MeshError("MEDLoader ist nicht verfügbar ({}).".format(exc)) from exc
    try:
        names = list(ml.GetMeshNames(path))
    except Exception as exc:
        raise MeshError("MED-Datei nicht lesbar: {}".format(exc)) from exc
    if not names:
        raise MeshError("Die MED-Datei enthält kein Netz.")
    errors = []
    for name in names:
        try:
            edges = _edges_from_med(ml, path, name)
        except Exception as exc:
            errors.append("{}: {}".format(name, exc))
            continue
        if edges:
            return edges
    detail = " ".join(errors)
    raise MeshError("Keine Balkenkanten (SEG2/SEG3) in der MED-Datei. {}".format(detail).strip())


def _edges_from_med(ml, path, name):
    filemesh = ml.ReadMeshFromFile(path, name, 0)
    dim = int(filemesh.getMeshDimension())
    level = 1 - dim
    umesh = filemesh.getMeshAtLevel(level) if hasattr(filemesh, "getMeshAtLevel") else filemesh
    if umesh is None:
        return []
    try:
        from MEDCoupling import NORM_SEG2, NORM_SEG3
    except Exception:
        NORM_SEG2, NORM_SEG3 = None, None
    coords = _numpy(umesh.getCoords())
    membership = {}
    if hasattr(filemesh, "getGroupsNames"):
        for gname in list(filemesh.getGroupsNames()):
            try:
                arr = filemesh.getGroupArr(level, gname)
            except Exception:
                continue
            ids = _numpy(arr)
            for index in ids:
                membership.setdefault(int(index), []).append(str(gname))
    edges = []
    ncells = int(umesh.getNumberOfCells())
    for index in range(ncells):
        ctype = umesh.getTypeOfCell(index)
        label = str(ctype)
        is_seg2 = (NORM_SEG2 is not None and ctype == NORM_SEG2) or "SEG2" in label
        is_seg3 = (NORM_SEG3 is not None and ctype == NORM_SEG3) or "SEG3" in label
        if not is_seg2 and not is_seg3:
            continue
        nodes = list(umesh.getNodeIdsOfCell(index))
        if len(nodes) < 2:
            continue
        p1 = tuple(float(v) for v in coords[nodes[0]][:3])
        p2 = tuple(float(v) for v in coords[nodes[1]][:3])
        edges.append(Edge(str(index + 1), p1, p2, tuple(membership.get(index, ()))))
    return edges


def edges_from_smesh(mesh):
    """Kanten eines geladenen SMESH-Netzes, Gruppen über GetGroups."""
    try:
        import SMESH
    except ImportError as exc:
        raise MeshError("SMESH ist nicht importierbar ({}).".format(exc)) from exc
    membership = {}
    for group in mesh.GetGroups():
        try:
            if group.GetType() != SMESH.EDGE:
                continue
            gname = group.GetName()
            for eid in group.GetIDs():
                membership.setdefault(int(eid), []).append(gname)
        except Exception:
            continue
    edges = []
    for eid in mesh.GetElementsByType(SMESH.EDGE):
        nodes = list(mesh.GetElemNodes(eid))
        if len(nodes) < 2:
            continue
        p1 = tuple(mesh.GetNodeXYZ(nodes[0]))
        p2 = tuple(mesh.GetNodeXYZ(nodes[1]))
        edges.append(Edge(str(eid), p1, p2, tuple(membership.get(int(eid), ()))))
    if not edges:
        raise MeshError("Das SMESH-Netz enthält keine Kanten.")
    return edges
