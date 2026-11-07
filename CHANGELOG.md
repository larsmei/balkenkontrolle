# Änderungsprotokoll

## 1.1.1 — 2026-11-07

* Der geöffnete AsterStudy-Fall wird über `ASTERSTUDYGUI.get_aster_gui()` gelesen. `AsterGui.instance()` gibt es dort nicht, deshalb kam bisher „Kein AsterStudy-Fall“.
* Dateien der Stufe (MED, mail) kommen aus `handle2info`, auch relativ zum Studienordner. Eine SALOME-Entry wird als SMESH-Netz geöffnet.
* „Visualisieren“ liest den Fall neu, statt einen leeren Stand vom Dialogstart zu verwenden.

## 1.1.0 — 2026-11-07

* Darstellung in der AsterStudy-Ansicht als SMESH-Netz `Balkenkontrolle`. Das GEOM-Modul wird nicht mehr geöffnet.
* MED: SEG2/SEG3 werden auf allen nicht leeren Zelldimensionen gelesen, nicht nur auf der höchsten. Gruppen gehören zur Ebene der Balken. SEG3 nimmt die beiden Endknoten, auch wenn der Mittelknoten dazwischen steht.

## 1.0.1 — 2026-11-07

* Querschnitte: `geomBuilder.MakePrism` wird mit Basis und zwei Punkten aufgerufen, wie in SALOME 9. Der vorherige Aufruf mit einem Vektor lief in `missing 1 required positional argument: 'thePoint2'`. Ältere Stände mit `MakePrismVecH` oder `MakePrism(base, vector)` bleiben nutzbar.

## 1.0.0 — 2026-11-07

Erstes Release.

* SALOME-Plugin für AsterStudy: lokale Balkenachsen und extrudierte Querschnitte im GEOM-Modul.
* Orientierung nach Code_Aster U4.42.01: Standardrahmen, Sonderfall Stab parallel zur globalen Z-Achse, `ANGL_VRIL`, `VECT_Y`, `VECT_Z`, Hinweis bei `VECT_MAIL_Y` / `VECT_MAIL_Z`.
* Schnitte `RECTANGLE` (voll und hohl), `CERCLE` (voll und Rohr), `GENERALE` als Hülle aus RY/RZ, `COUDE` nur als Nenngeometrie.
* Quelle: aktueller AsterStudy-Fall, comm- plus Netzdatei (MED oder ASTER-mail) oder ein geladenes SMESH-Netz.
* Beispielrahmen `beispiele/rahmen` und Unit-Tests ohne SALOME.
