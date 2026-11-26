# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware
"""The loading animation stops, and its dialog goes away, once a file is parsed."""
import os

from PyQt5.QtCore import QCoreApplication, QEvent
from PyQt5.QtGui import QMovie

from conftest import TEST_FILES


def test_no_loading_animation_left_running(gui, open_file):
    path = os.path.join(TEST_FILES, "LIN-CP_emu_Log_Binary.log")
    for _ in range(3):
        open_file(path)
    dialogs = gui["window"].findChildren(gui["LoadingDialog"])
    assert not [d for d in dialogs if d.movie.state() == QMovie.Running]
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert not gui["window"].findChildren(gui["LoadingDialog"])
