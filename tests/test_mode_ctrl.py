# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware
"""Grid-code fields of EvModeCtrl (frame 21) and SeModeCtrl (frame 22), J3068/2 Table 2.

Frame 21: bit 0 EvGridCodeStatusMod, bits 1-15 the 15-bit EvGridCodeStatus.
Frame 22: bit 0 reserved, bits 1-15 the 15-bit SeGridCodeRequest.  The
printed frame-22 row gives "bits 2-15", 14 bits for a 15-bit signal; that is
a known misprint, and the reference LDF, like frame 21, uses bits 1-15.
"""
import os

import pytest

from conftest import TEST_FILES, lin_frame


def _op_data(open_file, tmp_path, frame_id, raw16):
    log = tmp_path / "modectrl.bin"
    log.write_bytes(lin_frame(frame_id, [raw16 & 0xFF, raw16 >> 8, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]))
    g = open_file(log)
    assert g["frame_validity_map"] == {1: True}
    return {k: v[0] for k, v in g["current_op_data"].items()}


@pytest.mark.parametrize("status,mod,status_text,mod_text", [
    (0x0001, 0, "Basic V2G settings A configured", "Modified"),
    (0x0004, 1, "IEEE 1547-2018/UL 1741-SB defaults configured", "Unmodified/Not Configured"),
    (0x7000, 0, "Manufacturer-defined (7000)", "Modified"),
    (0x7FFF, 1, "Unconfigured (start value)", "Unmodified/Not Configured"),
])
def test_ev_grid_code_status(open_file, tmp_path, status, mod, status_text, mod_text):
    data = _op_data(open_file, tmp_path, 0x15, (status << 1) | mod)
    assert data["EvGridCodeStatus"] == status_text
    assert data["EvGridCodeStatusMod"] == mod_text


@pytest.mark.parametrize("req,text", [
    (0x0001, "Request basic V2G settings A"),
    (0x0004, "Request IEEE 1547-2018/UL 1741-SB defaults"),
    (0x7FFE, "Error"),
    (0x7FFF, "No request, follow SunSpec"),
])
def test_se_grid_code_request(open_file, tmp_path, req, text):
    data = _op_data(open_file, tmp_path, 0x16, (req << 1) | 1)  # bit 0 reserved, sent as 1
    assert data["SeGridCodeRequest"] == text


def test_emulator_log_shows_no_request(open_file):
    # every SeModeCtrl in this log carries FFFF: no request (7FFF) in bits 1-15
    g = open_file(os.path.join(TEST_FILES, "-2_testlog_emu.log"))
    assert g["current_op_data"]["SeGridCodeRequest"][0] == "No request, follow SunSpec"
    assert g["current_op_data"]["EvGridCodeStatus"][0] == "Unconfigured (start value)"
