# Installation

Das Plugin ist reines Python. Es braucht kein Kompilieren. SALOME muss geschlossen sein, während die Dateien kopiert werden.

## Dateien

SALOME lädt in jedem Plugin-Verzeichnis genau eine Datei `salome_plugins.py`. Daneben muss das Paket `beamcheck/` liegen, weil `salome_plugins.py` es über denselben Ordner importiert.

| Datei oder Ordner | Pflicht |
| --- | --- |
| `salome_plugins.py` | ja |
| `beamcheck/` | ja |
| `beispiele/` | nein, nur zum Ausprobieren |
| `tests/` | nein |

## Weg 1 — eigenes Verzeichnis (empfohlen)

Ein vorhandenes `~/.config/salome/Plugins/salome_plugins.py` wird so nicht überschrieben.

```bash
mkdir -p "$HOME/salome/plugins/balkenkontrolle"
cp -a salome_plugins.py beamcheck "$HOME/salome/plugins/balkenkontrolle/"
```

In der Umgebung, in der SALOME startet:

```bash
export SALOME_PLUGINS_PATH="$HOME/salome/plugins/balkenkontrolle${SALOME_PLUGINS_PATH:+:$SALOME_PLUGINS_PATH}"
```

Die Zeile gehört in die Shell-Datei, aus der SALOME gestartet wird, oder in das SALOME-Startskript. Danach SALOME neu starten.

## Weg 2 — Benutzer-Plugins

Nur verwenden, wenn unter `~/.config/salome/Plugins/` noch keine `salome_plugins.py` liegt. Eine vorhandene Datei enthält andere Erweiterungen. Sie nicht ersetzen. Dann Weg 1 nehmen oder den Registrierungsblock aus `salome_plugins.py` unten an die bestehende Datei hängen und `beamcheck/` daneben kopieren.

```bash
mkdir -p "$HOME/.config/salome/Plugins"
cp -a salome_plugins.py beamcheck "$HOME/.config/salome/Plugins/"
```

## Weg 3 — AsterStudy-Pluginordner

```text
<ASTERSTUDY_ROOT>/share/salome/plugins/asterstudy/
```

Dafür sind Schreibrechte auf die SALOME-Installation nötig. Nach einem Update der Distribution ist die Datei weg. Weg 1 ist dauerhafter.

## Start

SALOME neu starten, nicht nur das Modul wechseln. Plugin-Dateien werden beim Start gelesen.

Modul **AsterStudy** öffnen. Der Eintrag liegt unter

**Werkzeuge → Erweiterungen → Balkenkontrolle (Orientierung und Querschnitt)**.

In der Menüleiste von AsterStudy steht der Schalter **Balken**. Ein Klick zeigt die Balken der aktiven Studie, der nächste blendet sie aus.

Fehlt der Eintrag:

* Liegt `salome_plugins.py` wirklich in dem Verzeichnis, das SALOME durchsucht, und nicht eine Ebene darüber?
* Wurde eine zweite `salome_plugins.py` aus einem anderen Pfad geladen und diese hier nie erreicht?
* Steht im SALOME-Protokoll ein Importfehler aus `beamcheck`? Dann fehlt das Paket neben der Plugin-Datei, oder die Python-Version ist älter als 3.7.

## Abhängigkeiten zur Laufzeit

| Umgebung | Was gebraucht wird |
| --- | --- |
| Dialog | PyQt5, ersatzweise PyQt6, beides kommt mit SALOME |
| Darstellung | SMESH, sichtbar in der AsterStudy-Ansicht |
| MED-Netz | MEDLoader, Teil von SALOME |
| ASTER-mail | keine Zusatzbibliothek |
| Unit-Tests | Python 3.7 oder neuer, ohne SALOME |

Getestet ist der Kern ohne GUI:

```bash
python3 -m unittest tests/test_beamcheck.py
```
