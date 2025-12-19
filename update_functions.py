import re
from data_processing import format_frame
import globals


#   Redefine global names to match function call
color_map = globals.color_map
protocol_version_names = globals.protocol_version_names

def color_if_na(label, value):
    if value == "N/A":
        return f"{label}: <span style='color:#cfcfcf;'>{value}</span>"
    else:
        return f"{label}: {value}"

def colorize_if_needed(text_value):
    color = color_map.get(text_value, None)
    if color:
        return f"<span style='color:{color};'>{text_value}</span>"
    else:
        return text_value


def update_slider_label(value, frame_validity_map, label):
    if value in frame_validity_map:
        if frame_validity_map[value]:
            is_valid = '<span style="color:green;">Valid Frame</span>'
        else:
            is_valid = '<span style="color:red;">Invalid Frame</span>'
    else:
        is_valid = '<span style="color:black;">Unknown</span>'

    label.setText(f"Frame Number: {value}    {is_valid}")


def update_task_display(selected_frame, ver_data_timeline, op_data_timeline, task_operation_display, format_frame):
    import globals
    collapsible_task = globals.collapsible_task

    # Find the most recent data snapshot at or before the selected frame
    chosen = next((snap for fno, snap in reversed(ver_data_timeline) if fno <= selected_frame), None)

    if not chosen:
        task_operation_display.setHtml("No SE/EV status data available.")
        collapsible_task.label_header.setText("")
        return

    # Extract status values and their corresponding frame numbers
    sv, sv_f = chosen.get("SeStatusVer", ("N/A", 0))
    si, si_f = chosen.get("SeStatusInit", ("N/A", 0))
    so, so_f = chosen.get("SeStatusOp", ("N/A", 0))
    ev, ev_f = chosen.get("EvStatusVer", ("N/A", 0))
    ei, ei_f = chosen.get("EvStatusInit", ("N/A", 0))

    # Find the most recent EvID and SeID frame numbers
    evID_frame = next((snap["EvIDPage"][1] for fno, snap in reversed(op_data_timeline) if
                       fno <= selected_frame and "EvIDPage" in snap), None)
    seID_frame = next((snap["SeIDPage"][1] for fno, snap in reversed(op_data_timeline) if
                       fno <= selected_frame and "SeIDPage" in snap), None)

    # Compute statuses based on the presence of ID frames
    evID_status = "Complete" if evID_frame else ("Incomplete" if seID_frame else "N/A")
    seID_status = "Complete" if seID_frame else ("Incomplete" if evID_frame else "N/A")

    # A helper function to colorize text based on its content
    def color_for(text: str) -> str:
        t = text.lower()
        if "incomplete" in t or "error" in t: return "red"
        if "complete" in t: return "green"
        if "n/a" in t or "not available" in t: return "#cfcfcf"
        return "black"

    # Assemble data rows for the HTML table
    rows = [
        (f"SeStatusVer: <span style='color:{color_for(sv)}'>{sv}</span>", sv_f,
         f"EvStatusVer: <span style='color:{color_for(ev)}'>{ev}</span>", ev_f),
        (f"SeStatusInit: <span style='color:{color_for(si)}'>{si}</span>", si_f,
         f"EvStatusInit: <span style='color:{color_for(ei)}'>{ei}</span>", ei_f),
        (f"SeIdStatus: <span style='color:{color_for(seID_status)}'>{seID_status}</span>", seID_frame,
         f"EvIdStatus: <span style='color:{color_for(evID_status)}'>{evID_status}</span>", evID_frame)
    ]

    # Build the HTML table
    html_parts = ["<div style='text-align:left;'>",
                  "<table style='border-collapse:collapse;width:100%;table-layout:fixed;text-align:left;margin:0;'>",
                  "<colgroup><col style='width:35%;'/><col style='width:15%;'/><col style='width:35%;'/><col style='width:15%;'/></colgroup>"]
    for se_label, se_fno, ev_label, ev_fno in rows:
        se_fr = format_frame(se_fno) if se_fno is not None else "--"
        ev_fr = format_frame(ev_fno) if ev_fno is not None else "--"
        html_parts.append(
            f"<tr><td style='padding:3px;vertical-align:top;'>{se_label}</td><td style='padding:3px;vertical-align:top;text-align:right;'>{se_fr}</td>"
            f"<td style='padding:3px;vertical-align:top;'>{ev_label}</td><td style='padding:3px;vertical-align:top;text-align:right;'>{ev_fr}</td></tr>")
    html_parts.append("</table></div>")

    task_operation_display.setHtml("".join(html_parts))

    # Update the collapsible box title based on the overall state
    sv_l = sv.lower()
    si_l = si.lower()
    so_l = so.lower()
    ev_l = ev.lower()
    collapsible_task.toggle_button.setText("Task:")

    # Determine state based on a priority
    if sv_l == 'incomplete' and ev_l == 'incomplete':
        collapsible_task.label_header.setText("Ver")
    elif sv_l == 'complete' and si_l in ('incomplete', 'error'):
        collapsible_task.label_header.setText("Init")
    elif sv_l == 'complete' and si_l == 'complete' and so_l != 'not_available':
        collapsible_task.label_header.setText("Op")
    else:
        # Fallback for other combinations or initial state
        collapsible_task.label_header.setText("<span style='color:#cfcfcf;'>N/A</span>")


def update_contactor_state_display(selected_frame, ver_data_timeline, contactor_state_display, format_frame):
    collapsible_contactor_state = globals.collapsible_contactor_state

    # Find the most recent data snapshot at or before the selected frame
    chosen_data = next((snap for fno, snap in reversed(ver_data_timeline) if fno <= selected_frame), None)

    if not chosen_data:
        contactor_state_display.setText("No Contactor data available.")
        collapsible_contactor_state.toggle_button.setText("Contactor State:")
        collapsible_contactor_state.label_header.setText("<span style='color:#cfcfcf;font-size:8pt;'> N/A</span>")
        return

    # Extract status values and their corresponding frame numbers
    se_status_op, se_frame = chosen_data.get("SeStatusOp", ("N/A", 0))
    ev_status_op, ev_frame = chosen_data.get("EvStatusOp", ("N/A", 0))

    # Determine the combined state and corresponding color for the header
    def combine_contactor_state(s_op, e_op):
        s_op_lower, e_op_lower = s_op.lower(), e_op.lower()
        if s_op_lower in ("not_available", "n/a") and e_op_lower in ("not_available", "n/a"):
            return "N/A", "#cfcfcf"
        if "error" in (s_op_lower, e_op_lower):
            return "Error", "red"
        if "deny_v" in (s_op_lower, e_op_lower):
            return "Deny_V", "brown"
        if s_op_lower == "permit_v" and e_op_lower == "permit_v":
            return "Permit_V", "green"
        return "Unknown", "black"

    combined_label, combined_color = combine_contactor_state(se_status_op, ev_status_op)

    # Update the collapsible box header text and color
    collapsible_contactor_state.toggle_button.setText("Contactor State:")
    collapsible_contactor_state.label_header.setText(
        f"<span style='color:{combined_color}; font-size:8pt;'> {combined_label}</span>"
    )

    # Build the HTML content for the detailed display inside the dropdown
    html = (
        f"<div style='text-align:left;'>"
        f"<table style='border-collapse:collapse;width:100%;table-layout:fixed;text-align:left;'>"
        f"<colgroup>"
        f"<col style='width:35%;'/><col style='width:15%;'/>"
        f"<col style='width:35%;'/><col style='width:15%;'/>"
        f"</colgroup>"
        f"<tr>"
        f"<td style='padding:3px;vertical-align:top'>SeStatusOp: {colorize_if_needed(se_status_op)}</td>"
        f"<td style='padding:3px;vertical-align:top;text-align:right'>{format_frame(se_frame)}</td>"
        f"<td style='padding:3px;vertical-align:top'>EvStatusOp: {colorize_if_needed(ev_status_op)}</td>"
        f"<td style='padding:3px;vertical-align:top;text-align:right'>{format_frame(ev_frame)}</td>"
        f"</tr>"
        f"</table>"
        f"</div>"
    )

    # Set the final HTML to the display widget
    contactor_state_display.setHtml(html)


def update_protocol_version_display(
        selected_frame: int,
        ver_data_timeline: list,
        selected_protocol_version_display,
        format_frame,
        ratings_display,
        protocol_version_names):

    collapsible = globals.collapsible_selected_protocol_version


    snap = next(
        (s for f, s in reversed(ver_data_timeline) if f <= selected_frame),
        None,
    )
    if snap is None:
        selected_protocol_version_display.setText("No Protocol Version data.")
        collapsible.toggle_button.setText("Protocol Version:")
        collapsible.label_header.setText("")
        return

    good_words = {"complete", "permit_v"}
    bad_words  = {"incomplete", "deny_v"}
    na_words   = {"n/a", "not available", "unknown"}

    def html_val(v):
        txt = str(v)
        low = txt.lower()
        if low in good_words:
            return f"<span style='color:green;font-size:8pt;'>{txt}</span>"
        if low in bad_words:
            return f"<span style='color:red;font-size:8pt;'>{txt}</span>"
        if low in na_words:
            return f"<span style='color:#cfcfcf;font-size:8pt;'>{txt}</span>"
        if "error" in low:
            return f"<span style='color:red;font-size:8pt;'>{txt}</span>"
        return txt

    def first_present(keys):
        for k in keys:
            if k in snap:
                return snap[k]
        return ("N/A", 0)

    # rows (label, candidate-keys)
    rows = [
        ("SeSelectedVersion", ["SeSelectedVersion"]),
        ("SeStatusVer",       ["SeStatusVer"]),
        ("SeStatusInit",      ["SeStatusInit"]),
        ("SeStatusOp",        ["SeStatusOp"]),
        ("SeVersionPage",     ["SeVersionPageNumber"]),

        ("EvSelectedVersion", ["EvSelectedVersion"]),
        ("EvStatusVer",       ["EvStatusVer"]),
        ("EvStatusInit",      ["EvStatusInit"]),
        ("EvStatusOp",        ["EvStatusOp"]),
        ("EvVersionPage",     ["EvVersionPageNumber"]),
    ]

    # collect cells
    left, right = [], []
    for lab, cand in rows:
        val, fr = first_present(cand)
        cell = f"{lab}: {html_val(val)}"
        fr_txt = format_frame(fr) if fr else "--"
        (left if lab.startswith("Se") else right).append((cell, fr_txt))

    # pad so the table is rectangular
    m = max(len(left), len(right))
    left  += [("", "")] * (m - len(left))
    right += [("", "")] * (m - len(right))

    # HTML table
    html_parts = [
        "<div style='text-align:left;'>",
        "<table style='border-collapse:collapse;width:100%;table-layout:fixed;'>",
        "<colgroup><col style='width:35%;'/><col style='width:15%;'/>"
        "<col style='width:35%;'/><col style='width:15%;'/></colgroup>",
    ]
    for (lv, lf), (rv, rf) in zip(left, right):
        html_parts += [
            "<tr>",
            f"<td style='padding:3px;'>{lv}</td>",
            f"<td style='padding:3px;text-align:right;'>{lf}</td>",
            f"<td style='padding:3px;'>{rv}</td>",
            f"<td style='padding:3px;text-align:right;'>{rf}</td>",
            "</tr>",
        ]
    html_parts.append("</table></div>")
    final_html = "".join(html_parts)

    selected_protocol_version_display.setHtml(final_html)
    ratings_display.setHtml(final_html)

    #  header colour & consensus version (green / brown / red)
    status_keys = [
        "SeStatusVer",  "EvStatusVer",
        "SeStatusInit", "EvStatusInit",
        "SeStatusOp",   "EvStatusOp",
    ]
    version_keys = ["SeSelectedVersion", "EvSelectedVersion"]

    na_vals   = {"n/a", "not available", "unknown", "255"}
    good_vals = {"complete", "permit_v"}
    bad_vals  = {"incomplete", "deny_v"}

    good_cnt = bad_cnt = 0
    for k in status_keys:
        raw = str(snap.get(k, ("N/A", 0))[0]).lower()
        if raw in good_vals:
            good_cnt += 1
        elif raw in bad_vals:
            bad_cnt += 1

    # detect explicit mismatch in numeric version / page numbers
    ver_raws = [str(snap.get(k, ("N/A", 0))[0]) for k in version_keys]
    ver_valid = [v for v in ver_raws if v.lower() not in na_vals]
    version_mismatch = len(set(ver_valid)) > 1

    if version_mismatch or (good_cnt == 0 and bad_cnt > 0):
        header_color = "red"
    elif good_cnt > 0 and bad_cnt > 0:
        header_color = "brown"
    elif good_cnt > 0 and bad_cnt == 0:
        header_color = "green"
    else:
        header_color = "grey"

    # consensus protocol version text (same as before)
    def to_int_or_none(s):
        try:
            return int(s)
        except Exception:
            return None

    se_ver = to_int_or_none(snap.get("SeSelectedVersion", ("N/A", 0))[0])
    ev_ver = to_int_or_none(snap.get("EvSelectedVersion", ("N/A", 0))[0])

    if se_ver is not None and ev_ver is not None and se_ver == ev_ver:
        consensus = se_ver
    elif se_ver is not None:
        consensus = se_ver
    elif ev_ver is not None:
        consensus = ev_ver
    else:
        consensus = "N/A"

    name = (
        protocol_version_names.get(consensus, "")
        if isinstance(consensus, int)
        else ""
    )
    if consensus in ("N/A", 255):
        title_text = "N/A"
    else:
        title_text = f"{consensus} ({name})" if name else str(consensus)

    colored_title = (
        f"<span style='color:{header_color};font-size:8pt;'>{title_text}</span>"
    )

    collapsible.toggle_button.setText("Protocol Version:")
    collapsible.label_header.setText(colored_title)



