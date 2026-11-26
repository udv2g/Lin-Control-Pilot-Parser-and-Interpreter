# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware
"""The GUI starts headless and every bundled log loads through the File button path."""
import os

import pytest

from conftest import TEST_FILES

FRAME_COUNTS = {
    "-1_livedata.log": 2120,
    "-2_testlog_emu.log": 1350,
    "3p-1p_test.log": 1086,
    "CRC32_Match_test.log": 1026,
    "Cable_node_Ver_2_alter.txt": 193,
    "LIN-CP_emu_Log_Binary.log": 463,
    "Test_FIle.log": 990,
}


def test_window_starts(gui):
    assert gui["window"].windowTitle() == "LIN_GUI"


@pytest.mark.parametrize("name", sorted(FRAME_COUNTS))
def test_bundled_log_loads(open_file, name):
    g = open_file(os.path.join(TEST_FILES, name))
    assert g["total_frames"] == FRAME_COUNTS[name]
    assert g["slider"].maximum() == FRAME_COUNTS[name]
    assert g["window"].windowTitle() == f"LIN_GUI - {name}"
