# globals.py

from PyQt5.QtCore import QTimer

#   Core variables for serial and live data
ser = None
live_data_log = []
auto_update = True
live_data_state = False
na_toggle_active = False


frame_time_active = False
all_frame_types = []
frame_timestamps = {}
live_data_start_time = 0

# Additional display widgets
task_operation_display = None
contactor_state_display = None
selected_protocol_version_display = None
sesupported_protocol_versions_display = None
ratings_display = None
seavailable_current_display = None
evpresent_current_display = None
evrequested_current_display = None
EvInfo_display = None
SeInfo_display = None
cable_Node_display = None
sleep_connection_display = None
control_page_display = None
OP252_control_page_display = None
EvModeCtrl_display = None
SeModeCtrl_display = None
SeTargets1_display = None
EvJ3072_tab_display = None
SeJ3072_tab_display = None

# Collapsible box widget globals
collapsible_task = None
collapsible_contactor_state = None
collapsible_selected_protocol_version = None
collapsible_sesupported_protocol_versions = None
collapsible_ratings = None
collapsible_seavailable_current = None
collapsible_evpresent_current = None
collapsible_evrequested_current = None
collapsible_EvInfo = None
collapsible_SeInfo = None
collapsible_cable_Node = None
collapsible_sleep_Connection = None
collapsible_control_page = None
collapsible_OP252_control_page = None
collapsible_EvModeCtrl  = None
collapsible_SeModeCtrl_page = None
collapsible_SeTargets1_page = None


# Constants
color_map = {
    "Incomplete": "orange",
    "Complete": "green",
    "Error": "red",
    "Not_Available": "#cfcfcf",
    "N/A": "#cfcfcf",
    "Deny_V": "red",
    "Permit_V": "green"
}

protocol_version_names = {
    1: "IEC 61851-1",
    2: "SAE J3068",
    3: "SAE J3068/1",
    252: "SAE J3068/2",
    253: "UD Advanced",
    255: "N/A"
}