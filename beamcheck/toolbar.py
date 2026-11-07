"""Schalter in der Befehlsleiste von AsterStudy, rechts neben den Stufen."""

from __future__ import annotations

_BUTTON = "balkenkontrolle.toggle"
_state = {"on": None}


def select_toolbar(items):
    """``items`` sind ``(object_name, combo_count, toolbar)``.

    Gesucht ist die Leiste ``CommandsToolbar``. Sonst die mit den meisten
    Klappfeldern, aber nicht die Operationsleiste.
    """
    for name, _count, toolbar in items:
        if "CommandsToolbar" in (name or ""):
            return toolbar
    pool = [
        (count, toolbar)
        for name, count, toolbar in items
        if "OperationsToolbar" not in (name or "") and count > 0
    ]
    if not pool:
        return None
    pool.sort(key=lambda item: -item[0])
    return pool[0][1]


def _qt():
    try:
        from PyQt5 import QtCore, QtWidgets
    except ImportError:
        from PyQt6 import QtCore, QtWidgets
    return QtCore, QtWidgets


def _toolbars():
    QtCore, QtWidgets = _qt()
    app = QtWidgets.QApplication.instance()
    if app is None:
        return []
    found = []
    for widget in app.topLevelWidgets():
        try:
            bars = widget.findChildren(QtWidgets.QToolBar)
        except Exception:
            continue
        found.extend(bars)
    return found


def _existing_button():
    QtCore, QtWidgets = _qt()
    for toolbar in _toolbars():
        for button in toolbar.findChildren(QtWidgets.QToolButton):
            if button.objectName() == _BUTTON:
                return button
    return None


def _on_toggled(checked):
    _state["on"] = bool(checked)
    button = _existing_button()
    if button is not None:
        button.blockSignals(True)
    try:
        if checked:
            from beamcheck.control import visualize_active

            visualize_active()
        else:
            from beamcheck.smeshview import clear

            clear()
    except Exception as exc:
        _state["on"] = False
        if button is not None:
            button.setChecked(False)
        if not _state.get("quiet"):
            _warn(str(exc))
    finally:
        _state["quiet"] = False
        if button is not None:
            button.blockSignals(False)


def _warn(text):
    _QtCore, QtWidgets = _qt()
    QtWidgets.QMessageBox.warning(None, "Balkenkontrolle", text)


def _want_on():
    if _state["on"] is not None:
        return bool(_state["on"])
    try:
        from beamcheck.aster_access import current_case
        from beamcheck.parser import parse_comm

        parsed = parse_comm(current_case()["text"])
    except Exception:
        return False
    return bool(parsed.beam_groups or parsed.all_edges_are_beams or parsed.sections)


def _try_install():
    if _existing_button() is not None:
        return True
    items = []
    for toolbar in _toolbars():
        try:
            name = toolbar.objectName() or ""
        except Exception:
            name = ""
        try:
            from PyQt5.QtWidgets import QComboBox
        except ImportError:
            from PyQt6.QtWidgets import QComboBox
        try:
            count = len(toolbar.findChildren(QComboBox))
        except Exception:
            count = 0
        items.append((name, count, toolbar))
    toolbar = select_toolbar(items)
    if toolbar is None:
        return False
    _QtCore, QtWidgets = _qt()
    button = QtWidgets.QToolButton(toolbar)
    button.setObjectName(_BUTTON)
    button.setText("Balken")
    button.setToolTip("Balken der aktiven Studie ein- oder ausblenden")
    button.setCheckable(True)
    button.setAutoRaise(True)
    try:
        button.setToolButtonStyle(_QtCore.Qt.ToolButtonTextOnly)
    except Exception:
        pass
    toolbar.addSeparator()
    toolbar.addWidget(button)
    button.toggled.connect(_on_toggled)
    if _want_on():
        _state["quiet"] = True
        button.setChecked(True)
    return True


def _wrap_activate():
    try:
        import ASTERSTUDYGUI
    except ImportError:
        return
    current = getattr(ASTERSTUDYGUI, "activate", None)
    if not callable(current) or getattr(current, "_balkenkontrolle", False):
        return

    def wrapped(*args, **kwargs):
        result = current(*args, **kwargs)
        try:
            _try_install()
        except Exception:
            pass
        return result

    wrapped._balkenkontrolle = True
    ASTERSTUDYGUI.activate = wrapped


def _retry(left):
    if _existing_button() is not None or left <= 0:
        return
    try:
        _try_install()
    except Exception:
        pass
    if _existing_button() is not None:
        return
    QtCore, _QtWidgets = _qt()
    QtCore.QTimer.singleShot(700, lambda: _retry(left - 1))


def ensure_toolbar():
    """Hängt den Schalter an, sobald die Befehlsleiste existiert."""
    try:
        _wrap_activate()
        if not _try_install():
            _retry(12)
    except Exception:
        pass
