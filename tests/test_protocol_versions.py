# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware
"""Protocol versions the parts of the series define are named.

The base document lists 3-239 as reserved without mentioning that J3068/1
defines 3 and 103 (Appendix A: J3068/1 plus proprietary data) and J3068/2
defines 252.  The GUI named 3 and 252 but showed 103 as a bare number.
"""
import globals as gui_globals

from conftest import lin_frame


def test_defined_versions_have_names():
    for version in (2, 3, 103, 252):
        assert gui_globals.protocol_version_names.get(version), version


def test_selected_version_103_is_named(gui, open_file, tmp_path):
    log = tmp_path / "pv103.bin"
    log.write_bytes(lin_frame(0x00, [103, 0xFF, 0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])    # SeVersionList
                    + lin_frame(0x01, [103, 0xFF, 0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]))  # EvVersionList
    g = open_file(log)
    g["refresh_all_displays"](g["slider"].value())
    header = gui_globals.collapsible_selected_protocol_version.label_header.text()
    assert "103 (SAE J3068/1 + proprietary data)" in header, header


def _version_lists(open_file, tmp_path, selected, supported):
    log = tmp_path / "versions.bin"
    log.write_bytes(lin_frame(0x00, [selected, 0xFF, 0] + supported)
                    + lin_frame(0x01, [selected, 0xFF, 0] + supported))
    g = open_file(log)
    assert g["frame_validity_map"] == {1: True, 2: True}
    g["refresh_all_displays"](g["slider"].value())
    return g


def test_selected_version_254_is_a_version_not_an_error(open_file, tmp_path):
    # base 8.3.15 / 8.3.29: any value 0-254 may be selected; only FF is Not Available
    g = _version_lists(open_file, tmp_path, 254, [2, 0xFF, 0xFF, 0xFF, 0xFF])
    ver = {k: v[0] for k, v in g["current_ver_data"].items()}
    assert ver["SeSelectedVersion_SeVersionList"] == "254"
    assert ver["EvSelectedVersion_EvVersionList"] == "254"


def test_supported_versions_are_labelled_by_the_series(open_file, tmp_path):
    # base 8.3.19 / 8.3.33: 0-2 defined, 3-239 reserved, 240-253 experimental, 254 reserved;
    # J3068/1 defines 3 and 103, J3068/2 defines 252
    g = _version_lists(open_file, tmp_path, 2, [3, 252, 254, 7, 245])
    widget = g["sesupported_protocol_versions_display"]
    text = widget.toPlainText()
    for label in ("3 (SAE J3068/1)", "252 (SAE J3068/2)", "254 (Reserved)", "7 (Reserved)", "245 (Experimental)"):
        assert label in text, (label, text)
    assert "color:red" not in widget.toHtml().split("254 (Reserved)")[0][-80:]
