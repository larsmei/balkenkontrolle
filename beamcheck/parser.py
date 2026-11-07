"""Liest eine Code_Aster-comm (Python-Syntax) nur so weit, wie die Kontrolle braucht.

Ausgewertet wird in einer abgeschotteten Umgebung: keine Dateizugriffe, Importe
nur von math. INCLUDE wird nicht expandiert.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


class CommError(Exception):
    pass


class Factor(dict):
    """Abbildung von _F(...)."""


@dataclass
class Cmd:
    name: str
    kwargs: dict


@dataclass
class Target:
    """Wohin ein POUTRE- oder ORIENTATION-Faktor wirkt."""

    groups: tuple
    mailles: tuple
    tout: bool
    payload: dict


@dataclass
class ParsedComm:
    sections: list = field(default_factory=list)
    orientations: list = field(default_factory=list)
    beam_groups: set = field(default_factory=set)
    all_edges_are_beams: bool = False
    has_model: bool = False
    mesh_unite: int | None = None
    mesh_format: str | None = None
    warnings: list = field(default_factory=list)


_BEAM_PREFIXES = ("POU_", "TUYAU")
_SAFE_BUILTINS = {
    "abs": abs,
    "min": min,
    "max": max,
    "float": float,
    "int": int,
    "str": str,
    "bool": bool,
    "list": list,
    "tuple": tuple,
    "dict": dict,
    "set": set,
    "range": range,
    "len": len,
    "sum": sum,
    "round": round,
    "pow": pow,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "sorted": sorted,
    "reversed": reversed,
    "print": lambda *a, **k: None,
    "True": True,
    "False": False,
    "None": None,
}


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name == "math":
        return math
    raise ImportError("Import of '{}' is blocked in the beam check.".format(name))


def _as_factors(value):
    if isinstance(value, Factor):
        return [value]
    if isinstance(value, (list, tuple)):
        found = []
        for item in value:
            found.extend(_as_factors(item))
        return found
    return []


def _names(value):
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(v) for v in value)
    return (str(value),)


def _cara_values(factor):
    cara = factor.get("CARA")
    vale = factor.get("VALE")
    if cara is None or vale is None:
        return {}, []
    keys = [cara] if isinstance(cara, str) else [str(k) for k in cara]
    if isinstance(vale, bool):
        return {}, ["VALE is not a number."]
    if isinstance(vale, (int, float)):
        vals = [float(vale)]
    elif isinstance(vale, (list, tuple)):
        try:
            vals = [float(v) for v in vale]
        except (TypeError, ValueError):
            return {}, ["VALE contains a non-numeric value."]
    else:
        return {}, ["VALE has an unknown type."]
    if len(keys) == 1 and len(vals) > 1:
        # VECT_Y = (x, y, z): ein Name, drei Komponenten.
        return {keys[0]: vals}, []
    if len(vals) != len(keys):
        note = "CARA ({}) and VALE ({}) have different lengths.".format(len(keys), len(vals))
        n = min(len(keys), len(vals))
        return dict(zip(keys[:n], vals[:n])), [note]
    return dict(zip(keys, vals)), []


def _target(factor, payload):
    tout = str(factor.get("TOUT", "")).upper() == "OUI"
    return Target(
        groups=_names(factor.get("GROUP_MA")),
        mailles=_names(factor.get("MAILLE")),
        tout=tout,
        payload=payload,
    )


def _is_beam_model(name):
    upper = str(name).upper()
    return upper.startswith(_BEAM_PREFIXES)


def parse_comm(text):
    if text.startswith("\ufeff"):
        text = text[1:]
    calls = []

    def make(name):
        def caller(*args, **kwargs):
            if args:
                raise TypeError("{} expects keywords.".format(name))
            cmd = Cmd(name, kwargs)
            calls.append(cmd)
            return cmd

        return caller

    class NS(dict):
        def __missing__(self, key):
            if key.startswith("__"):
                raise KeyError(key)
            fn = make(key)
            self[key] = fn
            return fn

    ns = NS()
    builtins = dict(_SAFE_BUILTINS)
    builtins["__import__"] = _safe_import
    ns["__builtins__"] = builtins
    ns["_F"] = lambda **kw: Factor(kw)
    ns["math"] = math
    ns["pi"] = math.pi

    try:
        exec(compile(text, "<comm>", "exec"), ns)
    except Exception as exc:
        raise CommError("The command file could not be read: {}".format(exc)) from exc

    parsed = ParsedComm()
    mesh_cmds = [c for c in calls if c.name == "LIRE_MAILLAGE"]
    model_cmds = [c for c in calls if c.name == "AFFE_MODELE"]
    cara_cmds = [c for c in calls if c.name == "AFFE_CARA_ELEM"]
    if any(c.name == "INCLUDE" for c in calls):
        parsed.warnings.append("INCLUDE is not expanded. Use the resolved command file.")

    parsed.has_model = bool(model_cmds)
    beam_groups = set()
    all_beams = False
    for model in model_cmds:
        mail = model.kwargs.get("MAILLAGE")
        if isinstance(mail, Cmd) and mail.name == "LIRE_MAILLAGE":
            unite = mail.kwargs.get("UNITE")
            if unite is not None:
                try:
                    parsed.mesh_unite = int(unite)
                except (TypeError, ValueError):
                    parsed.warnings.append("UNITE of LIRE_MAILLAGE is not a number.")
            fmt = mail.kwargs.get("FORMAT")
            if fmt:
                parsed.mesh_format = str(fmt).upper()
        for factor in _as_factors(model.kwargs.get("AFFE")):
            models = factor.get("MODELISATION")
            names = [models] if isinstance(models, str) else list(models or [])
            beamish = [m for m in names if _is_beam_model(m)]
            if not beamish:
                continue
            if str(factor.get("TOUT", "")).upper() == "OUI":
                all_beams = True
            for group in _names(factor.get("GROUP_MA")):
                beam_groups.add(group)
    if model_cmds and parsed.mesh_unite is None and mesh_cmds:
        unite = mesh_cmds[0].kwargs.get("UNITE")
        if unite is not None:
            try:
                parsed.mesh_unite = int(unite)
            except (TypeError, ValueError):
                pass
        fmt = mesh_cmds[0].kwargs.get("FORMAT")
        if fmt and not parsed.mesh_format:
            parsed.mesh_format = str(fmt).upper()
    if not parsed.has_model:
        parsed.warnings.append("No AFFE_MODELE found. Every SEG2 is treated as a beam.")
        all_beams = True
    parsed.beam_groups = beam_groups
    parsed.all_edges_are_beams = all_beams

    for cara in cara_cmds:
        for factor in _as_factors(cara.kwargs.get("POUTRE")):
            section = factor.get("SECTION")
            values, notes = _cara_values(factor)
            parsed.warnings.extend(notes)
            if section is None:
                parsed.warnings.append("A POUTRE factor without SECTION is skipped.")
                continue
            vari = str(factor.get("VARI_SECT", "CONSTANT")).upper()
            payload = {"section": str(section).upper(), "values": values, "vari": vari}
            if vari not in ("CONSTANT", ""):
                parsed.warnings.append(
                    "VARI_SECT={} is drawn with the dimensions at the start of the beam.".format(vari)
                )
                # Homothetisch: HY1/HZ1 bevorzugen, sonst HY/HZ.
                alias = {}
                for key, val in values.items():
                    if key.endswith("1") and key[:-1] not in values:
                        alias[key[:-1]] = val
                values.update(alias)
                payload["values"] = values
            parsed.sections.append(_target(factor, payload))
        for factor in _as_factors(cara.kwargs.get("ORIENTATION")):
            o_cara = str(factor.get("CARA", "")).upper()
            values, notes = _cara_values(factor)
            parsed.warnings.extend(notes)
            if not o_cara:
                continue
            parsed.orientations.append(
                _target(factor, {"cara": o_cara, "values": values})
            )
    return parsed


def match_target(target: Target, groups, name):
    if target.tout:
        return True
    if name and name in target.mailles:
        return True
    return any(g in target.groups for g in groups)


def resolve_assignments(assignments, groups, name):
    """Letzte passende Zuweisung gewinnt (Règle de surcharge)."""
    chosen = None
    for target in assignments:
        if match_target(target, groups, name):
            chosen = target
    return chosen