def update_sesupported_protocol_versions_display(selected_frame, ver_data_timeline, sesupported_protocol_versions_display, format_frame):

    collapsible_sesupported_protocol_versions = globals.collapsible_sesupported_protocol_versions

    def interpret_supported_version(val_str: str) -> str:
        """
        Convert the given version byte string into a descriptive HTML string.
        """
        try:
            val = int(val_str)
        except (ValueError, TypeError):
            return "<span style='color:#cfcfcf;'>N/A</span>"

        if val == 255:
            return "<span style='color:#cfcfcf;'>N/A</span>"
        elif val == 254:
            return "<span style='color:red;'>Reserved</span>"
        elif val in [0, 1, 2]:
            return f"<span style='color:black;'>{val}</span>"
        elif 3 <= val <= 239:
            return "<span style='color:black;'>Reserved</span>"
        elif 240 <= val <= 253:
            return "<span style='color:black;'>Experimental</span>"
        else:
            return f"<span style='color:black;'>Unknown ({val})</span>"

    # Find the most recent data for SE and EV respectively
    chosen_data_se = next((d for f, d in reversed(ver_data_timeline) if f <= selected_frame and "SeVersionPageNumber" in d), None)
    chosen_data_ev = next((d for f, d in reversed(ver_data_timeline) if f <= selected_frame and "EvVersionPageNumber" in d), None)

    if not chosen_data_se and not chosen_data_ev:
        sesupported_protocol_versions_display.setText("No Supported Versions data available.")
        collapsible_sesupported_protocol_versions.toggle_button.setText("Supported Versions")
        collapsible_sesupported_protocol_versions.label_header.setText("")
        return

    # Helper to process data for either SE or EV
    def get_version_data(prefix, chosen_data):
        data_rows, supported_versions = [], []
        if chosen_data:
            page_num, page_frame = chosen_data.get(f"{prefix}VersionPageNumber", ("N/A", 0))
            data_rows.append((f"{prefix}VersionPageNumber: {page_num}", format_frame(page_frame)))
            for i in range(1, 6):
                key = f"{prefix}SupportedVersion{i}"
                val_str, frame_no = chosen_data.get(key, ("N/A", 0))
                data_rows.append((f"{key}: {interpret_supported_version(val_str)}", format_frame(frame_no)))
                if val_str.isdigit() and int(val_str) not in [254, 255]:
                    supported_versions.append(val_str)
        return data_rows, supported_versions

    se_data, se_supported_versions = get_version_data("Se", chosen_data_se)
    ev_data, ev_supported_versions = get_version_data("Ev", chosen_data_ev)

    # Build the HTML table for the dropdown content
    max_len = max(len(se_data), len(ev_data))
    html_parts = ["<div style='text-align:left;'><table style='border-collapse: collapse; width:100%; table-layout:fixed; text-align:left; margin:0;'>",
                  "<colgroup><col style='width:35%;'/><col style='width:15%;'/><col style='width:35%;'/><col style='width:15%;'/></colgroup>"]
    for i in range(max_len):
        se_key_val, se_frame = se_data[i] if i < len(se_data) else ("", "")
        ev_key_val, ev_frame = ev_data[i] if i < len(ev_data) else ("", "")
        html_parts.append(f"<tr><td style='padding:3px;'>{se_key_val}</td><td style='padding:3px;text-align:right;'>{se_frame}</td>"
                          f"<td style='padding:3px;'>{ev_key_val}</td><td style='padding:3px;text-align:right;'>{ev_frame}</td></tr>")
    html_parts.append("</table></div>")
    sesupported_protocol_versions_display.setHtml("".join(html_parts))

    se_supported_str = ", ".join(se_supported_versions) if se_supported_versions else "N/A"
    ev_supported_str = ", ".join(ev_supported_versions) if ev_supported_versions else "N/A"

    # Update the toggle button text with the desired format
    collapsible_sesupported_protocol_versions.toggle_button.setText(
        f"SeSupported Version: {se_supported_str}   EvSupported Version: {ev_supported_str}"
    )
    # Set the adjacent header label to be empty
    collapsible_sesupported_protocol_versions.label_header.setText("")


def parse_freq_ev(s):
    """
    Parse EV Frequency string. Returns a list of integer frequencies.
    """
    if "N/A" in s or "#cfcfcf\">N/A</span>" in s:
        return []
    frequencies = []
    # Split by commas, 'and' (case-insensitive), or '&'
    parts = re.split(r',|\bor\b|&', s, flags=re.IGNORECASE)
    for part in parts:
        part = part.strip()
        # Handle ranges like "50-60 Hz" (case-insensitive)
        range_match = re.match(r'(\d+)\s*-\s*(\d+)\s*Hz', part, flags=re.IGNORECASE)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            frequencies.extend(range(start, end + 1))
        else:
            freq_match = re.search(r'(\d+)\s*Hz', part, flags=re.IGNORECASE)
            if freq_match:
                frequencies.append(int(freq_match.group(1)))
    return frequencies


