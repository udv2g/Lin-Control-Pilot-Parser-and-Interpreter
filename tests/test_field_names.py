# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware
"""Fields are shown under the names their J3068/1 clause 6.1 definitions use.

J3068/1 Table 5 and the 6.1.56 heading print three names with a capital
"EV" (EVTimeToEnergy, EVTimeToEnergyForDept, EVTimeToRange) where the field
rows of 6.1.55-6.1.57 write "Ev"; the GUI had copied them as "EvEV...".  It
also spelled EvHVESSDschCapacity (6.1.23) "EvHVESSDishargeCapacity".
"""
import glob
import os

from conftest import REPO, lin_frame

OLD = ["EvEVTimeToEnergy", "EvEVTimeToEnergyForDept", "EvEVTimeToRange", "EvHVESSDishargeCapacity"]
NEW = ["EvTimeToEnergy", "EvTimeToEnergyForDept", "EvTimeToRange", "EvHVESSDschCapacity"]


def test_old_spellings_are_gone():
    for path in glob.glob(os.path.join(REPO, "*.py")):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for name in OLD:
            assert name not in text, f"{name} still in {os.path.basename(path)}"


def test_data_tab_uses_standard_names(gui, open_file, tmp_path):
    log = tmp_path / "evdata.bin"
    log.write_bytes(lin_frame(0x0F, [99, 0x10, 0x27, 0x00, 0, 0, 0, 0])      # EvHVESSDschCapacity 10000
                    + lin_frame(0x0F, [101, 0, 0, 0, 0, 30, 0, 0])            # EvTimeToEnergyForDept 30 min
                    + lin_frame(0x0F, [103, 0, 45, 0, 60, 0, 0, 0]))          # EvTimeToRange 45, EvTimeToEnergy 60
    g = open_file(log)
    op = g["current_op_data"]
    assert op["EvTimeToEnergyForDept"][0] == "30 min"
    assert op["EvTimeToRange"][0] == "45 min"
    assert op["EvTimeToEnergy"][0] == "60 min"
    assert "EvHVESSDschCapacity" in op
    g["refresh_all_displays"](g["slider"].value())
    tab = g["ev_data_tab_display"].toPlainText()
    for name in NEW:
        assert name in tab, f"{name} missing from the Ev Data tab"
