"""Prüft Rahmen, Parser und mail ohne SALOME."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from beamcheck.aster_access import _live_gui, read_case
from beamcheck.control import needed_groups, rank_meshes
from beamcheck.geomview import _extrude
from beamcheck.toolbar import select_toolbar
from beamcheck.smeshview import choose_roots, is_control_name
from beamcheck.mesh_io import (
    SEG2_TYPE,
    SEG3_TYPE,
    edge_membership,
    read_mail,
    segments_from_connectivity,
)
from beamcheck.surface import cap_triangles, extrude_shell
from beamcheck.orientation import Orientation, beam_axis, local_frame
from beamcheck.parser import parse_comm
from beamcheck.report import build_report
from beamcheck.sections import circle_profile, ellipse_semiaxes, general_profile, rectangle_profile

_HERE = os.path.dirname(os.path.abspath(__file__))
_BEISPIEL = os.path.join(os.path.dirname(_HERE), "beispiele")


def _close(a, b, tol=1e-9):
    return all(abs(a[i] - b[i]) < tol for i in range(3))


class OrientationTests(unittest.TestCase):
    def test_beam_along_x_default(self):
        ex, length = beam_axis((0, 0, 0), (2, 0, 0))
        self.assertAlmostEqual(length, 2.0)
        ey, ez, warnings = local_frame(ex, Orientation("DEFAULT"))
        self.assertEqual(warnings, [])
        self.assertTrue(_close(ey, (0, 1, 0)))
        self.assertTrue(_close(ez, (0, 0, 1)))

    def test_beam_along_y_default(self):
        ex, _ = beam_axis((0, 0, 0), (0, 3, 0))
        ey, ez, _ = local_frame(ex, Orientation("DEFAULT"))
        self.assertTrue(_close(ey, (-1, 0, 0)))
        self.assertTrue(_close(ez, (0, 0, 1)))

    def test_beam_along_z_default(self):
        ex, _ = beam_axis((0, 0, 0), (0, 0, 4))
        ey, ez, warnings = local_frame(ex, Orientation("DEFAULT"))
        self.assertTrue(any("global Z axis" in w for w in warnings))
        self.assertTrue(_close(ey, (0, 1, 0)))
        self.assertTrue(_close(ez, (-1, 0, 0)))

    def test_angl_vril_90(self):
        ex, _ = beam_axis((0, 0, 0), (1, 0, 0))
        ey, ez, _ = local_frame(ex, Orientation("ANGL_VRIL", angle=90))
        self.assertTrue(_close(ey, (0, 0, 1)))
        self.assertTrue(_close(ez, (0, -1, 0)))

    def test_vect_y_global_z(self):
        ex, _ = beam_axis((0, 0, 0), (1, 0, 0))
        ey, ez, warnings = local_frame(ex, Orientation("VECT_Y", vector=(0, 0, 1)))
        self.assertEqual(warnings, [])
        self.assertTrue(_close(ey, (0, 0, 1)))
        self.assertTrue(_close(ez, (0, -1, 0)))

    def test_vect_z_global_z(self):
        ex, _ = beam_axis((0, 0, 0), (1, 0, 0))
        ey, ez, _ = local_frame(ex, Orientation("VECT_Z", vector=(0, 0, 1)))
        self.assertTrue(_close(ez, (0, 0, 1)))
        self.assertTrue(_close(ey, (0, 1, 0)))

    def test_parallel_vector_falls_back(self):
        ex, _ = beam_axis((0, 0, 0), (1, 0, 0))
        _ey, _ez, warnings = local_frame(ex, Orientation("VECT_Y", vector=(4, 0, 0)))
        self.assertTrue(any("parallel to the beam" in w for w in warnings))
        self.assertTrue(_close(_ey, (0, 1, 0)))


class SectionTests(unittest.TestCase):
    def test_hollow_rectangle_area(self):
        profile = rectangle_profile(0.16, 0.32, 0.012, 0.012)
        self.assertAlmostEqual(profile.area, 0.16 * 0.32 - 0.136 * 0.296)
        self.assertEqual(len(profile.holes), 1)
        self.assertEqual(len(profile.outer), 4)

    def test_tube_area(self):
        profile = circle_profile(0.06, 0.005)
        self.assertAlmostEqual(profile.area, 3.141592653589793 * (0.06**2 - 0.055**2))
        self.assertEqual(len(profile.holes), 1)

    def test_solid_when_ep_equals_r(self):
        profile = circle_profile(0.05, 0.05)
        self.assertEqual(profile.holes, [])


class BeispielTests(unittest.TestCase):
    def test_rahmen(self):
        with open(os.path.join(_BEISPIEL, "rahmen.comm"), encoding="utf-8") as handle:
            parsed = parse_comm(handle.read())
        with open(os.path.join(_BEISPIEL, "rahmen.mail"), encoding="utf-8") as handle:
            edges = read_mail(handle.read())
        self.assertEqual(parsed.mesh_unite, 20)
        self.assertEqual(parsed.mesh_format, "ASTER")
        self.assertEqual(len(edges), 9)
        report = build_report(parsed, edges)
        self.assertEqual(len(report.beams), 9)
        self.assertEqual(report.skipped, 0)
        by_name = {beam.name: beam for beam in report.beams}

        column = by_name["SAB"]
        self.assertTrue(_close(column.ex, (0, 0, 1)))
        self.assertTrue(_close(column.ey, (1, 0, 0)))
        self.assertTrue(_close(column.ez, (0, 1, 0)))
        self.assertEqual(column.profile.kind, "RECTANGLE")
        self.assertFalse(column.warnings)

        beam = by_name["SBC"]
        self.assertTrue(_close(beam.ey, (0, 1, 0)))
        self.assertTrue(_close(beam.ez, (0, 0, 1)))
        self.assertIn("ANGL_VRIL", beam.orientation_label)

        traverse = by_name["SBF"]
        self.assertTrue(_close(traverse.ey, (-1, 0, 0)))
        self.assertTrue(_close(traverse.ez, (0, 0, 1)))
        self.assertEqual(len(traverse.profile.holes), 1)

        brace = by_name["SBG"]
        self.assertEqual(brace.profile.kind, "CERCLE")
        self.assertAlmostEqual(brace.ex[2], 0.0, places=9)
        self.assertAlmostEqual(brace.ez[2], 1.0, places=9)

    def test_surcharge_and_shell_skipped(self):
        text = """
