# -*- coding: utf-8 -*-
"""SALOME-Plugin: Balkenorientierung und Querschnitte zur Kontrolle.

Ablage (eine der drei Möglichkeiten), danach SALOME neu starten:

* ~/.config/salome/Plugins/
* $SALOME_PLUGINS_PATH  (dieses Verzeichnis)
* <ASTERSTUDY_ROOT>/share/salome/plugins/asterstudy/

Der Menüpunkt liegt unter Werkzeuge → Erweiterungen
(„Balkenkontrolle (Orientierung und Querschnitt)“).
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import salome_pluginsmanager

_TITLE = "Balkenkontrolle (Orientierung und Querschnitt)"
_HELP = (
    "Zeigt lokale Balkenachsen (X rot, Y grün, Z blau) und die Querschnitte "
    "aus AFFE_CARA_ELEM in der AsterStudy-Ansicht. Regeln nach Code_Aster U4.42.01."
)


def balkenkontrolle(context):
    from beamcheck.dialog import run_dialog

    run_dialog(context)


try:
    salome_pluginsmanager.AddFunction(_TITLE, _HELP, balkenkontrolle, module="ASTERSTUDY")
except TypeError:
    salome_pluginsmanager.AddFunction(_TITLE, _HELP, balkenkontrolle)
