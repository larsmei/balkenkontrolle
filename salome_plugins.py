# -*- coding: utf-8 -*-
"""SALOME plugin: beam orientation and cross-sections for checking.

Copy the files (one of the three places), then restart SALOME:

* ~/.config/salome/Plugins/
* $SALOME_PLUGINS_PATH  (this directory)
* <ASTERSTUDY_ROOT>/share/salome/plugins/asterstudy/

The menu entry is under Tools → Extensions
("Beam check (orientation and section)").
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import salome_pluginsmanager

_TITLE = "Beam check (orientation and section)"
_HELP = (
    "Shows local beam axes (X red, Y green, Z blue) and the cross-sections "
    "from AFFE_CARA_ELEM in the AsterStudy view. Rules follow Code_Aster U4.42.01."
)


def balkenkontrolle(context):
    from beamcheck.dialog import run_dialog

    run_dialog(context)


try:
    salome_pluginsmanager.AddFunction(_TITLE, _HELP, balkenkontrolle, module="ASTERSTUDY")
except TypeError:
    salome_pluginsmanager.AddFunction(_TITLE, _HELP, balkenkontrolle)

try:
    from beamcheck.toolbar import ensure_toolbar

    ensure_toolbar()
except Exception:
    pass
