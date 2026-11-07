# Änderungsprotokoll

## 1.1.7 — 2026-11-07

* Der Schalter **Balken** steht in der Menüleiste von AsterStudy. Die frühere Anheftung an eine Werkzeugleiste hat SALOME verworfen, deshalb war er nicht sichtbar.

## 1.1.6 — 2026-11-07

* `SECTION='GENERALE'` wird als elliptischer Vollquerschnitt gezeichnet. Die Halbachsen sind so gewählt, dass `IY` und `IZ` mit den Angaben des Balkens übereinstimmen.

## 1.1.5 — 2026-11-07

* Der Schalter **Balken** wird nur noch einmal eingehängt. Vorhandene Doppelgänger werden entfernt.
* Kantengruppen am SMESH-Netz werden auch gelesen, wenn der Typvergleich von SALOME 9 scheitert. Dadurch zählen `POU_D_T`-Gruppen wie `topbeam` wieder als Balken.

## 1.1.4 — 2026-11-07

* Schalter **Balken** in der Befehlsleiste, rechts neben den Stufen. Er visualisiert die Balkenelemente der aktiven Studie und blendet sie wieder aus.

## 1.1.3 — 2026-11-07

* **Anzeige entfernen** löscht das Kontrollnetz aus der Studie und aus der Ansicht. AsterStudy bleibt das aktive Modul.

## 1.1.2 — 2026-11-07

* Kein ``import MEDCoupling`` mehr. Die Hülle in SALOME 9 beendet den Prozess mit ``_PyThreadState_Attach``. Zelltypen bleiben die festen Werte SEG2=1 und SEG3=2.
* Liegt genau ein Netz mit Kanten schon in der Studie, wird es verwendet. Die MED-Datei wird dann nicht ein zweites Mal geöffnet.

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
