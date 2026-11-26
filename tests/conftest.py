# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware
"""Headless fixtures for the LIN-CP GUI tests.

main.py builds its window when it is run and ends with sys.exit(app.exec_()).
The `gui` fixture runs it once per test session on Qt's offscreen platform,
with the event loop replaced by a no-op, and hands back the module's globals,
so tests drive the same functions the buttons call.  No serial port is opened.
"""
import os
import runpy
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_FILES = os.path.join(REPO, "Test_Files")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if REPO not in sys.path:
    sys.path.insert(0, REPO)


@pytest.fixture(scope="session")
def gui(tmp_path_factory):
    """main.py's globals.  It is started from a directory other than the repository."""
    from PyQt5.QtWidgets import QApplication

    captured = {}

    def no_event_loop(*_args):
        frame = sys._getframe(1)
        while "window" not in frame.f_globals:
            frame = frame.f_back
        captured["globals"] = frame.f_globals
        return 0

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(QApplication, "exec_", staticmethod(no_event_loop))
        mp.setattr(sys, "argv", [os.path.join(REPO, "main.py")])
        mp.chdir(tmp_path_factory.mktemp("elsewhere"))
        try:
            runpy.run_path(os.path.join(REPO, "main.py"), run_name="__main__")
        except SystemExit:
            pass
    return captured["globals"]


@pytest.fixture
def open_file(gui, monkeypatch):
    """Load a file through the real File button handler, accepting the guessed format."""
    from PyQt5.QtWidgets import QDialog, QFileDialog

    monkeypatch.setattr(gui["FormatSelectionDialog"], "exec_", lambda self: QDialog.Accepted)

    def _open(path):
        monkeypatch.setattr(QFileDialog, "getOpenFileName",
                            staticmethod(lambda *a, **k: (str(path), "")))
        gui["open_file_dialog"]()
        return gui

    return _open


def lin_frame(frame_id, data):
    """One 12-byte LIN-Tool record (break, sync, PID, 8 data bytes, checksum) for a frame.

    Built independently of data_processing: the checksum is chosen so that the
    receiver's test holds -- PID (or 0 for the classic ids 60 and 61), the data
    and the checksum added with carry give 0xFF.
    """
    bits = [(frame_id >> i) & 1 for i in range(6)]
    p0 = bits[0] ^ bits[1] ^ bits[2] ^ bits[4]
    p1 = 1 - (bits[1] ^ bits[3] ^ bits[4] ^ bits[5])
    pid = (p1 << 7) | (p0 << 6) | frame_id
    data = list(data)
    for ck in range(256):
        total = 0 if frame_id in (60, 61) else pid
        for b in data + [ck]:
            total += b
            if total > 0xFF:
                total -= 0xFF
        if total == 0xFF:
            return bytes([0x00, 0x55, pid] + data + [ck])
    raise AssertionError("no checksum closes the frame")
