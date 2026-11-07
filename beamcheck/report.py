"""Ordnet Netz-Kanten den POUTRE- und ORIENTATION-Faktoren zu."""

from __future__ import annotations

from dataclasses import dataclass, field

from beamcheck.orientation import Orientation, beam_axis, local_frame
from beamcheck.parser import resolve_assignments
from beamcheck.sections import profile_from_cara


@dataclass
class Beam:
    name: str
    groups: tuple
    section_group: str
    p1: tuple
    p2: tuple
    length: float
    ex: tuple
    ey: tuple
    ez: tuple
    profile: object
    orientation_label: str
    warnings: list = field(default_factory=list)


@dataclass
class Report:
    beams: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    skipped: int = 0

    def summary(self):
        lines = ["{} Balken zur Kontrolle.".format(len(self.beams))]
        alarmed = [b for b in self.beams if b.warnings]
        if alarmed:
            lines.append("{} davon mit Hinweis.".format(len(alarmed)))
        if self.skipped:
            lines.append("{} Kanten übersprungen (keine Balkenmodellierung, kein POUTRE).".format(self.skipped))
        lines.extend(self.warnings)
        for beam in self.beams:
            for note in beam.warnings:
                lines.append("{}: {}".format(beam.name, note))
        return "\n".join(lines)


def _is_candidate(edge, parsed):
    if parsed.all_edges_are_beams:
        return True
    if any(g in parsed.beam_groups for g in edge.groups):
        return True
    if resolve_assignments(parsed.sections, edge.groups, edge.name):
        return True
    return False


def build_report(parsed, edges):
    report = Report(warnings=list(parsed.warnings))
    known_groups = set()
    for edge in edges:
        for group in edge.groups:
            known_groups.add(group)
    for target in list(parsed.sections) + list(parsed.orientations):
        if target.tout:
            continue
        for group in target.groups:
            if group and group not in known_groups:
                report.warnings.append("Gruppe '{}' kommt im Netz nicht vor.".format(group))

    for edge in edges:
        section_target = resolve_assignments(parsed.sections, edge.groups, edge.name)
        orient_target = resolve_assignments(parsed.orientations, edge.groups, edge.name)
        if not _is_candidate(edge, parsed) and section_target is None:
            report.skipped += 1
            continue
        ex, length = beam_axis(edge.p1, edge.p2)
        if ex is None:
            report.warnings.append("{} hat keine Länge und wird übersprungen.".format(edge.name))
            report.skipped += 1
            continue
        warnings = []
        if section_target is None:
            profile = profile_from_cara("GENERALE", {})
            profile.warnings = ["Keine POUTRE-Zuordnung. Nur die lokalen Achsen werden gezeigt."]
            section_group = edge.groups[0] if edge.groups else "OHNE_GRUPPE"
        else:
            payload = section_target.payload
            profile = profile_from_cara(payload["section"], payload["values"])
            if section_target.tout:
                section_group = edge.groups[0] if edge.groups else "TOUT"
            elif section_target.groups:
                hit = [g for g in edge.groups if g in section_target.groups]
                section_group = hit[-1] if hit else section_target.groups[-1]
            else:
                section_group = edge.name
        warnings.extend(profile.warnings)

        if orient_target is None:
            orient = Orientation("DEFAULT")
            label = "Standard (ANGL_VRIL = 0)"
        else:
            cara = orient_target.payload["cara"]
            values = orient_target.payload["values"]
            raw = values.get(cara)
            if cara == "ANGL_VRIL":
                if isinstance(raw, (list, tuple)):
                    angle = float(raw[0]) if raw else 0.0
                elif isinstance(raw, (int, float)):
                    angle = float(raw)
                elif values:
                    angle = float(next(iter(values.values())))
                else:
                    angle = 0.0
                orient = Orientation("ANGL_VRIL", angle=angle)
                label = "ANGL_VRIL = {:.4g}°".format(angle)
            elif cara in ("VECT_Y", "VECT_Z", "VECT_MAIL_Y", "VECT_MAIL_Z"):
                if isinstance(raw, (list, tuple)):
                    nums = [float(v) for v in raw]
                else:
                    nums = []
                    for val in values.values():
                        if isinstance(val, (int, float)):
                            nums.append(float(val))
                if len(nums) < 3:
                    orient = Orientation(cara, vector=None)
                    label = cara + " (unvollständig)"
                else:
                    orient = Orientation(cara, vector=tuple(nums[:3]))
                    label = "{} = ({:.4g}, {:.4g}, {:.4g})".format(cara, nums[0], nums[1], nums[2])
            else:
                orient = Orientation(cara)
                label = cara
        ey, ez, owarnings = local_frame(ex, orient)
        warnings.extend(owarnings)
        report.beams.append(
            Beam(
                name=edge.name,
                groups=edge.groups,
                section_group=section_group,
                p1=edge.p1,
                p2=edge.p2,
                length=length,
                ex=ex,
                ey=ey,
                ez=ez,
                profile=profile,
                orientation_label=label,
                warnings=warnings,
            )
        )
    # Doppelte Gruppen-Hinweise entfernen, Reihenfolge halten.
    seen = set()
    unique = []
    for note in report.warnings:
        if note not in seen:
            seen.add(note)
            unique.append(note)
    report.warnings = unique
    return report