DEBUT()
MAIL = LIRE_MAILLAGE(UNITE=20, FORMAT='MED')
MODELE = AFFE_MODELE(MAILLAGE=MAIL, AFFE=(
    _F(GROUP_MA='POUTRE', PHENOMENE='MECANIQUE', MODELISATION='POU_D_E'),
    _F(GROUP_MA='COQUE', PHENOMENE='MECANIQUE', MODELISATION='DKT'),
))
AFFE_CARA_ELEM(
    MODELE=MODELE,
    POUTRE=(
        _F(GROUP_MA='POUTRE', SECTION='CERCLE', CARA='R', VALE=0.05),
        _F(GROUP_MA='POUTRE', SECTION='RECTANGLE', CARA=('HY','HZ'), VALE=(0.2, 0.1)),
    ),
    ORIENTATION=_F(GROUP_MA='POUTRE', CARA='VECT_Y', VALE=(0.0, 0.0, 1.0)),
)
FIN()
"""
        parsed = parse_comm(text)
        edges = [
            type("E", (), {})(),
        ]
        from beamcheck.mesh_io import Edge

        edges = [
            Edge("1", (0, 0, 0), (1, 0, 0), ("POUTRE",)),
            Edge("2", (0, 0, 0), (0, 1, 0), ("COQUE",)),
        ]
        report = build_report(parsed, edges)
        self.assertEqual(len(report.beams), 1)
        self.assertEqual(report.beams[0].profile.kind, "RECTANGLE")
        self.assertTrue(any("VECT_Y" in report.beams[0].orientation_label for _ in [0]))
        ey = report.beams[0].ey
        self.assertTrue(_close(ey, (0, 0, 1)))

    def test_fortran_float_mail(self):
        text = """
