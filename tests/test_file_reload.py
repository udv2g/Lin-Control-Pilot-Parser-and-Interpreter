# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware
"""Opening a file shows that file only, whatever was loaded before it."""
import os

import globals as gui_globals
from PyQt5.QtWidgets import QDialog

from conftest import TEST_FILES, lin_frame


def _state(g):
    return {
        "validity": dict(g["frame_validity_map"]),
        "frame_types": list(gui_globals.all_frame_types),
        "timestamps": dict(gui_globals.frame_timestamps),
        "recent": list(g["recent_frame_types"]),
        "total": g["total_frames"],
    }


def _recent_data_tab(g):
    g["open_debug_dialog"]()
    text = g["debug_dialog"].recent_data_edit.toPlainText()
    g["debug_dialog"].close()
    return text


def test_second_file_replaces_the_first(gui, open_file):
    second = os.path.join(TEST_FILES, "LIN-CP_emu_Log_Binary.log")  # no ID, ModeCtrl or J3072 frames

    gui["clear_all_data"](QDialog())
    alone = _state(open_file(second))

    open_file(os.path.join(TEST_FILES, "Test_FIle.log"))  # 990 frames, all frame types
    after = _state(open_file(second))

    assert after == alone
    assert sorted(after["validity"]) == list(range(1, 464))
    recent = _recent_data_tab(gui)
    for absent in ("EvID", "SeID", "EvModeCtrl", "EvJ3072", "SeTargets1"):
        assert f"{absent}\n0\n" in recent, f"Recent Data counts {absent} frames the file does not have"


def test_short_file_after_one_with_bad_frames(gui, open_file, tmp_path):
    open_file(os.path.join(TEST_FILES, "Cable_node_Ver_2_alter.txt"))  # 19 bad frames, up to frame 187
    log = tmp_path / "two.bin"
    log.write_bytes(lin_frame(0x02, [0xFF, 0x81, 0, 0, 2, 0xFF, 0xFF, 0xFF]) * 2)
    g = open_file(log)
    assert g["frame_validity_map"] == {1: True, 2: True}
    assert len(gui_globals.all_frame_types) == 2
