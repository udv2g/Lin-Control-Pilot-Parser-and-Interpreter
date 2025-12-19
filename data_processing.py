import re
import globals

def format_frame(fno):
    """
    Formats the display for a frame number.
    If frame_time_toggle is active, it shows the elapsed time since the
    start of the live data session. Otherwise, it shows the frame number.
    """
    if not isinstance(fno, int) or fno <= 0:
        return ""

    if not globals.frame_time_active:
        # Toggle is OFF, show frame number as before
        return f"(Frame: {fno})"
    else:
        # Toggle is ON, show time since the timer started.
        try:
            # Find the timestamp for the current frame
            frame_type_key = globals.all_frame_types[fno - 1]
            timestamps_for_type = globals.frame_timestamps.get(frame_type_key, [])

            current_ts = None
            # This loop finds the specific timestamp for the frame number 'fno'
            for frame_num, timestamp in timestamps_for_type:
                if frame_num == fno:
                    current_ts = timestamp
                    break

            # If found the frame's timestamp and the session start time is valid
            if current_ts is not None and globals.live_data_start_time > 0:
                time_diff = current_ts - globals.live_data_start_time

                # Handle negative time if the new zero point is after this frame
                prefix = "-" if time_diff < 0 else ""
                time_diff = abs(time_diff)

                # Format the time to build up (d, h, m, s)
                if time_diff >= 86400:  # Days
                    days, rem = divmod(time_diff, 86400)
                    hours, rem = divmod(rem, 3600)
                    minutes, seconds = divmod(rem, 60)
                    return f"({prefix}{int(days)}d {int(hours):02d}h {int(minutes):02d}m {int(seconds):02d}s)"
                elif time_diff >= 3600:  # Hours
                    hours, rem = divmod(time_diff, 3600)
                    minutes, seconds = divmod(rem, 60)
                    return f"({prefix}{int(hours):02d}h {int(minutes):02d}m {int(seconds):02d}s)"
                elif time_diff >= 60:  # Minutes
                    minutes, seconds = divmod(time_diff, 60)
                    return f"({prefix}{int(minutes):02d}m {seconds:06.3f}s)"
                else:  # Seconds
                    return f"({prefix}{time_diff:.3f}s)"
            else:
                return "(--s)"

        except (IndexError, TypeError):
            return "(--s)"

def format_id_status(byte_val, device_type):
    """
    Formats the display for EvIDStatus and SeIDStatus values.
    """
    remote_type = "SE" if device_type == "EV" else "EV"
    if byte_val == 0:
        return f"ID Not Ready"
    elif byte_val == 1:
        return '<span style="color:Brown;">ID Incomplete</span>'
    elif byte_val == 2:
        return '<span style="color:Green;">ID Complete</span>'
    elif byte_val == 3:
        return '<span style="color:Green;">Data</span>'
    elif byte_val == 254:
        return '<span style="color:red;">Error</span>'
    elif byte_val == 255:
        return '<span style="color:#cfcfcf;">N/A</span>'
    else:
        return f"Reserved ({byte_val})"



def format_crc_status(byte_val, device_type):
    """
    Formats the display for EvCrcStatus and SeCrcStatus values based on the table
    from J3068/1, Tables 6.1.10 and 6.1.63.
    """
    remote_type = "SE" if device_type == "EV" else "EV"
    status_map = {
        0x00: f"Not sent by {device_type} No check {remote_type} CRC",
        0x01: f"CRC not transmitted {device_type} Data and CRC from last {remote_type} cycle match",
        0x0E: f"CRC not transmitted {device_type} Data and CRC from last {remote_type} cycle do not match",
        0x0F: f"CRC not transmitted {device_type}, {device_type} no complete cycle from {remote_type} in this stage",
        0x10: f"CRC is transmitted {device_type}, {device_type} does not check {remote_type} CRC",
        0x11: f"CRC is transmitted by {device_type}, Data and CRC from last {remote_type} cycle match",
        0x1E: f"CRC is transmitted by {device_type}, Data and CRC from last {remote_type} cycle do not match",
        0x1F: f"CRC is transmitted by {device_type}, {device_type} has not yet received a complete cycle from the {remote_type} in this stage",
    }
    return status_map.get(byte_val, f"Reserved ({byte_val})")

