# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware
"""Certification-stage dates are binary times (J3068/2 7.3.2, 7.3.16, 7.3.49).

56 bits, 1 s per bit from midnight, 1 January 1970, least significant byte
first; FExx... is Error and FFFF... is Not Available.  The GUI used to join
the bytes as text, which only worked for the ASCII placeholders the
reference sends ("abcdefg"); those are now shown as a number that is not a
calendar date, with the bytes as text.
"""
import pytest

from conftest import lin_frame

FIELDS = [(0x17, 13, "EvCertificationDate"), (0x17, 14, "EvUpdateTime"), (0x18, 3, "SeUpdateTimeEVSE")]


def _decoded(open_file, tmp_path, frame_id, page, seven):
    log = tmp_path / "date.bin"
    log.write_bytes(lin_frame(frame_id, [page] + list(seven)))
    g = open_file(log)
    assert g["frame_validity_map"] == {1: True}
    return {k: v[0] for k, v in g["current_op_data"].items()}


@pytest.mark.parametrize("frame_id,page,field", FIELDS, ids=[f[2] for f in FIELDS])
def test_date_fields(open_file, tmp_path, frame_id, page, field):
    secs = 1764115200  # 2025-11-26 00:00:00
    cases = [
        (secs.to_bytes(7, "little"), "2025-11-26 00:00:00"),
        (bytes([0x12] * 6 + [0xFE]), "Error"),
        (bytes([0xFF] * 7), "N/A"),
        (bytes([0] * 6 + [0xFC]), "Reserved"),
        (b"abcdefg", "not a calendar date"),
    ]
    for seven, expected in cases:
        value = _decoded(open_file, tmp_path, frame_id, page, seven)[field]
        assert expected in value, (seven, value)
    assert "abcdefg" in _decoded(open_file, tmp_path, frame_id, page, b"abcdefg")[field]
