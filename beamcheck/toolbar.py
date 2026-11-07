"""Beams toggle in the AsterStudy menu bar."""

from __future__ import annotations

import os

ACTION_ID = 19050
_BUTTON = "balkenkontrolle.toggle"
_state = {"on": None, "hooked": False, "busy": False}


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
        from PyQt5 import QtWidgets
    except ImportError:
        from PyQt6 import QtWidgets
    return QtWidgets


def _sg():
    try:
        from asterstudy.gui.salomegui_utils import get_salome_pyqt

        return get_salome_pyqt()
    except Exception:
        import SalomePyQt

        return SalomePyQt.SalomePyQt()


def _toolbars():
    QtWidgets = _qt()
    app = QtWidgets.QApplication.instance()
    if app is None:
        return []
    found = []
    for widget in app.topLevelWidgets():
        try:
            found.extend(widget.findChildren(QtWidgets.QToolBar))
        except Exception:
            continue
    return found


def _label(action):
    try:
        return action.text().replace("&", "").strip()
    except Exception:
        return ""


def _icon_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "beam.png")


def _menu_has(bar, action):
    if bar is None:
        return False
    try:
        actions = bar.actions()
    except Exception:
        return False
    for item in actions:
        if item is action or _label(item) in ("Beams", "Balken"):
            return True
        try:
            menu = item.menu()
        except Exception:
            menu = None
        if menu is None:
            continue
        for sub in menu.actions():
            if sub is action or _label(sub) in ("Beams", "Balken"):
                return True
    return False


def _on_commands_toolbar(action):
    for toolbar in _toolbars():
        name = ""
        try:
            name = toolbar.objectName() or ""
        except Exception:
            name = ""
        if "CommandsToolbar" not in name:
            continue
        try:
            if action in toolbar.actions():
                return True
        except Exception:
            continue
    return False


def _drop_legacy_buttons():
    """Entfernt die früher per addWidget gesetzten Doppelgänger."""
    QtWidgets = _qt()
    app = QtWidgets.QApplication.instance()
    if app is None:
        return
    for widget in app.allWidgets():
        if not isinstance(widget, QtWidgets.QToolButton):
            continue
        try:
            marked = widget.objectName() == _BUTTON
        except Exception:
            continue
        if not marked:
            continue
        parent = widget.parent()
        while parent is not None and not isinstance(parent, QtWidgets.QToolBar):
            parent = parent.parent()
        if isinstance(parent, QtWidgets.QToolBar):
            for item in list(parent.actions()):
                try:
                    if parent.widgetForAction(item) is widget:
                        parent.removeAction(item)
                except Exception:
                    continue
        try:
            widget.hide()
            widget.deleteLater()
        except Exception:
            pass


def _ensure_action(sg):
    action = None
    try:
        action = sg.action(ACTION_ID)
    except Exception:
        action = None
    tip = "Show or hide the beams of the active study"
    icon = _icon_path()
    if action is None:
        try:
            action = sg.createAction(ACTION_ID, "Beams", tip, tip, icon, 0, True)
        except TypeError:
            action = sg.createAction(ACTION_ID, "Beams", tip, tip, icon)
    action.setText("Beams")
    action.setToolTip(tip)
    action.setStatusTip(tip)
    action.setCheckable(True)
    try:
        from PyQt5.QtGui import QIcon
    except ImportError:
        from PyQt6.QtGui import QIcon
    if os.path.isfile(icon):
        action.setIcon(QIcon(icon))
    return action


def _on_toggled(checked):
    if _state.get("busy"):
        return
    _state["on"] = bool(checked)
    _state["busy"] = True
    try:
        if checked:
            from beamcheck.control import visualize_active

            visualize_active()
        else:
            from beamcheck.smeshview import clear

            clear()
    except Exception as exc:
        _state["on"] = False
        try:
            action = _ensure_action(_sg())
            action.blockSignals(True)
            action.setChecked(False)
            action.blockSignals(False)
        except Exception:
            pass
        if not _state.get("quiet"):
            _warn(str(exc))
    finally:
        _state["busy"] = False
        _state["quiet"] = False


def _warn(text):
    QtWidgets = _qt()
    QtWidgets.QMessageBox.warning(None, "Beam check", text)


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


def _hook(action):
    if _state.get("hooked"):
        return
    action.toggled.connect(_on_toggled)
    _state["hooked"] = True
    if _want_on() and not action.isChecked():
        _state["quiet"] = True
        action.setChecked(True)


def _aster_active(sg):
    try:
        return sg.getActiveComponent() == "ASTERSTUDY"
    except Exception:
        return False


def _on_any_toolbar(action):
    for toolbar in _toolbars():
        try:
            if action in toolbar.actions():
                return True
        except Exception:
            continue
    return False


def _try_install():
    sg = _sg()
    if not _aster_active(sg):
        return False
    action = _ensure_action(sg)
    _state["action"] = action
    _hook(action)
    try:
        bar = sg.getMainMenuBar()
    except Exception:
        bar = None
    if bar is not None:
        for item in list(bar.actions()):
            if _label(item) == "Balken":
                bar.removeAction(item)
        if not _menu_has(bar, action):
            bar.addAction(action)
    if not _state.get("tool_added") and not _on_any_toolbar(action):
        try:
            sg.createTool(ACTION_ID, "CommandsToolbar")
            _state["tool_added"] = True
        except Exception:
            pass
    return bar is not None and _menu_has(bar, action)


def _qt_core():
    try:
        from PyQt5 import QtCore
    except ImportError:
        from PyQt6 import QtCore
    return QtCore


def _retry(left):
    if left <= 0:
        return
    try:
        _try_install()
    except Exception:
        pass
    action = _state.get("action")
    if action is not None and _on_any_toolbar(action):
        try:
            if _menu_has(_sg().getMainMenuBar(), action):
                return
        except Exception:
            return
    _qt_core().QTimer.singleShot(700, lambda: _retry(left - 1))


def ensure_toolbar():
    """Setzt den Schalter in die Menüleiste, sobald AsterStudy aktiv ist."""
    try:
        _drop_legacy_buttons()
        _wrap_activate()
        if not _try_install():
            _retry(40)
    except Exception:
        pass


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
