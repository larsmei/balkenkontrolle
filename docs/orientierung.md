# Orientierung

Grundlage ist Code_Aster, Dokument **U4.42.01** (Operator `AFFE_CARA_ELEM`, Faktorwort `ORIENTATION`) für gerade Balkenelemente `POU_*` auf Kanten `SEG2`. Die Referenzbeschreibung der Theorie steht in **R3.08.01**.

Das Plugin zeichnet denselben Rahmen, den die Rechnung für die Steifigkeit benutzt. Es ersetzt nicht `REPERE_LOCAL` in den Ergebnissen und nicht den Winkel aus `MACR_CARA_POUTRE`.

## Achsen

Lokales X, im Viewer **rot**, zeigt vom ersten zum zweiten Knoten der Kante. Die Knotenreihenfolge kommt aus dem Netz, nicht aus der Gruppe.

Lokales Y ist **grün**, lokales Z **blau**. Das Tripel (X, Y, Z) ist rechtshändig.

Der Querschnitt liegt in der Ebene senkrecht zu X:

* `HY` läuft entlang Y
* `HZ` läuft entlang Z
* bei `CERCLE` ist der Radius senkrecht zu X, unabhängig von der Drehung um X, solange der Kreis voll oder konzentrisch ist

## Standardrahmen

Ohne Faktorwort `ORIENTATION`, oder mit `CARA='ANGL_VRIL'` und `VALE=0`, oder mit `CARA` leer bzw. `DEFAULT`.

Liegt der Stab **nicht** auf der globalen Z-Achse:

1. `ex` = normierter Vektor vom ersten zum zweiten Knoten
2. `ey` = normiertes Kreuzprodukt aus globalem Z und `ex`
3. `ez` = `ex` × `ey`

Bei einem horizontalen Stab zeigt lokales Z damit nach oben (globales Z). Lokales Y liegt in der horizontalen Ebene.

Liegt der Stab **parallel zur globalen Z-Achse**, verschwindet das Kreuzprodukt. Code_Aster legt dann lokales Y parallel zum globalen Y. Das Plugin macht dasselbe und schreibt den Hinweis ins Protokoll. Als parallel gilt ein Sinus des Winkels unter `1e-10`.

## ANGL_VRIL

`CARA='ANGL_VRIL'`, `VALE` in **Grad**.

Der Winkel dreht den Standardrahmen **rechtshändig um lokales X**. Positiv dreht Y in Richtung Z. Ein horizontaler Stab mit `ANGL_VRIL=90` trägt `HY` damit nach oben, wo vorher `HZ` lag.

`ANGL_VRIL` wird nicht zusätzlich auf `VECT_Y` oder `VECT_Z` aufgeschlagen. Steht beides in der comm-Datei, gilt die letzte Zuweisung für die Gruppe, wie bei Code_Aster die Surcharge.

## VECT_Y und VECT_Z

`VALE` hat drei Komponenten im **globalen** System.

Der Vektor wird auf die Ebene senkrecht zum Stab projiziert. Die Projektion wird `ey` (`VECT_Y`) oder `ez` (`VECT_Z`). Die fehlende Achse ergänzt das rechtshändige System.

Ist der Vektor parallel zum Stab, ist die Projektion null. Code_Aster bricht die Rechnung ab. Das Plugin zeichnet den Standardrahmen und schreibt eine Warnung. Als parallel gilt eine Projektion, die kürzer ist als `1e-8` mal der Vektorlänge.

Ein Vektor, der nur knapp aus der Stabachse herauszeigt, wird trotzdem verwendet. Kleine Komponenten kippen den Rahmen dann stark. Das ist dasselbe Verhalten wie in der Rechnung. Im Protokoll steht keine Extra-Warnung, solange die Projektion über der Schwelle liegt.

## VECT_MAIL_Y und VECT_MAIL_Z

Die Netzfaser wird wie `VECT_Y` bzw. `VECT_Z` projiziert. Der Winkel zwischen dieser Faser und den Hauptachsen des Profils, den `MACR_CARA_POUTRE` liefert, wird **nicht** addiert. Das Protokoll sagt das ausdrücklich. Für ein Rechteck oder einen Kreis ohne Hauptachsenversatz ist die Darstellung vollständig. Für ein allgemeines Profil mit verdrehten Hauptachsen fehlt dieser Anteil.

## Was nicht gezeichnet wird

* `ANGL_NAUT`, `ANGL_EUL`, `ANGL_REP` und andere Vorgaben, die nicht zum geraden SEG2-Balken gehören. Hinweis im Protokoll, Standardrahmen bleibt.
* Krumme Elemente und `SEG3` nur über die beiden Endknoten, als wäre die Kante gerade.
* Diskrete Elemente `DIS_*` ohne Balkenquerschnitt bleiben ohne Körper.

## Gruppen und Reihenfolge

`GROUP_MA`, `MAILLE` und `TOUT` werden aufgelöst. Mehrere `AFFE_CARA_ELEM` und mehrere Einträge in `POUTRE` und `ORIENTATION` gelten in der Reihenfolge der comm-Datei. Der spätere Eintrag überschreibt den früheren für dieselbe Kante.

Nur Kanten, deren Modellierung mit `POU` beginnt (`POU_D_E`, `POU_D_T`, `POU_D_TG`, …), bekommen einen Körper. Steht keine `AFFE_MODELE`-Zuweisung auf der Kante, wird sie trotzdem gezeichnet, sobald sie einen Balkenquerschnitt trägt. Das fängt Studien ab, in denen das Modell in einem anderen Include steht.

`INCLUDE` wird nicht expandiert. Die comm-Datei, die der Dialog liest, muss die Schlüsselwörter selbst enthalten.
