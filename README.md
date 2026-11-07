# Beam check for SALOME / AsterStudy

Plugin for a **check before the analysis**: local beam axes and the
cross-sections from `AFFE_CARA_ELEM`, the way Code_Aster uses them for `POU_*`
(document U4.42.01). AsterStudy no longer shows this since Eficas.

X is red, Y is green, Z is blue. The section lies in the local frame:
HY along Y, HZ along Z, tubes through R and EP.

## Rules

* Local X points from the first node of the SEG2 to the second.
* Without `ORIENTATION`, `ANGL_VRIL = 0`.
* If the beam is not along global Z, local Y is the normalised cross product
  of global Z and local X. Local Z completes the right-handed frame. On a
  horizontal beam, local Z then points upward.
* If the beam lies on global Z, local Y is parallel to global Y.
* `VECT_Y` / `VECT_Z`: the projection of the vector onto the plane normal to
  the beam becomes Y or Z. A vector parallel to the beam is invalid
  (Code_Aster rejects it). The plugin falls back to the default frame and
  writes a note.
* `ANGL_VRIL` rotates the default frame right-handed about X, in degrees.
* `VECT_MAIL_Y/Z` is shown without the principal-axis angle from
  `MACR_CARA_POUTRE`. `SECTION='GENERALE'` is a solid ellipse with the same
  `IY` and `IZ`.

Supported sections: `RECTANGLE` (solid and with EPY/EPZ), `CERCLE`
(solid and tube), `GENERALE` (equivalent solid ellipse), `COUDE` as nominal
geometry only.

## Install

Close SALOME. Copy `salome_plugins.py` and the package `beamcheck/` to one of:

1. `~/.config/salome/Plugins/`
2. a directory on `$SALOME_PLUGINS_PATH`
3. `<ASTERSTUDY_ROOT>/share/salome/plugins/asterstudy/`

Restart SALOME, open AsterStudy, then

**Tools → Extensions → Beam check (orientation and section)**.

The menu bar of AsterStudy has a **Beams** button with an I-beam icon. One
click shows the beams of the active study, the next hides them.

In the dialog, use the current case or pick a command file and a mesh file
(MED or ASTER mail). A mesh already loaded in SMESH works too. The check
appears in the **AsterStudy view** as the mesh `BeamCheck` (faces, not a GEOM
shape). A new run replaces the previous one. MED files are read on every
non-empty cell level, not only the highest one, so beams stored under a
volume mesh are kept.

Checked with the included study `beispiele/rahmen.comm` and
`beispiele/rahmen.mail` (without SALOME):

```bash
python3 -m unittest tests/test_beamcheck.py
```

Python 3.7 or newer. The GUI needs PyQt5 (or PyQt6) and the SALOME modules
GEOM and, for MED, MEDLoader.

The display checks the input. It does not replace `MACR_CARA_POUTRE` or the
results of `IMPR_RESU` / `REPERE_LOCAL`.