def format_Num_Prop_Pages(byte_val, device_type):
    """
        Formats the display for EvNumPropPages and SeNumPropPages values based on the table
        from J3068/1
        """
    remote_type = "SE" if device_type == "EV" else "EV"
    if 0 <= byte_val <=250:
        return f"{byte_val} proprietary pages"

    elif byte_val == 254:
        return '<span style="color:red;">Error</span>'
    elif byte_val == 255:
        return '<span style="color:#cfcfcf;">No Transmission</span>'
    else:
        return f"Reserved ({byte_val})"




def format_selected_version(byte_val):
    if byte_val == 255:
        return '<span style="color:#cfcfcf;">N/A</span>'
    elif byte_val == 254:
        return '<span style="color:red;">error</span>'
    else:
        return str(byte_val)


def format_amp_value(byte_val):
    if byte_val == 255:
        return '<span style="color:#cfcfcf;">N/A</span>'
    elif byte_val == 254:
        return '<span style="color:red;">error</span>'
    else:
        return f"{byte_val}A"


def format_voltage_value(voltage_float):
    # Check if voltage_float indicates N/A or error
    if abs(voltage_float - 255.0) < 1e-9 or abs(voltage_float - 6553.5) < 1e-9:
        return '<span style="color:#cfcfcf;">N/A</span>'
    elif abs(voltage_float - 254.0) < 1e-9:
        return '<span style="color:red;">error</span>'
    else:
        return f"{voltage_float:.1f}V"


def compute_lin_enhanced_checksum(frame_id, databytes):
    id_bits = [(frame_id >> i) & 0x01 for i in range(6)]
    p0 = id_bits[0] ^ id_bits[1] ^ id_bits[2] ^ id_bits[4]
    p1_xor = id_bits[1] ^ id_bits[3] ^ id_bits[4] ^ id_bits[5]
    p1 = 0 if p1_xor == 1 else 1
    protected_id = (p1 << 7) | (p0 << 6) | (frame_id & 0x3F)

    checksum = protected_id
    for b in databytes:
        checksum += b
    checksum = checksum % 255
    checksum = (~checksum) & 0xFF
    return checksum, protected_id


def guess_format(file_content):
    lines = file_content.splitlines()
    lines = [l for l in lines if l.strip()]
    if not lines:
        return False
    first_line = lines[0]
    if " " in first_line:
        return True
    return False


def parse_hex_data(hex_data, is_spaced):
    if is_spaced:
        tokens = re.split(r'\s+', hex_data.strip())
        byte_list = [t.upper() for t in tokens if re.fullmatch(r'[0-9A-Fa-f]{2}', t)]
    else:
        cleaned = re.sub(r'[^0-9A-Fa-f]', '', hex_data)
        byte_list = [cleaned[i:i + 2].upper() for i in range(0, len(cleaned), 2) if len(cleaned[i:i + 2]) == 2]
    return byte_list


def parse_data_stream(byte_list, is_live_data=False):
    """
    Parses a list of hex byte strings to extract LIN frames and identify garbage data between them.
    This simplified version scans for a frame header and treats all preceding bytes as a 'garbage' chunk.
    """
    chunks = []
    buffer = list(byte_list)
    FULL_FRAME_LENGTH = 12

    while True:
        header_start = -1
        try:
            for i in range(len(buffer) - 1):
                if buffer[i] in ("00", "80") and buffer[i + 1] == "55":
                    header_start = i
                    break
        except IndexError:
            break

        if header_start == -1:
            break

        if header_start > 0:
            garbage = buffer[:header_start]
            chunks.append(('garbage', garbage))

        buffer = buffer[header_start:]

        if len(buffer) >= FULL_FRAME_LENGTH:
            frame = buffer[:FULL_FRAME_LENGTH]
            chunks.append(('frame', frame))
            buffer = buffer[FULL_FRAME_LENGTH:]
        else:
            break

    remainder_list = buffer
    return chunks, remainder_list


