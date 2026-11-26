# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware
"""Images load however the GUI is started (the `gui` fixture starts it from a temporary directory)."""
import os

import pytest

BUTTONS = ["file_button", "debug_button", "live_data_button", "frame_time_toggle_button",
           "reset_time_button", "NA_toggle", "save_log_button", "trash_button",
           "Left_one", "Right_one", "Start_skip", "End_skip"]


@pytest.mark.parametrize("name", BUTTONS)
def test_button_icon_loaded(gui, name):
    assert gui[name].icon().availableSizes(), f"{name} has no icon image"


def test_resource_path_ignores_working_directory(gui, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for image in ("images/UD_logo.png", "images/twiggy-loading.gif"):
        assert os.path.isfile(gui["resource_path"](image)), image
