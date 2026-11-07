# Änderungsprotokoll

## 1.0.0 — 2026-11-07

Erstes Release.

* SALOME-Plugin für AsterStudy: lokale Balkenachsen und extrudierte Querschnitte im GEOM-Modul.
* Orientierung nach Code_Aster U4.42.01: Standardrahmen, Sonderfall Stab parallel zur globalen Z-Achse, `ANGL_VRIL`, `VECT_Y`, `VECT_Z`, Hinweis bei `VECT_MAIL_Y` / `VECT_MAIL_Z`.
* Schnitte `RECTANGLE` (voll und hohl), `CERCLE` (voll und Rohr), `GENERALE` als Hülle aus RY/RZ, `COUDE` nur als Nenngeometrie.
* Quelle: aktueller AsterStudy-Fall, comm- plus Netzdatei (MED oder ASTER-mail) oder ein geladenes SMESH-Netz.
* Beispielrahmen `beispiele/rahmen` und Unit-Tests ohne SALOME.
