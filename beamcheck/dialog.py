"""Dialog der Balkenkontrolle. Läuft im GUI-Prozess von SALOME (PyQt5)."""

from __future__ import annotations

import traceback

from beamcheck.mesh_io import MeshError, edges_from_smesh
from beamcheck.parser import CommError, parse_comm
from beamcheck.report import build_report


def _qt():
    try:
        from PyQt5 import QtCore, QtWidgets
    except ImportError:
        from PyQt6 import QtCore, QtWidgets
    return QtCore, QtWidgets


def run_dialog(context):
    QtCore, QtWidgets = _qt()

    class Dialog(QtWidgets.QDialog):
        def __init__(self):
            super(Dialog, self).__init__()
            self.setWindowTitle("Balkenkontrolle")
            self.setMinimumWidth(560)
            self.context = context
            self._case = None
            self._meshes = []
            self._build()
            self._load_sources()

        def _build(self):
            layout = QtWidgets.QVBoxLayout(self)
            intro = QtWidgets.QLabel(
                "Lokale Achsen und Querschnitte aus AFFE_CARA_ELEM, "
                "nach U4.42.01. Die Kontrolle erscheint in der AsterStudy-Ansicht "
                "als Netz Balkenkontrolle, nicht im GEOM-Modul."
            )
            intro.setWordWrap(True)
            layout.addWidget(intro)

            form = QtWidgets.QFormLayout()
            self.source = QtWidgets.QComboBox()
            self.source.addItem("Aktueller AsterStudy-Fall", "case")
            self.source.addItem("comm- und Netzdatei", "files")
            form.addRow("Quelle", self.source)

            self.mesh_choice = QtWidgets.QComboBox()
            form.addRow("SMESH-Netz", self.mesh_choice)

            file_row = QtWidgets.QHBoxLayout()
            self.comm_path = QtWidgets.QLineEdit()
            comm_btn = QtWidgets.QPushButton("comm…")
            comm_btn.clicked.connect(self._pick_comm)
            file_row.addWidget(self.comm_path)
            file_row.addWidget(comm_btn)
            form.addRow("comm-Datei", file_row)

            mesh_row = QtWidgets.QHBoxLayout()
            self.mesh_path = QtWidgets.QLineEdit()
            mesh_btn = QtWidgets.QPushButton("Netz…")
            mesh_btn.clicked.connect(self._pick_mesh)
            mesh_row.addWidget(self.mesh_path)
            mesh_row.addWidget(mesh_btn)
            form.addRow("Netzdatei", mesh_row)
            layout.addLayout(form)

            options = QtWidgets.QHBoxLayout()
            self.sections = QtWidgets.QCheckBox("Querschnitte")
            self.sections.setChecked(True)
            self.axes = QtWidgets.QCheckBox("Achsen X Y Z")
            self.axes.setChecked(True)
            self.solid = QtWidgets.QCheckBox("Entlang des Stabes")
            self.solid.setChecked(True)
            self.fit = QtWidgets.QCheckBox("Ansicht einpassen")
            self.fit.setChecked(True)
            options.addWidget(self.sections)
            options.addWidget(self.axes)
            options.addWidget(self.solid)
            options.addWidget(self.fit)
            layout.addLayout(options)

            scale_row = QtWidgets.QHBoxLayout()
            scale_row.addWidget(QtWidgets.QLabel("Achslänge / Stablänge"))
            self.fraction = QtWidgets.QDoubleSpinBox()
            self.fraction.setRange(0.05, 0.8)
            self.fraction.setSingleStep(0.02)
            self.fraction.setValue(0.22)
            scale_row.addWidget(self.fraction)
            scale_row.addStretch(1)
            layout.addLayout(scale_row)

            self.log = QtWidgets.QPlainTextEdit()
            self.log.setReadOnly(True)
            self.log.setMinimumHeight(180)
            layout.addWidget(self.log)

            buttons = QtWidgets.QHBoxLayout()
            run = QtWidgets.QPushButton("Visualisieren")
            run.clicked.connect(self._run)
            clear = QtWidgets.QPushButton("Anzeige entfernen")
            clear.clicked.connect(self._clear)
            close = QtWidgets.QPushButton("Schließen")
            close.clicked.connect(self.reject)
            buttons.addStretch(1)
            buttons.addWidget(run)
            buttons.addWidget(clear)
            buttons.addWidget(close)
            layout.addLayout(buttons)

        def _load_sources(self):
            try:
                from beamcheck.aster_access import current_case, list_smesh_meshes

                try:
                    self._case = current_case()
                    nfiles = len(self._case.get("files") or [])
                    self._say("AsterStudy-Fall gelesen ({} Datei-Verweise).".format(nfiles))
                except Exception as exc:
                    self._case = None
                    self._say("AsterStudy-Fall nicht lesbar: {}".format(exc))
                try:
                    from beamcheck.smeshview import is_control_name

                    self._meshes = [
                        (name, mesh)
                        for name, mesh in list_smesh_meshes()
                        if not is_control_name(name)
                    ]
                except Exception as exc:
                    self._meshes = []
                    self._say("SMESH-Netze nicht gelistet: {}".format(exc))
            except Exception as exc:
                self._say(str(exc))
            self.mesh_choice.addItem("(automatisch bzw. Datei)", None)
            for index, (name, _mesh) in enumerate(self._meshes):
                self.mesh_choice.addItem(name, index)

        def _pick_comm(self):
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "comm-Datei", "", "Code_Aster (*.comm *.comm.orig *.txt);;Alle (*)"
            )
            if path:
                self.comm_path.setText(path)
                self.source.setCurrentIndex(1)

        def _pick_mesh(self):
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Netz", "", "Netz (*.med *.rmed *.mail *.msh *.dat);;Alle (*)"
            )
            if path:
                self.mesh_path.setText(path)

        def _say(self, text):
            self.log.appendPlainText(text)

        def _comm_text(self):
            if self.source.currentData() == "files":
                path = self.comm_path.text().strip()
                if not path:
                    raise CommError("Bitte eine comm-Datei wählen.")
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    return handle.read(), None
            from beamcheck.aster_access import current_case

            try:
                self._case = current_case()
            except Exception as exc:
                raise CommError("AsterStudy-Fall nicht lesbar: {}".format(exc))
            return self._case["text"], self._case.get("files") or []

        def _edges(self, parsed, file_refs):
            choice = self.mesh_choice.currentData()
            if choice is not None:
                _name, mesh = self._meshes[choice]
                return edges_from_smesh(mesh), "SMESH:" + _name
            # Liegt das Netz schon in der Studie, nicht noch einmal über
            # MEDLoader öffnen. Der Import aus dem Plugin-Thread stürzt ab.
            from beamcheck.control import resolve_edges

            return resolve_edges(
                parsed,
                file_refs,
                self._meshes,
                self.mesh_path.text().strip(),
            )

        def _run(self):
            self.log.clear()
            try:
                text, file_refs = self._comm_text()
                parsed = parse_comm(text)
                edges, origin = self._edges(parsed, file_refs)
                self._say("Netz: {} ({} Kanten).".format(origin, len(edges)))
                report = build_report(parsed, edges)
                from beamcheck.smeshview import publish

                notes = publish(
                    self.context,
                    report,
                    show_sections=self.sections.isChecked(),
                    show_axes=self.axes.isChecked(),
                    axis_fraction=float(self.fraction.value()),
                    solid=self.solid.isChecked(),
                    fit=self.fit.isChecked(),
                )
                self._say(report.summary())
                for note in notes:
                    self._say(note)
            except (CommError, MeshError) as exc:
                self._say(str(exc))
            except Exception:
                self._say(traceback.format_exc())

        def _clear(self):
            self.log.clear()
            try:
                from beamcheck.smeshview import clear

                for note in clear():
                    self._say(note)
            except Exception:
                self._say(traceback.format_exc())

    dialog = Dialog()
    runner = getattr(dialog, "exec", None) or getattr(dialog, "exec_")
    runner()
