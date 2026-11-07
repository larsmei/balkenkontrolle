# Querschnitte

Alle Maße stehen in denselben Einheiten wie das Netz, bei Code_Aster in der Regel Meter. Der Schwerpunkt des gezeichneten Schnitts liegt auf der Stabachse. `HY` läuft in lokalem Y, `HZ` in lokalem Z.

In der AsterStudy-Ansicht entsteht das SMESH-Netz `Balkenkontrolle`. Pro Gruppe gibt es eine Flächengruppe `Balkenkontrolle_Querschnitt_…`, die Achsen liegen in `Balkenkontrolle_X`, `_Y` und `_Z`. Ein neuer Lauf ersetzt das Netz. **Anzeige entfernen** nimmt es wieder aus der Ansicht. GEOM wird nicht benutzt.

Die Option **Entlang des Stabes** prismt den Schnitt über die Stablänge. Ohne sie liegt nur eine Scheibe in Stabmitte, plus die Achsen. Die Achslänge ist ein Anteil der Stablänge (Vorgabe 0,22), gemessen ab dem ersten Knoten.

## RECTANGLE

`CARA=('HY','HZ')` und optional `EPY`, `EPZ`.

Der Vollquerschnitt ist das Rechteck `HY` × `HZ`.

Mit Wanddicken wird ein Loch `HY − 2·EPY` mal `HZ − 2·EPZ` ausgeschnitten. `EPY` ist die Dicke der beiden Wände senkrecht zu Y, `EPZ` die Dicke der beiden Wände senkrecht zu Z. Die Fläche ist

```text
A = HY·HZ − (HY − 2·EPY)·(HZ − 2·EPZ)
```

solange das Loch positiv bleibt. Füllt die Wand den Schnitt, erscheint der Vollquerschnitt und ein Hinweis.

Flächenträgheitsmomente im Protokoll, bezogen auf den Schwerpunkt:

```text
IY = (HY·HZ³ − innenY·innenZ³) / 12
IZ = (HZ·HY³ − innenZ·innenY³) / 12
```

`IY` ist das Moment um die lokale Y-Achse. Das sind Kontrollwerte der gezeichneten Kontur, nicht die Ausgabe von `POST_ELEM`.

## CERCLE

`CARA='R'` und optional `EP`.

`R` ist der Außenradius. Fehlt `EP`, oder ist `EP` gleich `R`, ist der Kreis voll. `0 < EP < R` zeichnet ein Rohr mit Innenradius `R − EP`. `EP > R` fällt auf den Vollkreis zurück, mit Hinweis.

Die Drehung um die Stabachse ändert einen konzentrischen Kreis nicht. Die Achsen bleiben sichtbar, damit `ANGL_VRIL` trotzdem prüfbar ist.

## GENERALE

`SECTION='GENERALE'` hat in der comm-Datei keine Kontur, sondern Flächenwerte und Trägheiten (`A`, `IY`, `IZ`, `AY`, `AZ`, `JX`, `RY`, `RZ`, …).

Gezeichnet wird nur die elliptische Hülle mit Halbachsen `RY` und `RZ`. Das ist nicht das Fertigprofil. Das Protokoll sagt das. Fehlen `RY` und `RZ` oder sind sie nicht positiv, erscheinen nur die Achsen.

## COUDE

Bögen werden nicht als gebogene Mittellinie vernetzt. `SECTION='COUDE'` übernimmt die Nennmaße (`HY`/`HZ` oder `R`) und zeichnet die gerade Nennkontur zwischen den Endknoten. Ovalisierung und der Krümmungsradius bleiben draußen. Das Protokoll weist darauf hin.

## Farbe

Alle Schnitte einer Gruppe haben dieselbe Farbe. Die Achsen sind fest:

| Achse | Farbe | Bedeutung |
| --- | --- | --- |
| X | rot | Stabachse, erster Knoten → zweiter Knoten |
| Y | grün | Richtung von `HY` |
| Z | blau | Richtung von `HZ` |

## Beispiel

`beispiele/rahmen.comm` mit `beispiele/rahmen.mail`:

| Gruppe | Schnitt | Orientierung |
| --- | --- | --- |
| `STUETZE` | Rechteck 0,30 × 0,45 | `VECT_Y = (1, 0, 0)`, also HY in globalem X |
| `RIEGEL` | Rechteck 0,18 × 0,42 | `ANGL_VRIL = 0`, lokales Z = globales Z |
| `TRAVERSE` | Hohlkasten 0,16 × 0,32, Wand 12 mm | Standardrahmen |
| `VERBAND` | Rohr R = 60 mm, EP = 5 mm | Standardrahmen |

Die Stützen stehen auf der globalen Z-Achse. Ohne `VECT_Y` läge lokales Y auf dem globalen Y. Mit `VECT_Y = (1, 0, 0)` liegt HY in globalem X und HZ in globalem Y.