def parse_freq_se(s):
    """
    Parse SE Frequency string. Returns an integer frequency or None.
    """
    if "N/A" in s or "#cfcfcf\">N/A</span>" in s:
        return None
    match = re.search(r'(\d+)\s*Hz', s, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def update_ratings_display(selected_frame, init_data_timeline, ratings_display):
    """
    Fill the 'ratings_display' TextEdit in two columns:
      Left column:  SE nominal data (SeNomVoltageL1N, etc.) and max currents
      Right column: EV max/min voltages/frequencies, max currents, min currents.
    """
    collapsible_ratings = globals.collapsible_ratings

    chosen_data = None
    for (fno, data_dict) in reversed(init_data_timeline):
        if fno <= selected_frame:
            chosen_data = data_dict
            break
    if not chosen_data:
        ratings_display.setText("No Ratings data available.")
        collapsible_ratings.toggle_button.setText(f"Ratings:")
        collapsible_ratings.label_header.setText("<span style='color:gray;font-size:8pt;'> Incomplete</span>")
        return

    se_nom_l1n_str, f_se_nom_l1n = chosen_data.get("SeNomVoltageL1N", ("N/A", 0))
    se_nom_ll_str, f_se_nom_ll = chosen_data.get("SeNomVoltageLL", ("N/A", 0))
    se_freq_str, f_se_freq = chosen_data.get("SeFrequency", ("N/A", 0))
    se_max_l1_str, f_se_max_l1 = chosen_data.get("SeMaxCurrent_L1", ("N/A", 0))
    se_max_l2_str, f_se_max_l2 = chosen_data.get("SeMaxCurrent_L2", ("N/A", 0))
    se_max_l3_str, f_se_max_l3 = chosen_data.get("SeMaxCurrent_L3", ("N/A", 0))
    se_max_n_str, f_se_max_n = chosen_data.get("SeMaxCurrent_N", ("N/A", 0))

    ev_max_l1n_str, f_ev_max_l1n = chosen_data.get("EvMaxVoltageL1N", ("N/A", 0))
    ev_max_ll_str, f_ev_max_ll = chosen_data.get("EvMaxVoltageLL", ("N/A", 0))
    ev_min_l1n_str, f_ev_min_l1n = chosen_data.get("EvMinVoltageL1N", ("N/A", 0))
    ev_min_ll_str, f_ev_min_ll = chosen_data.get("EvMinVoltageLL", ("N/A", 0))
    ev_freq_str, f_ev_freq = chosen_data.get("EvFrequencies", ("N/A", 0))
    ev_maxC_l1_str, f_ev_maxC_l1 = chosen_data.get("EvMaxCurrent_L1", ("N/A", 0))
    ev_maxC_l2_str, f_ev_maxC_l2 = chosen_data.get("EvMaxCurrent_L2", ("N/A", 0))
    ev_maxC_l3_str, f_ev_maxC_l3 = chosen_data.get("EvMaxCurrent_L3", ("N/A", 0))
    ev_maxC_n_str, f_ev_maxC_n = chosen_data.get("EvMaxCurrent_N", ("N/A", 0))
    ev_minC_l1_str, f_ev_minC_l1 = chosen_data.get("EvMinCurrent_L1", ("N/A", 0))
    ev_minC_l2_str, f_ev_minC_l2 = chosen_data.get("EvMinCurrent_L2", ("N/A", 0))
    ev_minC_l3_str, f_ev_minC_l3 = chosen_data.get("EvMinCurrent_L3", ("N/A", 0))

    def parse_voltage(s):
        if "N/A" in s or "#cfcfcf\">N/A</span>" in s:
            return None
        s = s.replace("V", "").strip()
        try:
            val = float(s)
        except ValueError:
            return None
        if val in (6553.5, 254.0, 255.0):
            return None
        return val

    def parse_current(s):
        if "N/A" in s or "#cfcfcf\">N/A</span>" in s:
            return None
        s = s.replace("A", "").strip()
        try:
            val = float(s)
        except ValueError:
            return None
        if val in (254.0, 255.0):
            return None
        return val

    se_nom_l1n = parse_voltage(se_nom_l1n_str)
    se_nom_ll = parse_voltage(se_nom_ll_str)
    se_max_l1 = parse_current(se_max_l1_str)
    se_max_l2 = parse_current(se_max_l2_str)
    se_max_l3 = parse_current(se_max_l3_str)
    se_max_n = parse_current(se_max_n_str)

    ev_max_l1n = parse_voltage(ev_max_l1n_str)
    ev_max_ll = parse_voltage(ev_max_ll_str)
    ev_min_l1n = parse_voltage(ev_min_l1n_str)
    ev_min_ll = parse_voltage(ev_min_ll_str)
    ev_maxC_l1 = parse_current(ev_maxC_l1_str)
    ev_maxC_l2 = parse_current(ev_maxC_l2_str)
    ev_maxC_l3 = parse_current(ev_maxC_l3_str)
    ev_maxC_n = parse_current(ev_maxC_n_str)
    ev_minC_l1 = parse_current(ev_minC_l1_str)
    ev_minC_l2 = parse_current(ev_minC_l2_str)
    ev_minC_l3 = parse_current(ev_minC_l3_str)

    se_freq = parse_freq_se(se_freq_str)
    ev_freq = parse_freq_ev(ev_freq_str)

    def color_for_volt_range(se_str, ev_min_str, ev_max_str, se_val, ev_min_val, ev_max_val):
        if "N/A" in se_str or "N/A" in ev_min_str or "N/A" in ev_max_str:
            return "#cfcfcf"
        if se_val is None or ev_min_val is None or ev_max_val is None:
            return "gray"
        return "green" if (ev_min_val <= se_val <= ev_max_val) else "red"

    def color_for_current_range(se_str, ev_min_str, se_val, ev_min_val):
        if "N/A" in se_str or "N/A" in ev_min_str:
            return "#cfcfcf"
        if "FF" in se_str.upper() or "FF" in ev_min_str.upper():
            return "#cfcfcf"
        if se_val is None or ev_min_val is None:
            return "gray"
        if se_val == 0:
            return "#cfcfcf"
        return "green" if (se_val >= ev_min_val) else "red"

    color_nom_l1n = color_for_volt_range(se_nom_l1n_str, ev_min_l1n_str, ev_max_l1n_str, se_nom_l1n, ev_min_l1n,
                                         ev_max_l1n)
    color_nom_ll = color_for_volt_range(se_nom_ll_str, ev_min_ll_str, ev_max_ll_str, se_nom_ll, ev_min_ll, ev_max_ll)
    color_freq = "gray" if se_freq is None or not ev_freq else ("green" if (se_freq in ev_freq) else "red")
    color_max_l1 = color_for_current_range(se_max_l1_str, ev_minC_l1_str, se_max_l1, ev_minC_l1)
    color_max_l2 = color_for_current_range(se_max_l2_str, ev_minC_l2_str, se_max_l2, ev_minC_l2)
    color_max_l3 = color_for_current_range(se_max_l3_str, ev_minC_l3_str, se_max_l3, ev_minC_l3)
    color_max_n = "gray" if (se_max_n is None) else "green"
    color_ev_maxC_n = "gray" if (ev_maxC_n is None) else "green"

    all_colors = [color_nom_l1n, color_nom_ll, color_freq, color_max_l1, color_max_l2, color_max_l3, color_max_n,
                  color_ev_maxC_n]

    def compute_ratings_label(colors):
        relevant_colors = [c for c in colors if c != "#cfcfcf"]
        if not relevant_colors:
            return "Incomplete"
        if any(c == "red" for c in relevant_colors):
            return "Incompatible"
        if all(c == "green" for c in relevant_colors):
            return "Compatible"
        return "Incomplete"

    ratings_label = compute_ratings_label(all_colors)

    color_map = {"Compatible": "green", "Incompatible": "red", "Incomplete": "gray"}
    color = color_map.get(ratings_label, "#000000")

    collapsible_ratings.toggle_button.setText(f"Ratings:")
    collapsible_ratings.label_header.setText(f"<span style='color:{color};font-size:8pt;'> {ratings_label}</span>")

    se_key_val_lines = [
        f"SeNomVoltageL1N:<span style='color:{color_nom_l1n};'> {se_nom_l1n_str} </span>",
        f"SeNomVoltageLL:<span style='color:{color_nom_ll};'> {se_nom_ll_str} </span>",
        f"SeFrequency:<span style='color:{color_freq};'> {se_freq_str} </span>",
        f"SeMaxCurrentL1:<span style='color:{color_max_l1};'> {se_max_l1_str} </span>",
        f"SeMaxCurrentL2:<span style='color:{color_max_l2};'> {se_max_l2_str} </span>",
        f"SeMaxCurrentL3:<span style='color:{color_max_l3};'> {se_max_l3_str} </span>",
        f"SeMaxCurrentN:<span style='color:{color_max_n};'> {se_max_n_str} </span>",
    ]

    se_frame_lines = [
        format_frame(f_se_nom_l1n),
        format_frame(f_se_nom_ll),
        format_frame(f_se_freq),
        format_frame(f_se_max_l1),
        format_frame(f_se_max_l2),
        format_frame(f_se_max_l3),
        format_frame(f_se_max_n),
    ]

    ev_key_val_lines = [
        f"EvMaxVoltageL1N:<span style='color:{color_nom_l1n};'> {ev_max_l1n_str} </span>",
        f"EvMinVoltageL1N:<span style='color:{color_nom_l1n};'> {ev_min_l1n_str} </span>",
        f"EvMaxVoltageLL:<span style='color:{color_nom_ll};'> {ev_max_ll_str} </span>",
        f"EvMinVoltageLL:<span style='color:{color_nom_ll};'> {ev_min_ll_str} </span>",
        f"EvFrequency:<span style='color:{color_freq};'> {ev_freq_str} </span>",
        f"EvMaxCurrentL1:<span style='color:{color_max_l1};'> {ev_maxC_l1_str} </span>",
        f"EvMaxCurrentL2:<span style='color:{color_max_l2};'> {ev_maxC_l2_str} </span>",
        f"EvMaxCurrentL3:<span style='color:{color_max_l3};'> {ev_maxC_l3_str} </span>",
        f"EvMaxCurrentN:<span style='color:{color_ev_maxC_n};'> {ev_maxC_n_str} </span>",
        f"EvMinCurrentL1:<span style='color:{color_max_l1};'> {ev_minC_l1_str} </span>",
        f"EvMinCurrentL2:<span style='color:{color_max_l2};'> {ev_minC_l2_str} </span>",
        f"EvMinCurrentL3:<span style='color:{color_max_l3};'> {ev_minC_l3_str} </span>"
    ]


    ev_frame_lines = [
        format_frame(f_ev_max_l1n),
        format_frame(f_ev_max_ll),
        format_frame(f_ev_freq),
        format_frame(f_ev_min_l1n),
        format_frame(f_ev_min_ll),
        format_frame(f_ev_maxC_l1),
        format_frame(f_ev_maxC_l2),
        format_frame(f_ev_maxC_l3),
        format_frame(f_ev_maxC_n),
        format_frame(f_ev_minC_l1),
        format_frame(f_ev_minC_l2),
        format_frame(f_ev_minC_l3),
    ]


    max_len = max(len(se_key_val_lines), len(ev_key_val_lines))
    html_parts = []
    html_parts.append("<div style='text-align:left;'>")
    html_parts.append(
        "<table style='border-collapse:collapse; width:100%; table-layout:fixed; text-align:left; margin:0;'>")
    html_parts.append("<colgroup>")
    html_parts.append("<col style='width:35%;'/>")
    html_parts.append("<col style='width:15%;'/>")
    html_parts.append("<col style='width:35%;'/>")
    html_parts.append("<col style='width:15%;'/>")
    html_parts.append("</colgroup>")

    for i in range(max_len):
        se_label = se_key_val_lines[i] if i < len(se_key_val_lines) else ""
        se_frame = se_frame_lines[i] if i < len(se_frame_lines) else ""
        ev_label = ev_key_val_lines[i] if i < len(ev_key_val_lines) else ""
        ev_frame = ev_frame_lines[i] if i < len(ev_frame_lines) else ""

        html_parts.append("<tr>")
        html_parts.append(f"<td style='padding:3px;vertical-align:top;text-align:left'>{se_label}</td>")
        html_parts.append(f"<td style='padding:3px;vertical-align:top;text-align:right'>{se_frame}</td>")
        html_parts.append(f"<td style='padding:3px;vertical-align:top;text-align:left'>{ev_label}</td>")
        html_parts.append(f"<td style='padding:3px;vertical-align:top;text-align:right'>{ev_frame}</td>")
        html_parts.append("</tr>")

    html_parts.append("</table>")
    html_parts.append("</div>")

    final_html = "".join(html_parts)
    ratings_display.setHtml(final_html)


def update_seavailable_current_display(selected_frame, init_data_timeline, seavailable_current_display, format_frame):
    """
    Display SeAvailableCurrentL1..N in 'seavailable_current_display',
    with frame # and color-coding. Also show the highest valid current
    on the collapsible box title.
    """
    collapsible_seavailable_current = globals.collapsible_seavailable_current

    # This function correctly uses init_data_timeline. The only fix needed is to use format_frame.
    chosen_data = None
    for (fno, data_dict) in reversed(init_data_timeline):
        if fno <= selected_frame:
            chosen_data = data_dict
            break

    if not chosen_data:
        seavailable_current_display.setText("No SeAvailableCurrent data available.")
        collapsible_seavailable_current.toggle_button.setText("SeAvailableCurrent:")
        collapsible_seavailable_current.label_header.setText(f"<span style='color:#cfcfcf;font-size:8pt;'>N/A</span>")
        return

    se_avail_l1, f_l1 = chosen_data.get("SeAvailableCurrent_L1", ("N/A", 0))
    se_avail_l2, f_l2 = chosen_data.get("SeAvailableCurrent_L2", ("N/A", 0))
    se_avail_l3, f_l3 = chosen_data.get("SeAvailableCurrent_L3", ("N/A", 0))
    se_avail_n, f_n = chosen_data.get("SeAvailableCurrent_N", ("N/A", 0))

    def parse_amp(val):
        if val == "N/A" or val.endswith('#cfcfcf">N/A</span>'): return None
        if val.endswith("A"):
            try:
                return int(val[:-1])
            except:
                return None
        return None

    amps = [parse_amp(se_avail_l1), parse_amp(se_avail_l2), parse_amp(se_avail_l3), parse_amp(se_avail_n)]
    valid_amps = [a for a in amps if a is not None]

    if not valid_amps:
        color_final = "#cfcfcf"
    elif all(v == valid_amps[0] for v in valid_amps):
        color_final = "green"
    else:
        color_final = "#664f3c"

    data_lines = [
        color_if_na("SeAvailableCurrentL1", se_avail_l1),
        color_if_na("SeAvailableCurrentL2", se_avail_l2),
        color_if_na("SeAvailableCurrentL3", se_avail_l3),
        color_if_na("SeAvailableCurrentN", se_avail_n),
    ]

    frame_lines = [
        format_frame(f_l1),
        format_frame(f_l2),
        format_frame(f_l3),
        format_frame(f_n),
    ]

    html_parts = ["<div style='text-align:left;'>",
                  "<table style='border-collapse:collapse;width:100%;table-layout:fixed;text-align:left;margin:0;'>",
                  "<colgroup><col style='width:70%;'/><col style='width:30%;'/></colgroup>"]
    for i in range(len(data_lines)):
        html_parts.append(f"<tr><td style='padding:3px;vertical-align:top;text-align:left'>{data_lines[i]}</td>"
                          f"<td style='padding:3px;vertical-align:top;text-align:right'>{frame_lines[i]}</td></tr>")
    html_parts.append("</table></div>")

    seavailable_current_display.setHtml("".join(html_parts))

    if valid_amps:
        highest_amp = max(valid_amps)
        collapsible_seavailable_current.label_header.setText(
            f"<span style='color:{color_final};font-size:8pt;'> {highest_amp}A</span>")
    else:
        collapsible_seavailable_current.label_header.setText(f"<span style='color:#cfcfcf;font-size:8pt;'> N/A</span>")
    collapsible_seavailable_current.toggle_button.setText("SeAvailableCurrent:")


def update_evpresent_current_display(selected_frame, op_data_timeline, evpresent_current_display, format_frame):
    """
    Shows EvPresentCurrentL1..N in 'evpresent_current_display' with frame
    numbers and color-coding rules, and also displays the highest valid
    current on the collapsible box title.
    """
    collapsible_evpresent_current = globals.collapsible_evpresent_current

    # FIX: This data is in op_data_timeline, not init_data_timeline
    chosen_data = None
    for (fno, data_dict) in reversed(op_data_timeline):
        if fno <= selected_frame:
            chosen_data = data_dict
            break

    if not chosen_data:
        evpresent_current_display.setText("No EvPresentCurrent data available.")
        collapsible_evpresent_current.toggle_button.setText("EvPresentCurrent:")
        collapsible_evpresent_current.label_header.setText(f"<span style='color:#cfcfcf;font-size:8pt;'> N/A</span>")
        return

    ev_pres_l1, f_l1 = chosen_data.get("EvOpPresentCurrent_L1", ("N/A", 0))
    ev_pres_l2, f_l2 = chosen_data.get("EvOpPresentCurrent_L2", ("N/A", 0))
    ev_pres_l3, f_l3 = chosen_data.get("EvOpPresentCurrent_L3", ("N/A", 0))
    ev_pres_n, f_n = chosen_data.get("EvOpPresentCurrent_N", ("N/A", 0))

    def parse_amp(val):
        if val == "N/A" or val.endswith('#cfcfcf">N/A</span>'): return None
        if val.endswith("A"):
            try:
                return int(val[:-1])
            except:
                return None
        return None

    amps = [parse_amp(v) for v in [ev_pres_l1, ev_pres_l2, ev_pres_l3, ev_pres_n]]
    valid_amps = [a for a in amps if a is not None]

    if not valid_amps:
        color_final = "#cfcfcf"
    elif all(v == valid_amps[0] for v in valid_amps):
        color_final = "green"
    else:
        color_final = "#664f3c"

    data_lines = [
        color_if_na("EvPresentCurrentL1", ev_pres_l1),
        color_if_na("EvPresentCurrentL2", ev_pres_l2),
        color_if_na("EvPresentCurrentL3", ev_pres_l3),
        color_if_na("EvPresentCurrentN", ev_pres_n),
    ]

    frame_lines = [
        format_frame(f_l1),
        format_frame(f_l2),
        format_frame(f_l3),
        format_frame(f_n),
    ]

    html_parts = ["<div style='text-align:left;'>",
                  "<table style='border-collapse:collapse;width:100%;table-layout:fixed;text-align:left;margin:0;'>",
                  "<colgroup><col style='width:70%;'/><col style='width:30%;'/></colgroup>"]
    for i in range(len(data_lines)):
        html_parts.append(f"<tr><td style='padding:3px;vertical-align:top;text-align:left'>{data_lines[i]}</td>"
                          f"<td style='padding:3px;vertical-align:top;text-align:right'>{frame_lines[i]}</td></tr>")
    html_parts.append("</table></div>")

    evpresent_current_display.setHtml("".join(html_parts))

    if valid_amps:
        highest_amp = max(valid_amps)
        collapsible_evpresent_current.label_header.setText(
            f"<span style='color:{color_final};font-size:8pt;'> {highest_amp}A</span>")
    else:
        collapsible_evpresent_current.label_header.setText(f"<span style='color:#cfcfcf;font-size:8pt;'> N/A</span>")
    collapsible_evpresent_current.toggle_button.setText("EvPresentCurrent:")


def update_evrequested_current_display(selected_frame, op_data_timeline, evrequested_current_display, format_frame):
    """
    Shows EvRequestedCurrentL1..N in the 'evrequested_current_display' box,
    along with the frame number and color-coding, and enables time toggle.
    """
    collapsible_evrequested_current = globals.collapsible_evrequested_current

    chosen_data = None
    for (fno, data_dict) in reversed(op_data_timeline):
        if fno <= selected_frame:
            chosen_data = data_dict
            break

    if not chosen_data:
        collapsible_evrequested_current.toggle_button.setText("EvRequestedCurrent:")
        evrequested_current_display.setHtml("No EV Requested Current data available.")
        collapsible_evrequested_current.label_header.setText(
            f"<span style='color:#cfcfcf;font-size:8pt;'> N/A</span>"
        )
        return

    ev_req_l1, f_l1 = chosen_data.get("EvOpRequestedCurrent_L1", ("N/A", 0))
    ev_req_l2, f_l2 = chosen_data.get("EvOpRequestedCurrent_L2", ("N/A", 0))
    ev_req_l3, f_l3 = chosen_data.get("EvOpRequestedCurrent_L3", ("N/A", 0))
    ev_req_n, f_n = chosen_data.get("EvOpRequestedCurrent_N", ("N/A", 0))

    def parse_amp(val):
        if val == "N/A" or val.endswith('#cfcfcf">N/A</span>'):
            return None
        if val.endswith("A"):
            try:
                return int(val[:-1])
            except:
                return None
        return None

    amps = [
        parse_amp(ev_req_l1),
        parse_amp(ev_req_l2),
        parse_amp(ev_req_l3),
        parse_amp(ev_req_n),
    ]

    valid_amps = [a for a in amps if a is not None]

    if not valid_amps:
        color_final = "#cfcfcf"
    elif all(v == valid_amps[0] for v in valid_amps):
        color_final = "green"
    else:
        color_final = "#664f3c"

    data_lines = [
        color_if_na("EvRequestedCurrentL1", ev_req_l1),
        color_if_na("EvRequestedCurrentL2", ev_req_l2),
        color_if_na("EvRequestedCurrentL3", ev_req_l3),
        color_if_na("EvRequestedCurrentN", ev_req_n),
    ]

    frame_lines = [
        format_frame(f_l1),
        format_frame(f_l2),
        format_frame(f_l3),
        format_frame(f_n),
    ]

    html_parts = []
    html_parts.append(
        "<table style='border-collapse: collapse; width:100%; table-layout:fixed; text-align:left; margin:0;'>"
    )
    html_parts.append("<colgroup><col style='width:70%;'/><col style='width:30%;'/></colgroup>")

    for i in range(len(data_lines)):
        data = data_lines[i]
        frame = frame_lines[i]
        html_parts.append("<tr>")
        html_parts.append(f"<td style='padding:3px;vertical-align:top;text-align:left'>{data}</td>")
        html_parts.append(f"<td style='padding:3px;vertical-align:top;text-align:right'>{frame}</td>")
        html_parts.append("</tr>")
    html_parts.append("</table>")

    final_html = "".join(html_parts)
    evrequested_current_display.setHtml(final_html)

    if valid_amps:
        highest_amp = max(valid_amps)
        collapsible_evrequested_current.label_header.setText(
            f"<span style='color:{color_final};font-size:8pt;'> {highest_amp}A</span>"
        )
    else:
        collapsible_evrequested_current.label_header.setText(
            f"<span style='color:#cfcfcf;font-size:8pt;'> N/A</span>"
        )
    collapsible_evrequested_current.toggle_button.setText("EvRequestedCurrent:")


def update_EvInfo_display(selected_frame, init_data_timeline, EvInfo_display, format_frame):
    """
    Update the 'EvInfo_display' QTextEdit to show
    EvInfoPageNumber and EvInfoEntry1..6 with their corresponding frame numbers.
    Format:
        EvInfoPageNumber: 0 (Frame #)
        EvInfoEntry1: 11 (Frame #) → EV determines that Protocol Version selection fails
        ...
    Additionally, update the collapsible_EvInfo toggle button text so that next to "EvInfo:" it
    shows only the hex info strings in a comma-separated list (skipping "FF").
    """
    collapsible_EvInfo = globals.collapsible_EvInfo

    # Search init_data_timeline backwards for a dict that has "EvInfoPageNumber"
    chosen_data = None
    for (fno, data_dict) in reversed(init_data_timeline):
        if fno <= selected_frame and "EvInfoPageNumber" in data_dict:
            chosen_data = data_dict
            break

    if not chosen_data:
        EvInfo_display.setText("No EV Info data available.")
        collapsible_EvInfo.toggle_button.setText("EvInfo:")
        collapsible_EvInfo.label_header.setText("")
        return

    # Extract the page number and its frame number
    page_num, page_frame = chosen_data.get("EvInfoPageNumber", ("N/A", "Unknown Frame"))

    # Each entry is a tuple: (hex_value, frame_no)
    entry_vals = []
    for i in range(1, 7):
        entry = chosen_data.get(f"EvInfoEntry{i}", ("N/A", "Unknown Frame"))
        entry_vals.append(entry)

    # Mapping of hex codes to descriptions
    EvInfoCodeMap = {
        "11": "EV determines that Protocol Version selection fails",
        "12": "EV determines that Initialization fails",
        "13": "EV determines to restart control seq. to reselect Protocol Version",
        "14": "[Deprecated]",
        "15": "EV needs to restart after MCU reset or CP-level event",
        "16": "EV needs to restart after no LIN detected for TnoLIN",
        "17": "EV detects no LIN headers for longer than TnoLIN",
        "18": "EV determines to restart after detecting recoverable internal fault",
        "19": "EV will terminate charging; an unrec. internal fault was detected",
        "1A": "Max available current is too low",
        "1B": "Minimum available voltage is too high",
        "1C": "Frequency does not match",
        "1D": "Charging delayed due to EMS",
        "1E": "EV isolation fault",
        "1F": "EV is not immediately ready to receive AC voltage",
        "20": "EV requests AC supply to be interrupted by load <1 A & opening S2",
        "21": "EV requests AC supply to be interrupted by opening S2 immediately",
        "22": "Maximum available voltage is too low",
        "23": "Unable to lock inlet, charging delayed until lock succeeds",
        "24": "Paging error",
        "25": "EV requires at least EvMinCurrentX to supply fixed load right now",
        "26": "EV requires no additional energy in this session (e.g. HVESS full)",
        "27": "Temporary conditions preventing charging (e.g. HVESS under temp.)",
        "28": "Fatal error prevents charging; EV may require service",
        "29": "EV determines connection with SE is incompatible",
        "2A": "Charging delayed for identification or affiliation",
        "2B": "Charging disallowed due to missing or invalid identity",
        "2C": "Proximity power requested",
        "2D": "EV detects inlet overtemp",
        "2F": "EV detects proximity out of range",
        "FF": "Empty"
    }

    data_lines = []
    frame_lines = []

    data_lines.append(f"EvInfoPageNumber: {page_num}")
    frame_lines.append(format_frame(page_frame))

    for i, (val_hex, frame_no) in enumerate(entry_vals, start=1):
        desc = EvInfoCodeMap.get(val_hex, "Reserved or Unknown")
        data_lines.append(f"EvInfoEntry{i}: {val_hex} → {desc}")
        # FIX: Use format_frame for the time toggle
        frame_lines.append(format_frame(frame_no))

    # Build the final HTML table (two columns: data and frame numbers)
    html_parts = []
    html_parts.append(
        "<table style='border-collapse: collapse; width:100%; table-layout:fixed; text-align:left; margin:0;'>"
    )
    html_parts.append("<colgroup><col style='width:70%;'/><col style='width:30%;'/></colgroup>")
    max_len = max(len(data_lines), len(frame_lines))
    for i in range(max_len):
        data = data_lines[i] if i < len(data_lines) else ""
        frame = frame_lines[i] if i < len(frame_lines) else ""
        html_parts.append("<tr>")
        html_parts.append(f"<td style='padding:3px;vertical-align:top;text-align:left'>{data}</td>")
        html_parts.append(f"<td style='padding:3px;vertical-align:top;text-align:right'>{frame}</td>")
        html_parts.append("</tr>")
    html_parts.append("</table>")
    final_html = "".join(html_parts)
    EvInfo_display.setHtml(final_html)

    hex_values = [val_hex for (val_hex, _) in entry_vals if val_hex.upper() != "FF" and val_hex != "N/A"]
    hex_list_str = ", ".join(hex_values)
    collapsible_EvInfo.toggle_button.setText(f"EvInfo: {hex_list_str}")


def update_SeInfo_display(selected_frame, init_data_timeline, SeInfo_display, format_frame):
    """
    Update the 'SeInfo_display' QTextEdit to show
    SeInfoPageNumber and SeInfoEntry1..6 with their corresponding frame numbers.
    """
    collapsible_SeInfo = globals.collapsible_SeInfo

    # Search init_data_timeline backwards for a dict that has "SeInfoPageNumber"
    chosen_data = None
    for (fno, data_dict) in reversed(init_data_timeline):
        if fno <= selected_frame and "SeInfoPageNumber" in data_dict:
            chosen_data = data_dict
            break

    if not chosen_data:
        SeInfo_display.setText("No SE Info data available.")
        collapsible_SeInfo.toggle_button.setText("SeInfo:")
        collapsible_SeInfo.label_header.setText(f"")
        return

    # Extract the page number and its frame number
    page_num, page_frame = chosen_data.get("SeInfoPageNumber", ("N/A", "Unknown Frame"))

    # Extract SeInfoEntry1 to SeInfoEntry6 along with their frame numbers
    entry_vals = []
    for i in range(1, 7):
        entry = chosen_data.get(f"SeInfoEntry{i}", ("N/A", "Unknown Frame"))
        entry_vals.append(entry)  # Each entry is a tuple (value, frame_no)

    # SeInfoCodeMap: Mapping of hex codes to descriptions
    SeInfoCodeMap = {
        "11": "SE determines that Protocol Version selection fails", "12": "SE determines that Initialization fails",
        "13": "SE determines to restart the control sequence to reselect Protocol Version",
        "14": "[This value is deprecated]",
        "15": "SE needs to restart the control sequence after an MCU reset",
        "16": "SE needs to restart the control sequence after a control power outage",
        "17": "SE detects no LIN responses for longer than TnoLIN",
        "18": "SE needs to restart the control sequence after detecting an internal fault",
        "19": "Charging delayed due to energy management system",
        "1A": "Charging stopped by user, for example the stop button on the charging station is pressed",
        "1B": "Maximum available current is too low (SeMaxCurrentX < EvMinCurrentX)",
        "1C": "Minimum available voltage is too high (lowest SeNomVoltage > EvMaxVoltage)",
        "1D": "Frequency does not match", "1E": "Initialization timeout at EVSE", "1F": "Overtemperature in connector",
        "20": "Overtemperature internally", "21": "Temperature sensor irrational",
        "22": "Overcurrent (EV load current is too high)",
        "23": "Current sensor irrational", "24": "Voltage sensor irrational", "25": "Pilot voltage fault",
        "26": "AC supply contactor fault", "27": "Input AC supply miswired",
        "28": "Measured AC supply input is over voltage",
        "29": "Measured AC supply input is under voltage", "2A": "CCID self-test fault",
        "2B": "CCID tripped – SE will auto-retry",
        "2C": "CCID tripped – retry limit exceeded/no auto-retry allowed", "2D": "Breaker tripped",
        "2E": "Ground monitor circuit fault", "2F": "EVSE configuration error",
        "30": "Improper grounding or ground is not present",
        "31": "Problem with EV communications – Disconnect and restart", "32": "Internal EVSE fault – Call for service",
        "33": "Maximum available voltage is too low", "34": "Paging error",
        "35": "SE determines connection with EV is incompatible",
        "36": "Charging delayed for identification or affiliation",
        "37": "Charging delayed for payment (external or plug-&-charge)",
        "38": "Charging disallowed due to missing or invalid identity",
        "39": "SE determines the requested energy/range cannot be met by departure time; charging continues at max rate",
        "3A": "SE requests the EV unlock its inlet (non-binding)", "3B": "Proximity power requested",
        "3C": "SE detects proximity out of range", "FF": "Empty"
    }

    # Initialize separate lists for data and frame numbers
    data_lines = []
    frame_lines = []

    data_lines.append(f"SeInfoPageNumber: {page_num}")
    frame_lines.append(format_frame(page_frame))

    # Add SeInfoEntry lines
    for i, (val_hex, frame_no) in enumerate(entry_vals, start=1):
        desc = SeInfoCodeMap.get(val_hex, "Reserved or Unknown")
        data_lines.append(f"SeInfoEntry{i}: {val_hex} → {desc}")
        # FIX: Use format_frame for the time toggle
        frame_lines.append(format_frame(frame_no))

    # --- Construct the final HTML table with two columns ---
    html_parts = []
    html_parts.append("<div style='text-align:left;'>")
    html_parts.append(
        "<table style='border-collapse:collapse;width:100%;table-layout:fixed;text-align:left;margin:0;'>"
    )
    html_parts.append("<colgroup><col style='width:70%;'/><col style='width:30%;'/></colgroup>")

    # Determine the maximum number of rows needed
    max_len = max(len(data_lines), len(frame_lines))

    for i in range(max_len):
        # Retrieve each column's content, or use an empty string if index out of range
        data = data_lines[i] if i < len(data_lines) else ""
        frame = frame_lines[i] if i < len(frame_lines) else ""

        html_parts.append("<tr>")
        html_parts.append(f"<td style='padding:3px;vertical-align:top;text-align:left'>{data}</td>")
        html_parts.append(f"<td style='padding:3px;vertical-align:top;text-align:right'>{frame}</td>")
        html_parts.append("</tr>")

    html_parts.append("</table></div>")

    final_html = "".join(html_parts)
    SeInfo_display.setHtml(final_html)

    hex_values = [val_hex for (val_hex, _) in entry_vals if val_hex.upper() != "FF" and val_hex != "N/A"]
    hex_list_str = ", ".join(hex_values)
    collapsible_SeInfo.toggle_button.setText(f"SeInfo: {hex_list_str}")


def update_CableNode_display(selected_frame, format_frame):
    """
    Shows CaProperty data in the 'cable_Node_display' with frame numbers
    or time, based on the toggle state.
    """
    cable_display = globals.cable_Node_display
    cable_node_frames = getattr(globals, "cable_node_frames", [])

    valid_frames = [frame for frame in cable_node_frames if frame["frame"] <= selected_frame]
    if not valid_frames:
        cable_display.setHtml("No CaProperty data available.")
        return

    newest_frame = max(valid_frames, key=lambda x: x["frame"])
    data_bytes = newest_frame["data"]
    if len(data_bytes) < 8:
        cable_display.setHtml("N/A")
        return

    frame_num = newest_frame["frame"]

    html_parts = ["<div style='text-align:left;'>",
                  "<table style='border-collapse:collapse;width:100%;table-layout:fixed;text-align:left;margin:0;'>",
                  "<colgroup><col style='width:70%;'/><col style='width:30%;'/></colgroup>"]

    def add_row(label, value, fno):
        html_parts.append(f"<tr><td style='padding:3px;vertical-align:top;'>{label}</td>"
                          f"<td style='padding:3px;vertical-align:top;text-align:right;'>{format_frame(fno)}</td></tr>")

    def fmt_field(raw):
        return "N/A" if raw == 0xFF else str(raw)

    version_byte = data_bytes[0]
    masked_version = version_byte & 0x7F
    add_row(color_if_na("CaVersion", fmt_field(masked_version)), "", frame_num)

    if masked_version == 1:
        add_row(color_if_na("CaResponseError", fmt_field(data_bytes[1] & 0x01)), "", frame_num)
        max_voltage = (data_bytes[3] << 8) | data_bytes[2]
        voltage_str = "N/A" if max_voltage == 0xFFFF else f"{max_voltage / 10.0:.1f}V"
        add_row(color_if_na("CaMaxVoltage", voltage_str), "", frame_num)
        for field, index in [("CaMaxCurrentL1", 4), ("CaMaxCurrentL2", 5), ("CaMaxCurrentL3", 6), ("CaMaxCurrentN", 7)]:
            raw = data_bytes[index]
            value_str = "N/A" if raw == 0xFF else f"{raw}A"
            add_row(color_if_na(field, value_str), "", frame_num)
    elif masked_version == 2:
        add_row(color_if_na("CaResponseError", fmt_field(data_bytes[1] & 0x01)), "", frame_num)
        add_row(color_if_na("CaConnectorType", fmt_field(data_bytes[1] >> 1)), "", frame_num)
        add_row(color_if_na("CaInslClassL1N", fmt_field(data_bytes[2] & 0x0F)), "", frame_num)
        add_row(color_if_na("CaInslClassLL", fmt_field(data_bytes[2] >> 4)), "", frame_num)
        for field, bit_index in [("CaPrestL1", 0), ("CaPrestL2", 1), ("CaPrestL3", 2), ("CaPrestN", 3)]:
            raw = (data_bytes[3] >> bit_index) & 0x01
            add_row(color_if_na(field, str(raw)), "", frame_num)
        for field, index in [("CaMaxCurrentL", 4), ("CaMaxCurrentN", 5)]:
            raw = data_bytes[index]
            value_str = "N/A" if raw == 0xFF else f"{raw}A"
            add_row(color_if_na(field, value_str), "", frame_num)
        add_row(color_if_na("CaPlugTemp", fmt_field(data_bytes[6])), "", frame_num)
        add_row(color_if_na("CaConnectorTemp", fmt_field(data_bytes[7])), "", frame_num)
    else:
        html_parts.append(
            f"<tr><td colspan='2'>Unsupported CaVersion: {version_byte:02X} {format_frame(frame_num)}</td></tr>")

    html_parts.append("</table></div>")
    cable_display.setHtml("\n".join(html_parts))


def update_sleep_connection_display(selected_frame, op_data_timeline, sleep_connection_display, format_frame):
    """
    Update the 'sleep_connection_display' QTextEdit to show
    SeConnectionType, EvConnectionType, EvResponseError, and EvAwake
    in four fixed columns, leaving blanks instead of '(Frame 0)'.
    """
    collapsible_sleep_Connection = globals.collapsible_sleep_Connection

    chosen_data = None
    for (fno, data_dict) in reversed(op_data_timeline):
        if fno <= selected_frame:
            chosen_data = data_dict
            break
    if not chosen_data:
        sleep_connection_display.setText("No Sleep and Connection data available")
        collapsible_sleep_Connection.toggle_button.setText("Sleep and Connection:")
        collapsible_sleep_Connection.label_header.setText("")
        return

    se_conn, se_frame = chosen_data.get("SeConnectionType", ("", 0))
    ev_conn, ev_frame = chosen_data.get("EvConnectionType", ("", 0))
    ev_err, err_frame = chosen_data.get("EvResponseError", ("", 0))
    ev_awake, awake_frame = chosen_data.get("EvAwake", ("", 0))

    def color_for_status(s):
        s = s.lower()
        if s in ("ok", "connected", "active"): return "green"
        if s in ("error", "disconnected", "inactive"): return "red"
        if s in ("warning", "slow"): return "orange"
        return "black"

    # HTML table
    html = [
        "<div style='text-align:left;'>",
        "<table style='border-collapse:collapse;width:100%;table-layout:fixed;text-align:left;margin:0;'>",
        "<colgroup>"
        "<col style='width:35%;'/><col style='width:15%;'/>"
        "<col style='width:35%;'/><col style='width:15%;'/>"
        "</colgroup>",
    ]

    # Row 1  ─ SeConnectionType  |  EvResponseError
    html.append(
        f"<tr>"
        f"<td style='padding:3px;'>SeConnectionType: "
        f"<span style='color:{color_for_status(se_conn)};'>{se_conn}</span></td>"
        f"<td style='padding:3px;text-align:right;'>{format_frame(se_frame)}</td>"
        f"<td style='padding:3px;'>EvResponseError: "
        f"<span style='color:{color_for_status(ev_err)};'>{ev_err}</span></td>"
        f"<td style='padding:3px;text-align:right;'>{format_frame(err_frame or ev_frame)}</td>"
        f"</tr>"
    )

    # Row 2  ─ EvConnectionType  |  EvAwake
    html.append(
        f"<tr>"
        f"<td style='padding:3px;'>EvConnectionType: "
        f"<span style='color:{color_for_status(ev_conn)};'>{ev_conn}</span></td>"
        f"<td style='padding:3px;text-align:right;'>{format_frame(ev_frame)}</td>"
        f"<td style='padding:3px;'>EvAwake: "
        f"<span style='color:{color_for_status(ev_awake)};'>{ev_awake}</span></td>"
        f"<td style='padding:3px;text-align:right;'>{format_frame(awake_frame or ev_frame)}</td>"
        f"</tr>"
    )

    html.append("</table></div>")
    sleep_connection_display.setHtml("".join(html))


def update_Op3EvID_display(selected_frame, op_data_timeline, Op3EvID_display, format_frame):
    """
    Renders the most recent EvID fields for the ID stage in the "ev id stage" tab,
    based on Table 4 of the J3068-1 draft.
    """
    op_snap = next((s for f, s in reversed(op_data_timeline) if f <= selected_frame), None)
    if not op_snap:
        Op3EvID_display.setText("No EvID stage available.")
        return

    # EV keys.
    ev_id_keys = {
        "EvVIN": op_snap,
        "EvEMAID": op_snap,
        "EvEVCCID": op_snap,
        "EvSerialNum": op_snap,
        "EvDriverID": op_snap,
        "EvVehicleName": op_snap,
        "EvFirmwareRevision": op_snap,
        "EvManufacturer": op_snap,
        "EvPropDataIdent": op_snap,
        "EvPropDataRev": op_snap,
        "EvPropDataSymb": op_snap
    }

    na_strings = {"n/a", "decode error"}

    html = [
        "<div style='text-align:left;'><table style='border-collapse:collapse;width:100%;table-layout:fixed;text-align:left;'>",
        "<colgroup><col style='width:70%;'/><col style='width:30%;'/></colgroup>"]

    for key, source in ev_id_keys.items():
        val, frame_no = source.get(key, ("N/A", 0))

        # Conditionally hide row if toggle is active and value is N/A-like
        val_str_lower = str(val).lower()
        is_na = any(sub in val_str_lower for sub in na_strings)
        if globals.na_toggle_active and is_na:
            continue

        html.append(f"<tr><td style='padding:3px;'>{key}: {val}</td>"
                    f"<td style='text-align:right;padding:3px;'>{format_frame(frame_no)}</td></tr>")

    html.append("</table></div>")
    scrollbar = Op3EvID_display.verticalScrollBar()
    old_value = scrollbar.value()
    Op3EvID_display.setHtml("".join(html))
    scrollbar.setValue(old_value)


def update_Op3SeID_display(selected_frame, op_data_timeline, Op3SeID_display, format_frame):
    """
    Renders the most recent SeID fields for the ID stage in the "se id stage" tab,
    based on Table 7 of the J3068-1 draft.
    """
    op_snap = next((s for f, s in reversed(op_data_timeline) if f <= selected_frame), None)
    if not op_snap:
        Op3SeID_display.setText("No SeID stage available.")
        return

    # SE keys. the sewifi stuff not tested
    se_id_keys = {
        "SeEVSEID": op_snap,
        "SeSECCID": op_snap,
        "SeSerialNum": op_snap,
        "SeFirmwareRevision": op_snap,
        "SeManufacturer": op_snap,
        "SePublicName": op_snap,
        "SePlcEui48Address": op_snap,
        "SeWiFiEui64Address1": op_snap,
        "SeWiFiEui64Address2": op_snap,
        "SeWiFiEui64Address3": op_snap,
        "SeWiFiEui64Address4": op_snap,
        "SeWiFiEui64Address5": op_snap,
        "SeWiFiEui64Address6": op_snap,
        "SeWiFiEui64Address7": op_snap,
    }

    na_strings = {"n/a", "decode error"}

    html = [
        "<div style='text-align:left;'><table style='border-collapse:collapse;width:100%;table-layout:fixed;text-align:left;'>",
        "<colgroup><col style='width:70%;'/><col style='width:30%;'/></colgroup>"]

    for key, source in se_id_keys.items():
        val, frame_no = source.get(key, ("N/A", 0))

        # Conditionally hide row if toggle is active and value is N/A-like
        val_str_lower = str(val).lower()
        is_na = any(sub in val_str_lower for sub in na_strings)
        if globals.na_toggle_active and is_na:
            continue

        html.append(f"<tr><td style='padding:3px;'>{key}: {val}</td>"
                    f"<td style='text-align:right;padding:3px;'>{format_frame(frame_no)}</td></tr>")

    html.append("</table></div>")
    scrollbar = Op3SeID_display.verticalScrollBar()
    old_value = scrollbar.value()
    Op3SeID_display.setHtml("".join(html))
    scrollbar.setValue(old_value)


# --------------- Paste in Code Gen code for update Functions here -----------------might need this------------------
def update_ev_data_tab(selected_frame, init_data, op_data, ver_data, display_widget, format_frame):
    """
    Populates the 'ev data' tab with a consolidated view of EV-related data.
    """
    # Find the most recent snapshot for each timeline
    init_snap = next((s for f, s in reversed(init_data) if f <= selected_frame), {})
    op_snap = next((s for f, s in reversed(op_data) if f <= selected_frame), {})
    ver_snap = next((s for f, s in reversed(ver_data) if f <= selected_frame), {})

    # An ordered list of keys for the "ev data" tab.
    ev_keys = [
        # Keys from op_data (Live Operation & EvID Data Stage)
        "EvOdometer", "EvStatusInletLatch", "EvStatusInletOverride", "EvStatusInletLock",
        "EvNumberJ2012Dtcs", "EvJ2012DtcStatus", "EvJ2012DtcCount", "EvHVESSDishargeCapacity",
        "EvHVESSChargeCapacity", "EvEnergyForDeparture", "EvTimeToDeparture",
        "EvHVESSRange", "EvFuelRange", "EvEVTimeToEnergyForDept", "EvDurMin", "EvChaDurMax",
        "EvDschDurMax", "EvTimeReqNum", "EvEVTimeToRange", "EvEVTimeToEnergy",
        "EvHVESSVoltage", "EvHVESSCurrent", "EvHVESSHealth", "EvHVESSUserSOC",
        "EvACActivePower", "EvACReactivePower", "EvACFrequency",
        "EvL1NVolts", "EvL2NVolts", "EvL3NVolts",
        "EvAmbientTemp", "EvCabinTemp",
        "EvHVESSCellTemp", "EvMaxHVESSTemp", "EvMinHVESSTemp", "EvHVESSElecTemp",
        "EvMaxHVESSCellVolt", "EvMinHVESSCellVolt", "EvNumHVESSCellBalancing",
        "EvStatusCellVoltDiff", "EvStatusCellBal", "EvActiveCellBal",
        "EvChargerTemp", "EvMaxChargerTemp", "EvInletTemp", "EvHVESSTemp"
    ]

    na_strings = {"n/a", "not_supported", "none_or_status_unknown", "error", "reserved"}

    html = [
        "<div style='text-align:left;'><table style='border-collapse:collapse;width:100%;table-layout:fixed;text-align:left;'>",
        "<colgroup><col style='width:70%;'/><col style='width:30%;'/></colgroup>"]

    found_any_data = False
    for key in ev_keys:
        val, frame_no = ("N/A", 0)
        # Check snapshots in order of preference: op -> init -> ver
        source_snap = None
        if key in op_snap:
            source_snap = op_snap
        elif key in init_snap:
            source_snap = init_snap
        elif key in ver_snap:
            source_snap = ver_snap

        if source_snap:
            val, frame_no = source_snap.get(key, ("N/A", 0))
            found_any_data = True

        # Conditionally hide row if toggle is active and value is N/A-like
        val_str_lower = str(val).lower()
        is_na = any(sub in val_str_lower for sub in na_strings)
        if globals.na_toggle_active and is_na:
            continue

        # Always display the row, showing N/A if the data doesn't exist for the selected frame
        html.append(f"<tr><td style='padding:3px;'>{key}: {val}</td>"
                    f"<td style='text-align:right;padding:3px;'>{format_frame(frame_no)}</td></tr>")

    if not found_any_data:
        display_widget.setHtml("No EV data available for this frame.")
        return

    html.append("</table></div>")
    scrollbar = display_widget.verticalScrollBar()
    old_value = scrollbar.value()
    display_widget.setHtml("".join(html))
    scrollbar.setValue(old_value)


def update_se_data_tab(selected_frame, init_data, op_data, ver_data, display_widget, format_frame):
    """
    Populates the 'se data' tab with a consolidated view of SE-related data,
    including fields from Table 8 of the J3068-1 draft.
    """
    # Find the most recent snapshot for each timeline
    op_snap = next((s for f, s in reversed(op_data) if f <= selected_frame), {})

    if not op_snap:
        display_widget.setHtml("<div style='padding:10px;'>No SE data available for this frame.</div>")
        return

    # Define all possible SE keys and their sources
    se_keys = {
        # Table 8 Data (from SeID frame, stored in op_data)
        "SeAmbientTemp": op_snap,
        "SeConnectorTemp": op_snap,
        "SeOutletTemp": op_snap,
        "SeEvStatusOutletOverride": op_snap,
        "SeEvStatusOutletLock": op_snap,
        "SeRmtMgmtStatus": op_snap,
        "SeEvTripStatus": op_snap,
        "SeSeTripStatus": op_snap,
        "SeExptTripPerct": op_snap,
        "SeTimeReqNum": op_snap,
        "SeHVESSRangeCalc": op_snap,
        "SeHVESSEnergyCalc": op_snap,
    }

    na_strings = {"n/a", "not_supported", "none_or_status_unknown", "error", "reserved", "invalid"}

    html = [
        "<div style='text-align:left;'><table style='border-collapse:collapse;width:100%;table-layout:fixed;text-align:left;'>",
        "<colgroup><col style='width:70%;'/><col style='width:30%;'/></colgroup>"]

    # Iterate through the keys and populate the HTML table
    for key, source in se_keys.items():
        # Default to "N/A" if the key is not in the source snapshot
        val, frame_no = source.get(key, ("N/A", 0))

        # Conditionally hide row if toggle is active and value is N/A-like
        val_str_lower = str(val).lower()
        is_na = any(sub in val_str_lower for sub in na_strings)
        if globals.na_toggle_active and is_na:
            continue

        html.append(f"<tr><td style='padding:3px;'>{key}: {val}</td>"
                    f"<td style='text-align:right;padding:3px;'>{format_frame(frame_no)}</td></tr>")

    html.append("</table></div>")

    # Preserve scrollbar position when updating the widget
    scrollbar = display_widget.verticalScrollBar()
    old_value = scrollbar.value()
    display_widget.setHtml("".join(html))
    scrollbar.setValue(old_value)


def update_control_page_display(selected_frame, op_data_timeline, control_page_display, format_frame):
    """
    Update the 'control_page_display' to show SE and EV control page data
    in a four-column layout, similar to the protocol version display.
    op3
    """
    collapsible_control_page = globals.collapsible_control_page

    snap = next((s for f, s in reversed(op_data_timeline) if f <= selected_frame), None)

    if not snap:
        control_page_display.setHtml("No Control Page data available.")
        collapsible_control_page.toggle_button.setText("OP3 Control Page:")
        collapsible_control_page.label_header.setText("")
        return

    # Define the keys to be displayed for SE and EV control pages
    se_keys = [
        "SeIDStatus", "SeNumIDPages", "SeFirstIDPage",
        "SeLastIDPage", "SeCrcStatus", "SeNumPropPages"
    ]
    ev_keys = [
        "EvIDStatus", "EvNumIDPages", "EvFirstIDPage",
        "EvLastIDPage", "EvCrcStatus", "EvNumPropPages"
    ]

    left_col, right_col = [], []

    # Populate the left (SE) column
    for key in se_keys:
        val, fno = snap.get(key, ("N/A", 0))
        left_col.append((f"{key}: {val}", format_frame(fno)))

    # Populate the right (EV) column
    for key in ev_keys:
        val, fno = snap.get(key, ("N/A", 0))
        right_col.append((f"{key}: {val}", format_frame(fno)))

    # Pad the shorter column to ensure the table is rectangular
    max_len = max(len(left_col), len(right_col))
    while len(left_col) < max_len:
        left_col.append(("", ""))
    while len(right_col) < max_len:
        right_col.append(("", ""))

    # Build the four-column HTML table
    html_parts = [
        "<div style='text-align:left;'>",
        "<table style='border-collapse:collapse;width:100%;table-layout:fixed;'>",
        "<colgroup><col style='width:35%;'/><col style='width:15%;'/><col style='width:35%;'/><col style='width:15%;'/></colgroup>",
    ]
    for (se_text, se_frame), (ev_text, ev_frame) in zip(left_col, right_col):
        html_parts.append(
            "<tr>"
            f"<td style='padding:3px;'>{se_text}</td>"
            f"<td style='padding:3px;text-align:right;'>{se_frame}</td>"
            f"<td style='padding:3px;'>{ev_text}</td>"
            f"<td style='padding:3px;text-align:right;'>{ev_frame}</td>"
            "</tr>"
        )
    html_parts.append("</table></div>")
    final_html = "".join(html_parts)
    control_page_display.setHtml(final_html)

    # Set the collapsible box header text as requested
    collapsible_control_page.toggle_button.setText("OP3 Control Page:")
    collapsible_control_page.label_header.setText("")  # No text next to the toggle button

# Start of J3068/2 functions

def update_OP252_control_page_display(selected_frame, op_data_timeline, OP252_control_page_display, format_frame):
    """
    Update the 'op252 control_page_display' to show SE and EV control page data for J3072
    in a four-column layout, similar to the protocol version display.
    op252
    """
    collapsible_OP252_control_page = globals.collapsible_OP252_control_page

    snap = next((s for f, s in reversed(op_data_timeline) if f <= selected_frame), None)

    if not snap:
        OP252_control_page_display.setHtml("No Control Page data available.")
        collapsible_OP252_control_page.toggle_button.setText("OP252 Control Page:")
        collapsible_OP252_control_page.label_header.setText("")
        return

    # Define the keys to be displayed for SE and EV control pages
    se_keys = [
        "SeJ3072Status", "SeNumJ3072Pages", "SeFirstJ3072Page",
        "SeLastJ3072Page", "SeJ3072CrcStatus"
    ]
    ev_keys = [
        "EvJ3072Status", "EvNumJ3072Pages", "EvFirstJ3072Page",
        "EvLastJ3072Page", "EvJ3072CrcStatus"
    ]

    left_col, right_col = [], []

    # Populate the left (SE) column
    for key in se_keys:
        val, fno = snap.get(key, ("N/A", 0))
        left_col.append((f"{key}: {val}", format_frame(fno)))

    # Populate the right (EV) column
    for key in ev_keys:
        val, fno = snap.get(key, ("N/A", 0))
        right_col.append((f"{key}: {val}", format_frame(fno)))

    # Pad the shorter column to ensure the table is rectangular
    max_len = max(len(left_col), len(right_col))
    while len(left_col) < max_len:
        left_col.append(("", ""))
    while len(right_col) < max_len:
        right_col.append(("", ""))

    # Build the four-column HTML table
    html_parts = [
        "<div style='text-align:left;'>",
        "<table style='border-collapse:collapse;width:100%;table-layout:fixed;'>",
        "<colgroup><col style='width:35%;'/><col style='width:15%;'/><col style='width:35%;'/><col style='width:15%;'/></colgroup>",
    ]
    for (se_text, se_frame), (ev_text, ev_frame) in zip(left_col, right_col):
        html_parts.append(
            "<tr>"
            f"<td style='padding:3px;'>{se_text}</td>"
            f"<td style='padding:3px;text-align:right;'>{se_frame}</td>"
            f"<td style='padding:3px;'>{ev_text}</td>"
            f"<td style='padding:3px;text-align:right;'>{ev_frame}</td>"
            "</tr>"
        )
    html_parts.append("</table></div>")
    final_html = "".join(html_parts)
    OP252_control_page_display.setHtml(final_html)

    # Set the collapsible box header text as requested
    collapsible_OP252_control_page.toggle_button.setText("OP252 Control Page:")
    collapsible_OP252_control_page.label_header.setText("")  # No text next to the toggle button


def update_EvModeCtrl_display(selected_frame, op_data_timeline, EvModeCtrl_display, format_frame):
    """
    Update the 'EvModeCtrl_display' to show EV power control mode data.
    """
    collapsible_EvModeCtrl = globals.collapsible_EvModeCtrl

    snap = next((s for f, s in reversed(op_data_timeline) if f <= selected_frame), None)

    if not snap:
        EvModeCtrl_display.setHtml("No EvModeCtrl data available.")
        collapsible_EvModeCtrl.toggle_button.setText("EvModeCtrl:")
        collapsible_EvModeCtrl.label_header.setText("")
        return

    keys_to_display = [
        "EvGridCodeStatus", "EvGridCodeStatusMod", "EvInverterState",
        "EvPwrCtrlModeAck", "EvPwrCtrlUnitsAvail", "EvPwrCtrlModesAvail"
    ]

    html_parts = [
        "<div style='text-align:left;'>",
        "<table style='border-collapse:collapse;width:100%;table-layout:fixed;'>",
        "<colgroup><col style='width:70%;'/><col style='width:30%;'/></colgroup>",
    ]

    # Iterate through keys and build table rows
    for key in keys_to_display:
        val, fno = snap.get(key, ("N/A", 0))
        display_val = (val[:40] + '...') if len(str(val)) > 40 else val

        html_parts.append(
            "<tr>"
            f"<td style='padding:3px;vertical-align:top;'>{key}: {display_val}</td>"
            f"<td style='padding:3px;text-align:right;'>{format_frame(fno)}</td>"
            "</tr>"
        )

    html_parts.append("</table></div>")
    final_html = "".join(html_parts)
    EvModeCtrl_display.setHtml(final_html)

    # Set the collapsible box header text
    collapsible_EvModeCtrl.toggle_button.setText("EvModeCtrl:")
    # Set the label next to the toggle button based on the acknowledged mode
    ack_mode, _ = snap.get("EvPwrCtrlModeAck", ("N/A", 0))
    ack_color = "green" if ack_mode not in ["N/A", "Processing", "Invalid/Reserved", "Normal Charging"] else "gray"
    collapsible_EvModeCtrl.label_header.setText(f"<span style='color:{ack_color};font-size:8pt;'> {ack_mode}</span>")

def update_SeModeCtrl_display(selected_frame, op_data_timeline, SeModeCtrl_display, format_frame):
    """
    Update the 'SeModeCtrl_display' to show SE power control mode data.
    """
    collapsible_SeModeCtrl = globals.collapsible_SeModeCtrl_page

    snap = next((s for f, s in reversed(op_data_timeline) if f <= selected_frame), None)

    if not snap:
        SeModeCtrl_display.setHtml("No SeModeCtrl data available.")
        collapsible_SeModeCtrl.toggle_button.setText("SeModeCtrl:")
        collapsible_SeModeCtrl.label_header.setText("")
        return

    keys_to_display = [
        "SeGridCodeRequest", "SeInverterRequest", "SePwrCtrlMode",
        "SePwrCtrlUnits", "SePwrCtrlAuth", "SeTimeStamp"
    ]

    html_parts = [
        "<div style='text-align:left;'>",
        "<table style='border-collapse:collapse;width:100%;table-layout:fixed;'>",
        "<colgroup><col style='width:70%;'/><col style='width:30%;'/></colgroup>",
    ]

    for key in keys_to_display:
        val, fno = snap.get(key, ("N/A", 0))
        display_val = (val[:40] + '...') if len(str(val)) > 40 else val

        html_parts.append(
            "<tr>"
            f"<td style='padding:3px;vertical-align:top;'>{key}: {display_val}</td>"
            f"<td style='padding:3px;text-align:right;'>{format_frame(fno)}</td>"
            "</tr>"
        )

    html_parts.append("</table></div>")
    final_html = "".join(html_parts)
    SeModeCtrl_display.setHtml(final_html)

    collapsible_SeModeCtrl.toggle_button.setText("SeModeCtrl:")
    req_mode, _ = snap.get("SePwrCtrlMode", ("N/A", 0))
    req_color = "green" if req_mode not in ["N/A", "Processing", "Invalid/Reserved", "Normal Charging"] else "gray"
    collapsible_SeModeCtrl.label_header.setText(f"<span style='color:{req_color};font-size:8pt;'> {req_mode}</span>")


def update_EvJ3072_display(selected_frame, op_data_timeline, EvJ3072_tab_display, format_frame):
    """
    Renders the most recent EvJ3072 fields for the certification stage.
    """
    op_snap = next((s for f, s in reversed(op_data_timeline) if f <= selected_frame), None)
    if not op_snap:
        EvJ3072_tab_display.setHtml("No EvJ3072 data available.")
        return

    # Keys that are being parsed in display_frames
    ev_j3072_keys = [
        "EvPwrCtrlModesSpt", "EvSupGridCode1", "EvSupGridCode2", "EvSupGridCode3", "EvSupGridCode4", "EvSupGridCode5",
        "EvSupGridCode6", "EvSupGridCode7", "EvSupGridCode8", "EvSupGridCode9", "EvSupGridCode10", "EvSupGridCode11",
        "EvRemGridCode", "EvVRefL1N", "EvVRefLL", "EvWMaxRtg","EvVAMaxRtg", "EvIvarMaxRtg", "EvAvarMaxRtg",
        "EvChaWMaxRtg", "EvChaVAMaxRtg", "EvInverterSMN", "EvCertificationDate", "EvUpdateTime"
    ]

    na_strings = {"n/a", "decode error", "not available"}
    html = ["<div style='text-align:left;'><table style='border-collapse:collapse;width:100%;table-layout:fixed;text-align:left;'>",
            "<colgroup><col style='width:70%;'/><col style='width:30%;'/></colgroup>"]

    found_any_data = False
    for key in ev_j3072_keys:
        val, frame_no = op_snap.get(key, ("N/A", 0))
        if val != "N/A":
            found_any_data = True
        if globals.na_toggle_active and any(sub in str(val).lower() for sub in na_strings):
            continue
        html.append(f"<tr><td style='padding:3px; word-wrap:break-word;'>{key}: {val}</td>"
                    f"<td style='text-align:right;padding:3px;'>{format_frame(frame_no)}</td></tr>")

    if not found_any_data:
        EvJ3072_tab_display.setHtml("No EvJ3072 data available for this frame.")
        return

    html.append("</table></div>")
    scrollbar = EvJ3072_tab_display.verticalScrollBar()
    old_value = scrollbar.value()
    EvJ3072_tab_display.setHtml("".join(html))
    scrollbar.setValue(old_value)


def update_SeJ3072_display(selected_frame, op_data_timeline, SeJ3072_tab_display, format_frame):
    """
    Renders the most recent SeJ3072 fields for the certification stage.
    """
    op_snap = next((s for f, s in reversed(op_data_timeline) if f <= selected_frame), None)
    if not op_snap:
        SeJ3072_tab_display.setHtml("No SeJ3072 data available.")
        return

    # Keys that are being parsed in display_frames
    se_j3072_keys = [
        "SePwrCtrlModesSpt", "SeWMaxEVSE", "SeChaWMaxEVSE", "SeIvarMaxEVSE", "SeAvarMaxEVSE",
        "SeUpdateTimeEVSE", "SeFreqOver1FreqA", "SeFreqOver1TimeA", "SeFreqOver2FreqA", "SeFreqOver2TimeA",
        "SeFreqUnder1FreqA", "SeFreqUnder1TimeA", "SeFreqUnder2FreqA", "SeFreqUnder2TimeA",
        "SeLV3hLV2lLNA", "SeLV3TimeA", "SeLV2hLV1lLNA", "SeLV2TimeA", "SeLV1hLNA", "SeLV1TimeA",
        "SeHV1lLNA", "SeHV1TimeA", "SeHV1hHV2lLNA", "SeHV2TimeA", "SeFreqOver1FreqB", "SeFreqOver1TimeB",
        "SeFreqOver2FreqB", "SeFreqOver2TimeB", "SeFreqUnder1FreqB", "SeFreqUnder1TimeB", "SeFreqUnder2FreqB",
        "SeFreqUnder2TimeB", "SeLV3hLV2lLNB", "SeLV3TimeB", "SeLV2hLV1lLNB", "SeLV2TimeB", "SeLV1hLNB",
        "SeLV1TimeB", "SeHV1lLNB", "SeHV1TimeB", "SeHV1hHV2lLNB", "SeHV2TimeB"
    ]

    na_strings = {"n/a", "decode error", "not available"}
    html = ["<div style='text-align:left;'><table style='border-collapse:collapse;width:100%;table-layout:fixed;text-align:left;'>",
            "<colgroup><col style='width:70%;'/><col style='width:30%;'/></colgroup>"]

    found_any_data = False
    for key in se_j3072_keys:
        val, frame_no = op_snap.get(key, ("N/A", 0))
        if val != "N/A":
            found_any_data = True
        if globals.na_toggle_active and any(sub in str(val).lower() for sub in na_strings):
            continue
        html.append(f"<tr><td style='padding:3px; word-wrap:break-word;'>{key}: {val}</td>"
                    f"<td style='text-align:right;padding:3px;'>{format_frame(frame_no)}</td></tr>")

    if not found_any_data:
        SeJ3072_tab_display.setHtml("No SeJ3072 data available for this frame.")
        return

    html.append("</table></div>")
    scrollbar = SeJ3072_tab_display.verticalScrollBar()
    old_value = scrollbar.value()
    SeJ3072_tab_display.setHtml("".join(html))
    scrollbar.setValue(old_value)

def update_SeTargets1_display(selected_frame, op_data_timeline, SeTargets1_display, format_frame):
    """
    Interpret and display the SeTargets1 frame data based on the selected SePwrCtrlUnits.
    """
    collapsible_SeTargets1 = globals.collapsible_SeTargets1_page

    snap = next((s for f, s in reversed(op_data_timeline) if f <= selected_frame), None)

    if not snap or "SeTargets1ElementA" not in snap:
        SeTargets1_display.setHtml("No SeTargets1 data available.")
        collapsible_SeTargets1.toggle_button.setText("SeTargets1:")
        collapsible_SeTargets1.label_header.setText("")
        return

    units_mode, _ = snap.get("SePwrCtrlUnits", ("N/A", 0))
    collapsible_SeTargets1.toggle_button.setText("SeTargets1:")
    collapsible_SeTargets1.label_header.setText(f"<span style='font-size:8pt;'> {units_mode}</span>")

    val_a, fno_a = snap.get("SeTargets1ElementA", (0xFFFF, 0))
    val_b, fno_b = snap.get("SeTargets1ElementB", (0xFFFF, 0))
    val_c, fno_c = snap.get("SeTargets1ElementC", (0xFFFF, 0))
    val_d, fno_d = snap.get("SeTargets1ElementD", (0xFFFF, 0))

    def to_signed(val):
        return val - 65536 if val > 32767 else val

    rows = []
    # SePwrCtrlUnits
    if units_mode == "% Max Watt":
        target_w = (to_signed(val_a) / 256.0) - 125.0
        rows.append((f"Target Power: {target_w:.2f} %", fno_a))
    elif units_mode == "Current per phase":
        target_l1 = (val_a * 0.05) - 1600
        target_l2 = (val_b * 0.05) - 1600
        target_l3 = (val_c * 0.05) - 1600
        rows.extend([
            (f"Target L1 Current: {target_l1:.2f} A", fno_a),
            (f"Target L2 Current: {target_l2:.2f} A", fno_b),
            (f"Target L3 Current: {target_l3:.2f} A", fno_c)
        ])
    elif units_mode == "Total Watt":
        target_w = (val_a * 16) - 500000
        rows.append((f"Target Power: {target_w} W", fno_a))
    elif units_mode == "% Max Watt + % Max VAR":
        target_w = (to_signed(val_a) / 256.0) - 125.0
        target_var = (to_signed(val_b) / 256.0) - 125.0
        rows.extend([
            (f"Target Power: {target_w:.2f} %", fno_a),
            (f"Target Reactive Power: {target_var:.2f} %", fno_b)
        ])
    elif units_mode == "Current per phase + power factor":
        target_l1 = (val_a * 0.05) - 1600
        target_l2 = (val_b * 0.05) - 1600
        target_l3 = (val_c * 0.05) - 1600
        target_pf = (val_d / 16384.0) - 1.0
        rows.extend([
            (f"Target L1 Current: {target_l1:.2f} A", fno_a),
            (f"Target L2 Current: {target_l2:.2f} A", fno_b),
            (f"Target L3 Current: {target_l3:.2f} A", fno_c),
            (f"Target Power Factor: {target_pf:.4f}", fno_d)
        ])
    elif units_mode == "Current per phase + phase angle":
        target_l1 = (val_a * 0.05) - 1600
        target_l2 = (val_b * 0.05) - 1600
        target_l3 = (val_c * 0.05) - 1600
        target_phi = (val_d / 128.0) - 200
        rows.extend([
            (f"Target L1 Current: {target_l1:.2f} A", fno_a),
            (f"Target L2 Current: {target_l2:.2f} A", fno_b),
            (f"Target L3 Current: {target_l3:.2f} A", fno_c),
            (f"Target Phase Angle: {target_phi:.2f}°", fno_d)
        ])
    elif units_mode == "Total Watt + Total VAR":
        target_w = (val_a * 16) - 500000
        target_var = (val_b * 16) - 500000
        rows.extend([
            (f"Target Power: {target_w} W", fno_a),
            (f"Target Reactive Power: {target_var} VAR", fno_b)
        ])
    else:
        rows.append(("Units mode not yet set", 0))
        rows.append((f"Raw A: 0x{val_a:04X}", fno_a))
        rows.append((f"Raw B: 0x{val_b:04X}", fno_b))
        rows.append((f"Raw C: 0x{val_c:04X}", fno_c))
        rows.append((f"Raw D: 0x{val_d:04X}", fno_d))

    html_parts = [
        "<div style='text-align:left;'>",
        "<table style='border-collapse:collapse;width:100%;table-layout:fixed;'>",
        "<colgroup><col style='width:70%;'/><col style='width:30%;'/></colgroup>",
    ]
    for text, fno in rows:
        if val_a == 0xFFFF and "Raw" not in text:
            text = text.split(':')[0] + ": N/A"
        html_parts.append(
            "<tr>"
            f"<td style='padding:3px;vertical-align:top;'>{text}</td>"
            f"<td style='padding:3px;text-align:right;'>{format_frame(fno)}</td>"
            "</tr>"
        )
    html_parts.append("</table></div>")
    SeTargets1_display.setHtml("".join(html_parts))