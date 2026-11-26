# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware
"""The EvID/SeID CRC-32 check works with the standard library alone."""
import os
import sys

import pytest

from conftest import TEST_FILES, lin_frame
from data_processing import crc_check


def test_crc32_check_value(monkeypatch):
    monkeypatch.setitem(sys.modules, "crc", None)  # the third-party package must not be needed
    # 0xCBF43926 is the published CRC-32 check value for the ASCII string "123456789"
    assert crc_check(0xCBF43926, bytearray(b"123456789")) == (True, 0xCBF43926)
    assert crc_check(0x00000000, bytearray(b"123456789")) == (False, 0xCBF43926)


def test_gui_checks_crc32_pages(open_file, monkeypatch):
    monkeypatch.setitem(sys.modules, "crc", None)
    g = open_file(os.path.join(TEST_FILES, "CRC32_Match_test.log"))
    text = g["result_display"].toPlainText()
    assert "Error processing frame" not in text
    # The two ID-stage cycles match.  Every Data-stage CRC in this log is wrong at the
    # sender: it never restarts its CRC at the Data-stage control page, so its CRC grows
    # with each cycle.  Counted per cycle (J3068/1 7.3.1.1), all eight mismatch.
    assert text.count("CRC Check: MATCH") == 2
    assert text.count("CRC Check: MISMATCH") == 8
    assert not any(v is False for k, v in g["frame_validity_map"].items() if k <= g["total_frames"])


def _crc_page(frame_id, pages):
    """CRC page 251 for the given pages: CRC-32 over page number + 7 bytes of each, in order."""
    import zlib
    crc = zlib.crc32(b"".join(bytes([p] + d) for p, d in pages)) & 0xFFFFFFFF
    return lin_frame(frame_id, [251] + list(crc.to_bytes(4, "little")) + [0xFF] * 3)


@pytest.mark.parametrize("frame_id", [0x0F, 0x10], ids=["EvID", "SeID"])
def test_crc_covers_one_cycle_from_the_control_page(open_file, tmp_path, frame_id):
    # J3068/1 3.13 and 7.3.1.1: a cycle starts at the control page; the CRC covers the pages
    # after it (page numbers included) up to the CRC page.  Pages sent before the control
    # page, with no CRC page of their own, belong to no cycle.
    control = lin_frame(frame_id, [0, 3, 2, 97, 98, 0x11, 0xFF, 0xFF])
    leftover = [(1, [0x41] * 7), (2, [0x42] * 7)]
    cycle = [(97, [1, 2, 3, 4, 5, 6, 7]), (98, [8, 9, 10, 11, 12, 13, 14])]
    log = tmp_path / "cycle.bin"
    log.write_bytes(b"".join(lin_frame(frame_id, [p] + d) for p, d in leftover)
                    + control + b"".join(lin_frame(frame_id, [p] + d) for p, d in cycle)
                    + _crc_page(frame_id, cycle))
    g = open_file(log)
    text = g["result_display"].toPlainText()
    assert text.count("CRC Check: MATCH") == 1 and "MISMATCH" not in text, text[-600:]


def test_log_from_a_per_cycle_sender_matches_every_crc(open_file):
    # Recorded from the saej3068-emulator slash2 build that restarts its CRC at every
    # control page: every EvID and SeID CRC page, ID and Data stages, matches.
    g = open_file(os.path.join(TEST_FILES, "CRC32_Match_test_fixed_emulator.log"))
    text = g["result_display"].toPlainText()
    assert "Error processing frame" not in text
    assert text.count("CRC Check: MATCH") == 62
    assert "CRC Check: MISMATCH" not in text
    assert not any(v is False for v in g["frame_validity_map"].values())
