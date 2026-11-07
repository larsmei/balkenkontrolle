# Balkenkontrolle

Plugin für **SALOME / AsterStudy**. Es zeigt vor der Rechnung, wie Code_Aster die Balken eines Falls orientiert und welchen Querschnitt `AFFE_CARA_ELEM` ihnen gibt.

Seit dem Wegfall der Eficas-Vorschau fehlt diese Kontrolle im Modul. Das Plugin legt die Körper im Modul **GEOM** ab: lokale Achse X rot, Y grün, Z blau, der Querschnitt als Prisma entlang des Stabes.

Die Regeln folgen Code_Aster **U4.42.01** für gerade `POU_*`-Elemente auf `SEG2`.

Die Darstellung prüft die Eingabe. Sie ersetzt weder `MACR_CARA_POUTRE` noch `IMPR_RESU` / `REPERE_LOCAL`.

## Installation

Kurzfassung, wenn noch keine andere `salome_plugins.py` im Benutzerordner liegt:

```bash
mkdir -p "$HOME/.config/salome/Plugins"
cp -a salome_plugins.py beamcheck "$HOME/.config/salome/Plugins/"
```

SALOME neu starten. In AsterStudy:

**Werkzeuge → Erweiterungen → Balkenkontrolle (Orientierung und Querschnitt)**

Liegt dort schon eine `salome_plugins.py`, diese Datei nicht überschreiben. Das Plugin in ein eigenes Verzeichnis legen und `SALOME_PLUGINS_PATH` setzen. Die drei Wege, der Hinweis zum bestehenden Plugin und die Laufzeitabhängigkeiten stehen in [docs/installation.md](docs/installation.md).

Python 3.7 oder neuer. Im GUI werden PyQt5 (oder PyQt6) und GEOM erwartet, für MED-Dateien zusätzlich MEDLoader. Alles davon bringt SALOME mit.

## Bedienung

| Quelle | Wann |
| --- | --- |
| Aktueller AsterStudy-Fall | comm-Text und die Datei aus `LIRE_MAILLAGE` / `UNITE` kommen aus der offenen Studie |
| comm- und Netzdatei | Dateien vom Rechner, MED oder ASTER-`.mail` |
| SMESH-Netz | ein bereits geladenes Netz, Gruppen inklusive |

Optionen im Dialog:

* **Querschnitte** und **Achsen X Y Z** lassen sich getrennt schalten.
* **Entlang des Stabes** prismt den Schnitt über die Länge. Sonst liegt eine Scheibe in der Mitte.
* **Achslänge / Stablänge** setzt die Pfeillänge, Vorgabe 0,22.
* **GEOM öffnen** wechselt nach dem Lauf in das GEOM-Modul.

Die Körper heißen `Balkenkontrolle_…`. Ein neuer Lauf ersetzt den vorherigen. Hinweise (paralleler Vektor, Hohlprofil zugelaufen, `GENERALE` nur als Hülle) stehen im Textfeld des Dialogs.

## Orientierung

* Lokales X zeigt vom ersten zum zweiten Knoten.
* Ohne `ORIENTATION` gilt der Standardrahmen (`ANGL_VRIL = 0`).
* Stab nicht parallel zu global Z: lokales Y ist das normierte Kreuzprodukt aus globalem Z und lokalem X. Bei einem horizontalen Stab zeigt lokales Z nach oben.
* Stab parallel zu global Z: lokales Y liegt parallel zum globalen Y.
* `VECT_Y` / `VECT_Z`: die Projektion auf die Schnittebene wird Y bzw. Z. Ein zum Stab paralleler Vektor ist ungültig. Gezeigt wird dann der Standardrahmen, plus Hinweis.
* `ANGL_VRIL` dreht den Standardrahmen rechtshändig um X, in Grad.
* `VECT_MAIL_Y` / `VECT_MAIL_Z` ohne den Hauptachsenwinkel aus `MACR_CARA_POUTRE`.

Ausführlich, inklusive Surcharge und `INCLUDE`: [docs/orientierung.md](docs/orientierung.md).

## Querschnitte

| `SECTION` | Gezeichnet |
| --- | --- |
| `RECTANGLE` | Vollquerschnitt `HY` × `HZ`, mit `EPY`/`EPZ` als Hohlkasten |
| `CERCLE` | Vollkreis über `R`, mit `EP` < `R` als Rohr |
| `GENERALE` | nur die Hülle ±`RY`, ±`RZ`, nicht das Fertigprofil |
| `COUDE` | Nenngeometrie, gerade zwischen den Endknoten, ohne Ovalisierung |

`HY` liegt auf lokalem Y, `HZ` auf lokalem Z. Details und die Flächenformeln: [docs/querschnitte.md](docs/querschnitte.md).

## Beispiel

`beispiele/rahmen.comm` und `beispiele/rahmen.mail` beschreiben einen Rahmen mit Stützen, Riegeln, Hohlkasten-Traversen und Rohrverband.

Die Stützen nutzen `VECT_Y = (1, 0, 0)`, der Riegel `ANGL_VRIL = 0`. Im Dialog **comm- und Netzdatei** wählen und beide Dateien angeben. Eine SALOME-Studie ist dafür nicht nötig, das Netz ist ASTER-mail.

## Tests

Ohne SALOME, aus dem Projektverzeichnis:

```bash
python3 -m unittest tests/test_beamcheck.py
```

Die Tests prüfen den Standardrahmen, den Sonderfall parallel zu Z, `ANGL_VRIL`, `VECT_Y`, den parallelen Vektor und das Einlesen des Beispielrahmens.

## Grenzen

* `INCLUDE` wird nicht expandiert. Die gelesene comm-Datei muss `AFFE_CARA_ELEM` selbst enthalten.
* `SEG3` wird über die Endknoten behandelt.
* Diskrete Elemente ohne Balkenquerschnitt bleiben unsichtbar.
* Der Winkel zwischen einer `VECT_MAIL_*`-Faser und den Hauptachsen eines allgemeinen Profils fehlt.
* Sehr viele Stäbe werden zu einem Compound je Gruppe zusammengefasst. Einzelne GEOM-Objekte pro Stab gibt es nicht.

## Lizenz

[MIT](LICENSE).
