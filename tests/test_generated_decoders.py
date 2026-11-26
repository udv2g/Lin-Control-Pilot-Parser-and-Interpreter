# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware
"""Generated field decoders give each special value the meaning the standard gives it.

Most numeric fields of J3068/1 clause 6.1 and J3068/2 clause 7.3 reserve the
top values: all ones is Not Available, 0xFE (0xFExx, ...) is Error, and the
generated decoders call 0xFB-0xFD Reserved.  The generated chains tested the
N/A value twice, so Error was unreachable.  A few fields are not numbers of
that kind and are checked one by one below: a 7-bit count with its own top
codes (6.1.33), a count with no Error value (7.3.14), a count with a
"subsequent DTC" code (6.1.43), the grid-code lists (7.3.15) and the
power-control mode bitmasks (7.3.13, 7.3.48).
"""
import ast
import os

import pytest

from conftest import REPO, lin_frame


def test_no_if_elif_repeats_its_condition():
    with open(os.path.join(REPO, "main.py"), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    repeated = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
            if ast.unparse(node.test) == ast.unparse(node.orelse[0].test):
                repeated.append(node.orelse[0].lineno)
    assert not repeated, f"elif repeats the if above it at lines {repeated}"


def _le(value, n):
    return [(value >> (8 * i)) & 0xFF for i in range(n)]


# (frame id, page, field, function building data bytes 1..7 from a value, width in bytes)
FIELDS = [
    (0x0F, 104, "EvHVESSHealth", lambda v: [0] * 4 + [v] + [0] * 2, 1),
    (0x17, 7, "EvAvarMaxRtg", lambda v: _le(v, 2) + [0] * 5, 2),
    (0x0F, 99, "EvHVESSDschCapacity", lambda v: _le(v, 3) + [0] * 4, 3),
    (0x0F, 97, "EvOdometer", lambda v: _le(v, 4) + [0] * 3, 4),
]


def _decoded(open_file, tmp_path, frame_id, page, rest):
    log = tmp_path / "field.bin"
    log.write_bytes(lin_frame(frame_id, [page] + rest))
    g = open_file(log)
    assert g["frame_validity_map"] == {1: True}
    return g["current_op_data"]


@pytest.mark.parametrize("frame_id,page,field,build,width", FIELDS, ids=[f[2] for f in FIELDS])
def test_na_error_reserved(open_file, tmp_path, frame_id, page, field, build, width):
    shift = 8 * (width - 1)
    for top_byte, expected in ((0xFF, "N/A"), (0xFE, "Error"), (0xFB, "Reserved")):
        data = _decoded(open_file, tmp_path, frame_id, page, build(top_byte << shift))
        assert data[field][0].startswith(expected), (hex(top_byte << shift), data[field][0])


def _check(open_file, tmp_path, frame_id, page, build, field, cases):
    for value, expected in cases:
        data = _decoded(open_file, tmp_path, frame_id, page, build(value))
        assert data[field][0].strip().startswith(expected), (field, hex(value), data[field][0])


def test_dtc_count_top_codes(open_file, tmp_path):
    # 6.1.33: a 7-bit count 0-125, then "more than 125" and Not Available; no Error value
    _check(open_file, tmp_path, 0x0F, 98, lambda v: [0] * 6 + [v << 1], "EvJ2012DtcCount",
           [(0x7F, "N/A"), (0x7E, "More than 125"), (0x05, "5 count")])


def test_remaining_grid_codes_has_no_error_value(open_file, tmp_path):
    # 7.3.14: a count 0-250; FF Not Available (no further codes); nothing else is defined
    _check(open_file, tmp_path, 0x17, 4, lambda v: [0] * 6 + [v], "EvRemGridCode",
           [(0xFF, "N/A"), (0xFE, "Reserved 0xFE"), (0xFB, "Reserved 0xFB"), (0x05, "5 count")])


def test_number_of_dtcs_subsequent_code(open_file, tmp_path):
    # 6.1.43: FB marks a subsequent DTC, FE Error, FF Not Available
    _check(open_file, tmp_path, 0x0F, 98, lambda v: [v] + [0] * 6, "EvNumberJ2012Dtcs",
           [(0xFB, "Subsequent DTC"), (0xFE, "Error"), (0xFF, "N/A"), (0xFC, "Reserved 0xFC"), (3, "3 count")])


def test_supported_grid_codes(open_file, tmp_path):
    # 7.3.15: 0001-0004 and 7000-7FFA are codes; 7FFF and FFFF are Not Available (unused); no Error value
    _check(open_file, tmp_path, 0x17, 1, lambda v: [0, 0] + _le(v, 2) + [0] * 3, "EvSupGridCode1",
           [(0x0004, "0x0004"), (0x7000, "0x7000"), (0x7FFA, "0x7FFA"), (0x7FFF, "N/A"), (0xFFFF, "N/A"),
            (0xFE00, "Reserved 0xFE00"), (0x0005, "Reserved 0x0005")])


@pytest.mark.parametrize("frame_id,field", [(0x17, "EvPwrCtrlModesSpt"), (0x18, "SePwrCtrlModesSpt")])
def test_mode_bitmasks_are_shown_as_masks(open_file, tmp_path, frame_id, field):
    # 7.3.13 / 7.3.48: one bit per supported mode; no value of the mask means N/A or Error
    _check(open_file, tmp_path, frame_id, 1, lambda v: _le(v, 2) + [0] * 5, field,
           [(0x0E00, "0x0E00"), (0xFE00, "0xFE00"), (0xFF0A, "0xFF0A")])


def test_power_pages_111_112(open_file, tmp_path):
    # J3068/2 Table 8, 7.1.1-7.1.4: EV data pages 111 and 112 (Protocol Version 252 sessions),
    # 2 bytes each at 0.05 kW or kVA per bit, with the general N/A / Error / Reserved values
    for page, (first, second), unit in ((111, ("EvCurWattCharge", "EvCurWattDischarge"), "kW"),
                                         (112, ("EvCurVarAbsorb", "EvCurVarSupply"), "kVA")):
        data = _decoded(open_file, tmp_path, 0x0F, page, _le(200, 2) + _le(0xFE00, 2) + [0xFF] * 3)
        assert data[first][0] == f"10.000 {unit}", data[first][0]
        assert data[second][0] == "Error"
