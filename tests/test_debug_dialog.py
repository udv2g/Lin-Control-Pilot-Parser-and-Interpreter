# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware
"""The debug dialog listens to the slider once while open, and not at all once closed."""
import os

from PyQt5.QtCore import QCoreApplication, QEvent

from conftest import TEST_FILES


def _listeners(g):
    slider = g["slider"]
    return slider.receivers(slider.valueChanged)


def _flush_deletes():
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_one_connection_while_open_none_after_close(gui, open_file):
    open_file(os.path.join(TEST_FILES, "Test_FIle.log"))
    base = _listeners(gui)

    for close in ("close", "reject", "close_button"):
        gui["open_debug_dialog"]()
        dialog = gui["debug_dialog"]
        assert _listeners(gui) == base + 1
        {"close": dialog.close,
         "reject": dialog.reject,  # Esc
         "close_button": dialog.close_button.click}[close]()
        _flush_deletes()
        assert _listeners(gui) == base, f"still connected after {close}"

    for _ in range(5):
        gui["open_debug_dialog"]()
        gui["debug_dialog"].close()
    _flush_deletes()
    assert _listeners(gui) == base


def test_recent_data_follows_the_slider_while_open(gui, open_file):
    open_file(os.path.join(TEST_FILES, "Test_FIle.log"))
    gui["open_debug_dialog"]()
    dialog = gui["debug_dialog"]
    gui["slider"].setValue(1)
    at_start = dialog.recent_data_edit.toPlainText()
    gui["slider"].setValue(gui["slider"].maximum())
    assert dialog.recent_data_edit.toPlainText() != at_start
    dialog.close()
