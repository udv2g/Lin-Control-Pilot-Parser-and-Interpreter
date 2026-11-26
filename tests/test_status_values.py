# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware
"""The Ver/Init/Op status fields decode every value, including Op = Not Available.

Base document 8.3.17 and 8.3.31: xxStatusOp is 0 Deny_V, 1 Permit_V,
2 Error, 3 Not Available (the EV's start value).  The decoder's table had
no entry for Op = 3, so any version-list or status frame carrying it raised
"list index out of range" and was marked invalid.
"""
import pytest

from conftest import lin_frame

OP = {0: "Deny_V", 1: "Permit_V", 2: "Error", 3: "N/A"}
VER_INIT = {0: "Incomplete", 1: "Complete", 2: "Error", 3: "N/A"}


@pytest.mark.parametrize("frame_id,prefix", [(0x00, "Se"), (0x01, "Ev"), (0x02, "Se"), (0x03, "Ev")],
                         ids=["SeVersionList", "EvVersionList", "SeStatus", "EvStatus"])
@pytest.mark.parametrize("op", sorted(OP))
def test_status_byte_decodes(open_file, tmp_path, frame_id, prefix, op):
    ver, init = 1, 3
    d1 = 0x80 | (op << 5) | (init << 3) | (ver << 1)
    log = tmp_path / "status.bin"
    log.write_bytes(lin_frame(frame_id, [2, d1, 0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]))
    g = open_file(log)
    assert g["frame_validity_map"] == {1: True}
    assert "Error processing frame" not in g["result_display"].toPlainText()
    ver_data = {k: v[0] for k, v in g["current_ver_data"].items()}
    assert ver_data[prefix + "StatusOp"] == OP[op]
    assert ver_data[prefix + "StatusInit"] == VER_INIT[init]
    assert ver_data[prefix + "StatusVer"] == VER_INIT[ver]
