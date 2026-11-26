# Copyright (c) 2026, Systems and Standards Group, Institute of Energy Conversion, University of Delaware
"""Currents and voltages of the base frames, base document 8.3.

Every current table (8.3.6, 8.3.9, 8.3.12, 8.3.13, 8.3.21, 8.3.26): 0-250 A
at 1 A per bit, 251-254 Reserved, FF Not Available; there is no Error value.
Voltages (8.3.7, 8.3.8, 8.3.10, 8.3.11, 8.3.27, 8.3.28): 0-10000 at 0.1 V
per bit and FFFF Not Available, so 254.0 V and 255.0 V are ordinary values.
"""
from conftest import lin_frame
from data_processing import format_amp_value, format_voltage_value


def test_current_values():
    assert format_amp_value(0) == "0A"
    assert format_amp_value(250) == "250A"
    for raw in (251, 252, 253, 254):
        assert "Reserved" in format_amp_value(raw) and "error" not in format_amp_value(raw).lower(), raw
    assert "N/A" in format_amp_value(255)


def test_voltage_values():
    assert format_voltage_value(254.0) == "254.0V"
    assert format_voltage_value(255.0) == "255.0V"
    assert format_voltage_value(1000.0) == "1000.0V"
    assert "Reserved" in format_voltage_value(1000.1)
    assert "N/A" in format_voltage_value(6553.5)


def test_present_currents_frame(open_file, tmp_path):
    log = tmp_path / "currents.bin"
    log.write_bytes(lin_frame(0x04, [2, 16, 251, 254, 255, 0xFF, 0xFF, 0xFF]))  # EvPresentCurrents L1-L3, N
    g = open_file(log)
    op = {k: v[0] for k, v in g["current_op_data"].items()}
    assert op["EvOpPresentCurrent_L1"] == "16A"
    assert "Reserved" in op["EvOpPresentCurrent_L2"] and "Reserved" in op["EvOpPresentCurrent_L3"]
    assert "N/A" in op["EvOpPresentCurrent_N"]


def test_nominal_voltages_frame(open_file, tmp_path):
    log = tmp_path / "voltages.bin"
    l1n, ll = 2540, 2550  # 254.0 V and 255.0 V
    log.write_bytes(lin_frame(0x05, [2, l1n & 0xFF, l1n >> 8, ll & 0xFF, ll >> 8, 2, 0xFF, 0xFF]))
    g = open_file(log)
    init = {k: v[0] for k, v in g["current_init_data"].items()}
    assert init["SeNomVoltageL1N"] == "254.0V"
    assert init["SeNomVoltageLL"] == "255.0V"