COOR_3D
N1 0.0D+00 1.0D+00 2.5D+00
N2 1.0D+00 1.0D+00 2.5D+00
FINSF
SEG2
M1 N1 N2
FINSF
GROUP_MA
P
M1
FINSF
FIN
"""
        edges = read_mail(text)
        self.assertEqual(len(edges), 1)
        self.assertAlmostEqual(edges[0].p1[1], 1.0)
        self.assertEqual(edges[0].groups, ("P",))


class _Recorder:
    def __init__(self, prism):
        self.prism = prism
        self.calls = []

    def MakeVertex(self, *point):
        self.calls.append(("vertex", point))
        return ("vertex", point)

    def MakeVector(self, p1, p2):
        self.calls.append(("vector", p1, p2))
        return ("vector", p1, p2)

    def MakeVectorDXDYDZ(self, *comps):
        self.calls.append(("dxdydz", comps))
        return ("dxdydz", comps)


class ExtrudeTests(unittest.TestCase):
    def test_salome9_two_points(self):
        class Geom(_Recorder):
            def MakePrism(self, base, p1, p2):
                self.calls.append(("prism", base, p1, p2))
                return self.prism

        geom = Geom("solid")
        self.assertEqual(_extrude(geom, "face", (0, 0, 0), (1, 0, 0), 2.0), "solid")
        self.assertEqual(geom.calls[-1][0], "prism")
        self.assertEqual(geom.calls[-1][2], ("vertex", (0, 0, 0)))
        self.assertEqual(geom.calls[-1][3], ("vertex", (2.0, 0, 0)))

    def test_legacy_vector(self):
        class Geom(_Recorder):
            def MakePrism(self, base, vector):
                self.calls.append(("prism2", base, vector))
                return self.prism

        geom = Geom("solid")
        self.assertEqual(_extrude(geom, "face", (0, 0, 1), (0, 0, 1), 3.0), "solid")
        self.assertEqual(geom.calls[-1][0], "prism2")


def _tri_area(triangle):
    a, b, c = triangle
    return abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) * 0.5


class MedAndShellTests(unittest.TestCase):
    def test_connectivity_skips_faces_and_keeps_group(self):
        coords = [(0, 0, 0), (2, 0, 0), (0, 1, 0), (1, 0, 0)]
        # SEG2 (Typ 1, Knoten 0-1), danach TRI3 (Typ 3).
        conn = [SEG2_TYPE, 0, 1, 3, 0, 2, 3]
        cindex = [0, 3, 7]
        edges = segments_from_connectivity(coords, conn, cindex, {0: ["RIEGEL"]})
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].name, "1")
        self.assertEqual(edges[0].groups, ("RIEGEL",))
        self.assertEqual(edges[0].p2, (2, 0, 0))

    def test_seg3_uses_the_far_ends(self):
        coords = [(0, 0, 0), (1, 0, 0), (0.5, 0, 0)]
        conn = [SEG3_TYPE, 0, 2, 1]
        edges = segments_from_connectivity(coords, conn, [0, 4], names=["M7"])
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].name, "M7")
        self.assertEqual({edges[0].p1, edges[0].p2}, {(0, 0, 0), (1, 0, 0)})

    def test_solid_rectangle_shell(self):
        outer = [(-0.15, -0.225), (0.15, -0.225), (0.15, 0.225), (-0.15, 0.225)]
        shell = extrude_shell((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), 2.0, outer, [])
        self.assertEqual(len(shell), 12)

    def test_hollow_cap_keeps_the_opening(self):
        outer = [(-0.15, -0.2), (0.15, -0.2), (0.15, 0.2), (-0.15, 0.2)]
        hole = [(-0.1, -0.12), (0.1, -0.12), (0.1, 0.12), (-0.1, 0.12)]
        caps = cap_triangles(outer, [list(reversed(hole))])
        self.assertEqual(len(caps), 8)
        area = sum(_tri_area(triangle) for triangle in caps)
        self.assertAlmostEqual(area, 0.30 * 0.40 - 0.20 * 0.24, places=6)


class _Info:
    def __init__(self, filename):
        self.filename = filename


class AsterCaseTests(unittest.TestCase):
    def test_reads_current_case_and_unit_file(self):
        class Stage:
            handle2info = {20: _Info("rahmen.med")}

            def get_text(self):
                return "DEBUT()\nLIRE_MAILLAGE(UNITE=20)\nFIN()\n"

        class Case:
            stages = [Stage()]

        class History:
            current_case = Case()
            folder = _BEISPIEL

        class Study:
            history = History()

        class Gui:
            def study(self):
                return Study()

        payload = read_case(Gui())
        self.assertIn("LIRE_MAILLAGE", payload["text"])
        self.assertEqual(payload["files"][0][0], 20)
        self.assertTrue(payload["files"][0][1].endswith("rahmen.med"))

    def test_live_gui_does_not_construct_a_second_one(self):
        constructed = []

        def get_aster_gui():
            constructed.append(1)
            return object()

        class Module:
            pass

        module = Module()
        module.get_aster_gui = get_aster_gui
        self.assertIsNone(_live_gui([module]))
        self.assertEqual(constructed, [])
        get_aster_gui.aster_gui = "sentinel"

        class Study:
            pass

        class Gui:
            def study(self):
                return Study()

        def getter():
            return Gui()

        getter.aster_gui = Gui()
        module.get_aster_gui = getter
        self.assertIsInstance(_live_gui([module]), Gui)


class ClearSelectionTests(unittest.TestCase):
    def test_removes_mesh_that_only_holds_control_groups(self):
        nodes = [
            ("0:1:2", "Balkenkontrolle_X", "0:1:8", False, ["Balkenkontrolle_X", "Balkenkontrolle_Y"]),
            ("0:1:3", "Balkenkontrolle_Y", "0:1:8", False, ["Balkenkontrolle_X", "Balkenkontrolle_Y"]),
        ]
        self.assertEqual(choose_roots(nodes), ["0:1:8"])

    def test_keeps_a_foreign_mesh_and_drops_only_the_group(self):
        nodes = [
            ("0:1:4", "Balkenkontrolle_X", "0:1:9", False, ["Balkenkontrolle_X", "Wand"]),
        ]
        self.assertEqual(choose_roots(nodes), ["0:1:4"])
        self.assertTrue(is_control_name("Balkenkontrolle"))
        self.assertFalse(is_control_name("Mesh_1"))


class _Group:
    def __init__(self, name):
        self._name = name

    def GetName(self):
        return self._name


class _Mesh:
    def __init__(self, names):
        self._groups = [_Group(name) for name in names]

    def GetGroups(self):
        return self._groups


class ToolbarChoiceTests(unittest.TestCase):
    def test_prefers_the_commands_toolbar(self):
        ops = object()
        cmds = object()
        chosen = select_toolbar(
            [("OperationsToolbar", 2, ops), ("CommandsToolbar", 2, cmds)]
        )
        self.assertIs(chosen, cmds)

    def test_ranks_the_mesh_that_holds_the_beam_group(self):
        class Parsed:
            beam_groups = {"POUTRE"}
            sections = []
            orientations = []

        other = _Mesh(["Last"])
        beams = _Mesh(["POUTRE", "Lager"])
        ranked = rank_meshes(
            [("Volumen", other), ("Rahmen", beams), ("Balkenkontrolle", _Mesh(["X"]))],
            needed_groups(Parsed()),
        )
        self.assertEqual(ranked[0][0], "Rahmen")
        self.assertEqual(ranked[0][2], 1)
        self.assertTrue(all(name != "Balkenkontrolle" for name, _mesh, _score in ranked))


class GroupMembershipTests(unittest.TestCase):
    def test_keeps_edge_ids_when_the_enum_does_not_match(self):
        # Typ 3 wäre eine Fläche, die Nummern sind aber Kanten.
        membership = edge_membership(
            [("topbeam", 3, [1, 2]), ("vertb", 2, [2]), ("Knoten", 1, [9])],
            [1, 2],
            2,
        )
        self.assertEqual(membership[1], ["topbeam"])
        self.assertEqual(membership[2], ["topbeam", "vertb"])
        self.assertNotIn(9, membership)


class EllipseTests(unittest.TestCase):
    def test_solid_ellipse_reproduces_iy_and_iz(self):
        iy = 1.2e-4
        iz = 3.4e-5
        profile = general_profile(iy, iz)
        self.assertEqual(profile.holes, [])
        self.assertGreater(len(profile.outer), 8)
        self.assertAlmostEqual(profile.iy, iy, delta=iy * 1e-9)
        self.assertAlmostEqual(profile.iz, iz, delta=iz * 1e-9)
        a, b = ellipse_semiaxes(iy, iz)
        self.assertAlmostEqual(max(p[0] for p in profile.outer), a, places=6)
        self.assertAlmostEqual(max(p[1] for p in profile.outer), b, places=6)

    def test_equal_inertias_are_a_circle(self):
        a, b = ellipse_semiaxes(2.5e-3, 2.5e-3)
        self.assertAlmostEqual(a, b, places=9)


if __name__ == "__main__":
    unittest.main()
