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


def _as_points(raw):
    arr = _numpy(raw)
    shape = getattr(arr, "shape", None)
    try:
        if shape is not None and len(shape) == 2 and shape[1] >= 3:
            return [(float(arr[i][0]), float(arr[i][1]), float(arr[i][2])) for i in range(int(shape[0]))]
        if shape is not None and len(shape) == 1 and int(shape[0]) % 3 == 0:
            count = int(shape[0]) // 3
            return [
                (float(arr[3 * i]), float(arr[3 * i + 1]), float(arr[3 * i + 2])) for i in range(count)
            ]
    except Exception:
        pass
    if hasattr(raw, "getNumberOfTuples") and hasattr(raw, "getIJ"):
        count = int(raw.getNumberOfTuples())
        return [
            (float(raw.getIJ(i, 0)), float(raw.getIJ(i, 1)), float(raw.getIJ(i, 2))) for i in range(count)
        ]
    raise MeshError("Koordinaten der MED-Datei sind nicht lesbar.")


def _flat_ints(raw):
    arr = _numpy(raw)
    try:
        return [int(value) for value in list(arr)]
    except TypeError:
        if hasattr(raw, "getIJ"):
            count = int(raw.getNumberOfTuples())
            return [int(raw.getIJ(i, 0)) for i in range(count)]
        raise


# INTERP_KERNEL.NormalizedCellType, unverändert seit MEDCoupling 6.
SEG2_TYPE = 1
SEG3_TYPE = 2


def segments_from_connectivity(coords, conn, cindex, groups_by_cell=None, names=None, seg_types=None):
    """SEG2/SEG3 aus der MEDCoupling-Konnektivität.

    conn enthält je Zelle den Typ und danach die Knotenindizes.
    cindex markiert den Anfang jeder Zelle und hat die Länge Zellenzahl + 1.
    Bei SEG3 werden die beiden am weitesten auseinanderliegenden Knoten
    die Stabenden, unabhängig davon, ob der Mittelknoten an zweiter oder
    dritter Stelle steht.
    """
    groups_by_cell = groups_by_cell or {}
    if seg_types is None:
        seg_types = {SEG2_TYPE, SEG3_TYPE}
    edges = []
    if not cindex or len(cindex) < 2:
        return edges
    for cell in range(len(cindex) - 1):
        start = int(cindex[cell])
        stop = int(cindex[cell + 1])
        chunk = [int(value) for value in conn[start:stop]]
        if len(chunk) < 3:
            continue
        ctype = chunk[0]
        nodes = chunk[1:]
        if ctype not in seg_types or len(nodes) < 2:
            continue
        if any(node < 0 or node >= len(coords) for node in nodes[:3]):
            continue
        if len(nodes) >= 3:
            candidates = ((nodes[0], nodes[1]), (nodes[0], nodes[2]), (nodes[1], nodes[2]))

            def span(pair):
                a = coords[pair[0]]
                b = coords[pair[1]]
                return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2

            n1, n2 = max(candidates, key=span)
        else:
            n1, n2 = nodes[0], nodes[1]
        if names is not None and cell < len(names) and names[cell] not in (None, ""):
            name = str(names[cell])
        else:
            name = str(cell + 1)
        groups = tuple(groups_by_cell.get(cell, ()))
        edges.append(Edge(name, coords[n1], coords[n2], groups))
    return edges


def _segment_type_codes():
    codes = {SEG2_TYPE, SEG3_TYPE}
    for module_name in ("MEDCoupling", "medcoupling"):
        try:
            module = __import__(module_name)
        except Exception:
            continue
        for label, fallback in (("NORM_SEG2", SEG2_TYPE), ("NORM_SEG3", SEG3_TYPE)):
            value = getattr(module, label, None)
            if value is not None:
                try:
                    codes.add(int(value))
                except (TypeError, ValueError):
                    pass
    return codes


def _groups_on_level(med_file, level):
    membership = {}
    getter = getattr(med_file, "getGroupsOnSpecifiedLev", None)
    if getter is None:
        getter = getattr(med_file, "getGroupsNames", None)
        if getter is None:
            return membership
        try:
            names = list(getter())
        except Exception:
            return membership
    else:
        try:
            names = list(getter(level))
        except Exception:
            return membership
    for gname in names:
        try:
            arr = med_file.getGroupArr(level, gname)
        except Exception:
            continue
        for index in _flat_ints(arr):
            membership.setdefault(int(index), []).append(str(gname).strip())
    return membership


def _names_on_level(med_file, umesh, level, count):
    for owner, method in (
        (med_file, "getGlobalNumFieldAtLevel"),
        (umesh, "getGlobalNumField"),
    ):
        fn = getattr(owner, method, None)
        if fn is None:
            continue
        try:
            raw = fn(level) if method.endswith("AtLevel") else fn()
            values = _flat_ints(raw)
        except Exception:
            continue
        if len(values) >= count:
            return [str(int(value)) for value in values[:count]]
    return None