def evaluate_protocol_version(versions, version_name_map):
    """
    versions: list of possible protocol versions (ints or None)
    version_name_map: dict mapping version -> name
    returns: (chosen_version, chosen_name, color_code)
    """
    # Filter out invalid (None) versions
    valid_versions = [v for v in versions if v is not None]

    # Edge case: if no valid versions, we might treat it as 'unknown'
    if not valid_versions:
        return (None, "No valid version", "red")

    # Check if all valid versions match
    all_match = all(v == valid_versions[0] for v in valid_versions)

    if all_match:
        # All valid versions match
        chosen_version = valid_versions[0]
        chosen_name = version_name_map.get(chosen_version, "Unknown")

        # If # of valid == total #, color is green; else brown
        if len(valid_versions) == len(versions):
            color = "green"
        else:
            color = "brown"

        return (chosen_version, chosen_name, color)
    else:
        from collections import Counter
        counter = Counter(valid_versions)
        most_common_version, _ = counter.most_common(1)[0]

        chosen_version = most_common_version
        chosen_name = version_name_map.get(chosen_version, "Unknown")
        color = "red"  # any mismatch yields red

        return (chosen_version, chosen_name, color)


def determine_protocol_version(se_status_ver, se_status_init, se_status_op, se_selected_version):
    ver_str = se_status_ver.capitalize()
    init_str = se_status_init.capitalize()
    op_str = se_status_op.capitalize()

    if (ver_str in ["Incomplete", "Error"]) and (init_str in ["Incomplete", "Error"]) and (op_str == "Deny_v"):
        return "All"
    if (ver_str in ["Complete", "Error"]) and (init_str in ["Incomplete", "Error"]) and (op_str == "Deny_v"):
        return "All"
    if ver_str == "Complete" and init_str == "Complete" and op_str != "Not_Available":
        if se_selected_version == 2:
            return "2"
        elif se_selected_version == 3:
            return "3"
        else:
            return "Unknown"

    return "Unknown Protocol version"


def format_j3072_status(byte_val, device_type):
    """
    Formats the display for EvJ3072Status and SeJ3072Status values.
    """
    status_map = {
        0x00: "CERT NOT READY",
        0x01: '<span style="color:Brown;">CERT INCOMPLETE</span>',
        0x02: '<span style="color:Green;">CERT COMPLETE</span>',
        0x03: '<span style="color:Green;">SUNSPEC</span>',
        0xFE: '<span style="color:red;">Error</span>',
        0xFF: '<span style="color:#cfcfcf;">N/A</span>',
    }
    return status_map.get(byte_val, f"Reserved ({byte_val})")


def format_j3072_crc_status(byte_val, device_type):
    """
    Formats the display for EvJ3072CrcStatus and SeJ3072CrcStatus values.
    """
    remote_type = "SE" if device_type == "EV" else "EV"
    status_map = {
        0x00: f"Not sent by {device_type}; No check {remote_type} CRC",
        0x01: f"Not sent by {device_type}; Last {remote_type} CRC OK",
        0x0E: f"Not sent by {device_type}; Last {remote_type} CRC FAIL",
        0x0F: f"Not sent by {device_type}; No complete cycle from {remote_type}",
        0x10: f"Sent by {device_type}; No check {remote_type} CRC",
        0x11: f"Sent by {device_type}; Last {remote_type} CRC OK",
        0x1E: f"Sent by {device_type}; Last {remote_type} CRC FAIL",
        0x1F: f"Sent by {device_type}; No complete cycle from {remote_type}",
    }
    return status_map.get(byte_val, f"Reserved ({byte_val})")


def crc_check(page_crc_value, stored_pages_bytes):
    """
    Computes the CRC-32.CRC32 was used from library
    https://github.com/Nicoretti/crc
    This is currently configured directly from documentation
    Change at own discretion
    This is a confirmed working implementation of CRC32 for EvID and SeID in SAE J3068/1
    """
    from crc import Calculator, Crc32

    calculator = Calculator(Crc32.CRC32, optimized=True)

    computed_crc = calculator.checksum(bytes(stored_pages_bytes))

    is_match = (page_crc_value == computed_crc)

    return is_match, computed_crc
