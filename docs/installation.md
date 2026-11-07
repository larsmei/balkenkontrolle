# Installation

The plugin is plain Python. Nothing has to be compiled. SALOME must be closed while the files are copied.

## Files

SALOME loads exactly one `salome_plugins.py` from each plugin directory. The package `beamcheck/` must sit next to it, because `salome_plugins.py` imports it from that folder. The beam icon is `beamcheck/icons/beam.png`.

| File or folder | Required |
| --- | --- |
| `salome_plugins.py` | yes |
| `beamcheck/` | yes |
| `beispiele/` | no, only for trying the example |
| `tests/` | no |

## Way 1 — own directory (recommended)

This does not overwrite an existing `~/.config/salome/Plugins/salome_plugins.py`.

```bash
mkdir -p "$HOME/salome/plugins/balkenkontrolle"
cp -a salome_plugins.py beamcheck "$HOME/salome/plugins/balkenkontrolle/"
```

In the environment that starts SALOME:

```bash
export SALOME_PLUGINS_PATH="$HOME/salome/plugins/balkenkontrolle${SALOME_PLUGINS_PATH:+:$SALOME_PLUGINS_PATH}"
```

Put that line in the shell file from which SALOME is started, or in the SALOME launch script. Then restart SALOME.

## Way 2 — user plugins

Use this only when `~/.config/salome/Plugins/` does not already contain a `salome_plugins.py`. An existing file holds other extensions. Do not replace it. Use way 1, or append the registration block from `salome_plugins.py` to the existing file and copy `beamcheck/` beside it.

```bash
mkdir -p "$HOME/.config/salome/Plugins"
cp -a salome_plugins.py beamcheck "$HOME/.config/salome/Plugins/"
```

## Way 3 — AsterStudy plugin folder

```text
<ASTERSTUDY_ROOT>/share/salome/plugins/asterstudy/
```

This needs write access to the SALOME installation. A distribution update removes the file. Way 1 lasts longer.

## Start

Restart SALOME. Switching modules is not enough. Plugin files are read at startup.

Open the **AsterStudy** module. The entry is under

**Tools → Extensions → Beam check (orientation and section)**.

The AsterStudy menu bar shows **Beams**, with an I-beam icon. One click shows the beams of the active study, the next hides them.

If the entry is missing:

* Is `salome_plugins.py` in a directory SALOME actually searches, and not one level above it?
* Was another `salome_plugins.py` loaded from a different path, so this one was never reached?
* Does the SALOME log report an import error from `beamcheck`? Then the package is not next to the plugin file, or Python is older than 3.7.

## Runtime dependencies

| Environment | What is needed |
| --- | --- |
| Dialog | PyQt5, or PyQt6, both ship with SALOME |
| Display | SMESH, shown in the AsterStudy view |
| MED mesh | MEDLoader, part of SALOME |
| ASTER mail | no extra library |
| Unit tests | Python 3.7 or newer, without SALOME |

The core is tested without the GUI:

```bash
python3 -m unittest tests/test_beamcheck.py
```