def _edges_of_umesh(umesh, membership, names=None):
    coords = _as_points(umesh.getCoords())
    codes = _segment_type_codes()
    conn_fn = getattr(umesh, "getNodalConnectivity", None)
    index_fn = getattr(umesh, "getNodalConnectivityIndex", None)
    if conn_fn is not None and index_fn is not None:
        try:
            return segments_from_connectivity(
                coords,
                _flat_ints(conn_fn()),
                _flat_ints(index_fn()),
                membership,
                names,
                codes,
            )
        except MeshError:
            raise
        except Exception:
            pass
    edges = []
    ncells = int(umesh.getNumberOfCells())
    for index in range(ncells):
        try:
            ctype = int(umesh.getTypeOfCell(index))
        except Exception:
            continue
        if ctype not in codes:
            continue
        try:
            nodes = [int(node) for node in list(umesh.getNodeIdsOfCell(index))]
        except Exception:
            continue
        fake_conn = [ctype] + nodes
        found = segments_from_connectivity(
            coords,
            fake_conn,
            [0, len(fake_conn)],
            {0: membership.get(index, ())},
            [names[index]] if names is not None and index < len(names) else [str(index + 1)],
            codes,
        )
        edges.extend(found)
    return edges


def _levels_of(med_file):
    fn = getattr(med_file, "getNonEmptyLevels", None)
    if fn is None:
        return [0]
    try:
        return list(fn())
    except Exception:
        return [0]


def _open_med_file(ml, path, name):
    errors = []
    for call in (
        lambda: ml.MEDFileUMesh(path, name),
        lambda: ml.MEDFileUMesh.New(path, name),
    ):
        try:
            opened = call()
        except Exception as exc:
            errors.append(str(exc))
            continue
        if opened is not None:
            return opened, errors
    return None, errors


def _edges_from_med(ml, path, name):
    med_file, errors = _open_med_file(ml, path, name)
    if med_file is not None:
        found = []
        for level in _levels_of(med_file):
            try:
                umesh = med_file.getMeshAtLevel(level)
            except Exception as exc:
                errors.append("Ebene {}: {}".format(level, exc))
                continue
            if umesh is None:
                continue
            try:
                if int(umesh.getNumberOfCells()) <= 0:
                    continue
                membership = _groups_on_level(med_file, level)
                names = _names_on_level(med_file, umesh, level, int(umesh.getNumberOfCells()))
                found.extend(_edges_of_umesh(umesh, membership, names))
            except MeshError:
                raise
            except Exception as exc:
                errors.append("Ebene {}: {}".format(level, exc))
        if found:
            return found
        if errors:
            raise MeshError("MED-Netz '{}': {}".format(name, "; ".join(errors[:4])))
        return []

    codes_note = []
    for rel in (0, -1, -2, -3):
        try:
            umesh = ml.ReadUMeshFromFile(path, name, rel)
        except Exception as exc:
            codes_note.append(str(exc))
            continue
        if umesh is None:
            continue
        try:
            if int(umesh.getNumberOfCells()) <= 0:
                continue
            found = _edges_of_umesh(umesh, {}, None)
        except Exception as exc:
            codes_note.append(str(exc))
            continue
        if found:
            return found
    detail = "; ".join((errors + codes_note)[:4])
    if detail:
        raise MeshError("MED-Netz '{}': {}".format(name, detail))
    return []


def read_med(path):
    """Liest SEG2/SEG3 über MEDLoader, auf allen nicht leeren Ebenen.

    Ein reines Balkennetz hat die Zelldimension 1. Liegen die Balken in
    einer Datei unter einem Volumen- oder Flächennetz, stehen sie auf einer
    tieferen relativen Ebene. Es wird nicht nur die höchste Dimension gelesen.
    """
    try:
        import MEDLoader as ml
    except ImportError as exc:
        raise MeshError(
            "MEDLoader ist nicht verfügbar ({}). MED-Dateien liest das Plugin nur innerhalb von SALOME.".format(
                exc
            )
        ) from exc
    try:
        names = list(ml.GetMeshNames(path))
    except Exception as exc:
        raise MeshError("MED-Datei nicht lesbar: {}".format(exc)) from exc
    if not names:
        raise MeshError("Die MED-Datei enthält kein Netz.")
    errors = []
    found = []
    for name in names:
        try:
            found.extend(_edges_from_med(ml, path, name))
        except MeshError as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append("{}: {}".format(name, exc))
    if found:
        return found
    detail = " ".join(errors)
    raise MeshError("Keine Balkenkanten (SEG2/SEG3) in der MED-Datei. {}".format(detail).strip())


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
