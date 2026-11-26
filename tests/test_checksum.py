# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware
"""LIN checksum: add with carry, then invert; enhanced (PID included) except the classic ids 60 and 61.

The reference is conftest.lin_checksum, a closed form of the same sum.  The
receiver's test (everything including the checksum adds to 0xFF) is not
enough on its own: when PID and data add to exactly 0xFF it accepts both 0x00
and 0xFF, but a sender always puts 0x00 on the wire, so a decoder that
computes 0xFF and compares rejects a good frame.
"""
import os
import random

import pytest

from conftest import TEST_FILES, lin_checksum, lin_frame
from data_processing import compute_lin_enhanced_checksum


@pytest.mark.parametrize("frame_id", range(62))
def test_checksum_matches_the_sender(frame_id):
    rng = random.Random(frame_id)
    cases = [[rng.randrange(256) for _ in range(8)] for _ in range(2000)]
    cases += [[0] * 8, [0xFF] * 8]
    for data in cases:
        checksum, pid = compute_lin_enhanced_checksum(frame_id, data)
        start = 0 if frame_id in (60, 61) else pid
        assert checksum == lin_checksum(start, data), (frame_id, data, checksum)


def test_sum_of_0xff_gives_checksum_0x00():
    # SeStatus frame 22 of Test_Files/Cable_node_Ver_2_alter.txt: 00 55 42 02 8B 18 FF FF 18 FF FF 00
    checksum, pid = compute_lin_enhanced_checksum(0x02, [0x02, 0x8B, 0x18, 0xFF, 0xFF, 0x18, 0xFF, 0xFF])
    assert (pid, checksum) == (0x42, 0x00)


def test_go_to_sleep_uses_classic_checksum():
    checksum, pid = compute_lin_enhanced_checksum(60, [0x00] + [0xFF] * 7)
    assert (pid, checksum) == (0x3C, 0x00)


def test_gui_accepts_frames_whose_sum_is_0xff(open_file):
    g = open_file(os.path.join(TEST_FILES, "Cable_node_Ver_2_alter.txt"))
    validity = g["frame_validity_map"]
    assert validity[22] and validity[26]
    # the file's other 19 bad frames really do carry a wrong checksum
    assert sum(1 for k, v in validity.items() if k <= g["total_frames"] and not v) == 19


def test_gui_accepts_go_to_sleep(open_file, tmp_path):
    log = tmp_path / "gts.bin"
    log.write_bytes(lin_frame(0x02, [0xFF, 0x81, 0x00, 0x00, 0x02, 0xFF, 0xFF, 0xFF])
                    + lin_frame(60, [0x00] + [0xFF] * 7))
    g = open_file(log)
    assert g["total_frames"] == 2
    assert g["frame_validity_map"][2] is True
