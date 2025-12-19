from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QSlider,
    QHBoxLayout, QSizePolicy, QSpacerItem, QFrame, QGridLayout, QPushButton,
    QFileDialog, QTextEdit, QDialog, QRadioButton, QDialogButtonBox, QLineEdit, QComboBox,
    QToolButton, QScrollArea, QShortcut, QInputDialog, QMessageBox, QTabWidget
)
from PyQt5.QtGui import QFont, QIcon, QFontMetrics, QKeySequence, QTextCursor, QColor, QPalette, QMovie
from PyQt5.QtCore import Qt, QTimer, QSize, QSettings, QCoreApplication
import copy
import os
import sys
import serial
import serial.tools.list_ports
import ctypes
import sys
import globals
import time
import math

'''
Stable state of J3068/2

Next Fixes
-- fix so that debug log isn't laggy with lots of frames
'''

from data_processing import format_frame, format_selected_version, format_amp_value, format_voltage_value, \
    compute_lin_enhanced_checksum, guess_format, parse_hex_data, parse_data_stream, determine_protocol_version, \
    format_id_status, format_crc_status, format_Num_Prop_Pages, format_j3072_status, format_j3072_crc_status, \
    crc_check

from update_functions import (update_slider_label, update_task_display, update_contactor_state_display, \
    update_protocol_version_display, update_sesupported_protocol_versions_display, update_ratings_display, \
    update_seavailable_current_display, update_evpresent_current_display, update_evrequested_current_display, \
    update_EvInfo_display, update_SeInfo_display, update_CableNode_display, update_sleep_connection_display, \
    update_Op3EvID_display, update_Op3SeID_display, update_ev_data_tab, update_se_data_tab, update_control_page_display, \
    update_OP252_control_page_display,update_EvModeCtrl_display, update_SeModeCtrl_display, update_EvJ3072_display, \
    update_SeJ3072_display, update_SeTargets1_display)

#   Redefine global names from globals.py
protocol_version_names = globals.protocol_version_names
ser = globals.ser
live_data_log = globals.live_data_log
auto_update1 = globals.auto_update

# ---------------- Globals --------------------
raw_file_buffer = ""
is_spaced_format = False
frames_parsed = 0
total_frames = 0
live_data_active = False
live_timer_state = False
frame_validity_map = {}
current_init_data = {}
init_data_timeline = []
current_op_data = {}
op_data_timeline = []
current_ver_data = {}
ver_data_timeline = []
evID_buffer = {}
seID_buffer = {}
evJ3072_buffer = {}
seJ3072_buffer = {}



evID_stage_bytes = bytearray()
seID_stage_bytes = bytearray()



raw_byte_list = []
fsm_state = 0
fsm_buffer = []
last_valid_frame = None
LAST_N_FRAMES = 100
recent_frame_types = []
debug_dialog = None
frame_type_map = {
    0: "SeVersionList",
    1: "EvVersionList",
    2: "SeStatus",
    3: "EvStatus",
    4: "EvPresentCurrents",
    5: "SeNomVoltages",
    6: "SeMaxCurrents",
    7: "EvMaxVoltages",
    8: "EvMinVoltages",
    9: "EvMaxMinCurrents",
    0x0A: "Cable Node",
    0x0B: "SeInfoList",
    0x0C: "EvInfoList",
    0x0F: "EvID",
    0x10: "SeID",
    0x15: "EvModeCtrl",
    0x16: "SeModeCtrl",
    0x17: "EvJ3072",
    0x18: "SeJ3072",
    0x19: "SeTargets1"

    # Add new frame types here for recent data
}


#   CollapsibleBox: for collapsible “dropdown” panels
class CollapsibleBox(QWidget):
    """
    A simple collapsible panel (dropdown) that toggles open/closed,
    """

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # A toggle button for the arrow only; no text
        self.toggle_button = QToolButton(checkable=True, checked=False)
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        # Arrow on drop down menu size
        self.toggle_button.setIconSize(QSize(8, 8))

        # A label to hold the HTML-based text
        self.label_header = QLabel()
        # Some default text (plain black)
        self.label_header.setText("<span style='color:black;'></span>")

        # Put both in a small horizontal layout:
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addSpacing(3)
        header_layout.addWidget(self.toggle_button)
        header_layout.addWidget(self.label_header)

        self.header_widget = QWidget()
        self.header_widget.setLayout(header_layout)

        # The content area is hidden by default
        self.content_widget = QWidget()
        self.content_widget.setVisible(False)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.header_widget)
        main_layout.addWidget(self.content_widget)

        self.toggle_button.setStyleSheet("""
                   QToolButton {
                       background-color: #F7F9FC;
                       border: 1px solid #CBD2D9;
                       border-top-left-radius: 6px;
                       border-top-right-radius: 6px;
                       border-bottom-left-radius: 0px;
                       border-bottom-right-radius: 0px;
                       /* Remove any bold: */
                       font-size: 10px;
                       color: #333;
                   }
                   QToolButton::hover {
                       background-color: #ECEFF1;
                   }
                   QToolButton::checked {
                       background-color: #E2E6EA;
                   }
               """)

        self.toggle_button.clicked.connect(self.on_toggle)

    def on_toggle(self):
        # Toggle open/close
        if self.toggle_button.isChecked():
            self.toggle_button.setArrowType(Qt.DownArrow)
            self.content_widget.setVisible(True)
        else:
            self.toggle_button.setArrowType(Qt.RightArrow)
            self.content_widget.setVisible(False)

    def setContentLayout(self, layout):
        self.content_widget.setLayout(layout)


class SliderLabelBar(QWidget):
    """
    A custom widget that draws numeric labels under a QSlider,
    lining up precisely with the slider's tick marks.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._min_val = 0
        self._max_val = 0
        self._interval = 1
        self._font = QFont("Times New Roman", 8)

    def setRange(self, min_val, max_val):
        self._min_val = min_val
        self._max_val = max_val
        self.update()

    def setTickInterval(self, interval):
        self._interval = max(1, interval)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter_metrics = QFontMetrics(self._font)
        total_range = self._max_val - self._min_val
        if total_range <= 0:
            return

        width = self.width()
        height = self.height()

        val = self._min_val
        while val <= self._max_val:
            fraction = (val - self._min_val) / total_range
            x_center = int(fraction * width)

            text = str(val)
            text_width = painter_metrics.horizontalAdvance(text)
            # Draw so that 'val' is centered at x_center, near bottom:
            self._drawText(x_center - text_width // 2, height - 2, text)

            val += self._interval

        # If the last label isn't exactly on an interval, ensure we paint it
        if (self._max_val - self._min_val) % self._interval != 0:
            text = str(self._max_val)
            text_width = painter_metrics.horizontalAdvance(text)
            self._drawText(width - text_width // 2, height - 2, text)

    def _drawText(self, x, y, text):
        from PyQt5.QtGui import QPainter
        painter = QPainter(self)
        painter.setFont(self._font)
        # Check global dark mode flag to set appropriate text color
        painter.setPen(Qt.black)
        painter.drawText(x, y, text)


#   Fixes auto scaling text issue
QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
app = QApplication(sys.argv)

screen = app.primaryScreen()
dpi_scale = screen.logicalDotsPerInch() / 96.0

window = QMainWindow()

# -- Window Setup --
#   set minimum size
# window.setMinimumSize(1200, 600)
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

#   sets open size of program
window.resize(int(1600 * dpi_scale), int(900 * dpi_scale))

window.setWindowTitle("LIN_GUI")
window.setWindowIcon(QIcon(resource_path(r"images/UD_logo.png")))

if os.name == "nt":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(resource_path(r"images/UD_logo.png"))

# Initialization of slider label (top bar)
label = QLabel("Frame Number: 50")  # Start with slider's initial value
label.setAlignment(Qt.AlignCenter)
font = QFont("Times New Roman", 17, QFont.Bold)
label.setFont(font)

# Create the slider
slider = QSlider(Qt.Horizontal)
slider.setMinimum(0)
slider.setMaximum(100)
slider.setValue(50)
slider.setTickPosition(QSlider.TicksBelow)
slider.setTickInterval(10)
slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
slider.setFixedHeight(int(50 * dpi_scale))

# Create custom slider label bar (numbers beneath slider)
slider_label_bar = SliderLabelBar()
slider_label_bar.setFixedHeight(20)

slider_label_bar.setRange(slider.minimum(), slider.maximum())
slider_label_bar.setTickInterval(slider.tickInterval())

frame_input = QLineEdit()
frame_input.setFixedWidth(60)
frame_input.setPlaceholderText("Go to…")
frame_input.setAlignment(Qt.AlignCenter)
frame_input.setStyleSheet("""
    QLineEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;                 
        font-size: 8pt; 
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")


#   lets user move slider if slider presssed if not update to newest frame
def user_started_slider_interaction():
    global auto_update1
    auto_update1 = False


slider.sliderPressed.connect(user_started_slider_interaction)
slider.sliderMoved.connect(user_started_slider_interaction)


def jump_to_frame():
    text = frame_input.text().strip()
    global auto_update1
    auto_update1 = False
    if text.isdigit():
        val = int(text)
        val = max(slider.minimum(), min(slider.maximum(), val))
        slider.setValue(val)


frame_input.returnPressed.connect(jump_to_frame)

Right_one = QPushButton()
Right_one.setIcon(QIcon(resource_path(r"images/fast-arrow-right.png")))

Right_one.setFixedSize(20, 20)

Right_one.setToolTip("Next Frame")
Right_one.setStyleSheet("""
    QPushButton {
        background-color: transparent;
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

Left_one = QPushButton()
Left_one.setIcon(QIcon(resource_path(r"images/fast-arrow-left.png")))

Left_one.setFixedSize(20, 20)

Left_one.setToolTip("Previous Frame")
Left_one.setStyleSheet("""
    QPushButton {
        background-color: transparent;
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

End_skip = QPushButton()
End_skip.setIcon(QIcon(resource_path(r"images/End-Skip.png")))

End_skip.setFixedSize(20, 20)

End_skip.setToolTip("Skip to End")
End_skip.setStyleSheet("""
    QPushButton {
        background-color: transparent;
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

Start_skip = QPushButton()
Start_skip.setIcon(QIcon(resource_path(r"images/Start-Skip.png")))

Start_skip.setFixedSize(20, 20)

Start_skip.setToolTip("Skip to Start")
Start_skip.setStyleSheet("""
    QPushButton {
        background-color: transparent;
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")


def increment_frame():
    global auto_update1
    auto_update1 = False
    current_value = slider.value()
    if current_value < slider.maximum():
        slider.setValue(current_value + 1)


def decrement_frame():
    global auto_update1
    auto_update1 = False
    current_value = slider.value()
    if current_value - 1 >= slider.minimum():
        slider.setValue(current_value - 1)


def Start_frame():
    global auto_update1
    auto_update1 = False
    slider.setValue(slider.minimum())


def Last_frame():
    global auto_update1
    slider.setValue(slider.maximum())
    auto_update1 = True


Right_one.clicked.connect(increment_frame)
Left_one.clicked.connect(decrement_frame)
Start_skip.clicked.connect(Start_frame)
End_skip.clicked.connect(Last_frame)

top_bar = QHBoxLayout()
top_bar.addStretch()
spacer_label = QSpacerItem(205, 60, QSizePolicy.Minimum, QSizePolicy.Fixed)
top_bar.addItem(spacer_label)
top_bar.addWidget(label)
top_bar.addStretch()
top_bar.addWidget(Start_skip)
top_bar.addWidget(Left_one)
top_bar.addWidget(frame_input)
top_bar.addWidget(Right_one)
top_bar.addWidget(End_skip)

slider_container_layout = QVBoxLayout()
slider_container_layout.addWidget(slider)
slider_container_layout.addWidget(slider_label_bar)

result_display = QTextEdit()
result_display.setReadOnly(True)
result_display.setFont(QFont("Times New Roman", 9))
result_display.setAlignment(Qt.AlignCenter)
result_display.setMinimumHeight(410)

# ---------------------- Start of OP Drop Down ---------------------------------------
task_operation_display = QTextEdit()
task_operation_display.setReadOnly(True)
task_operation_display.setFont(QFont("Times New Roman", 9))
task_operation_display.setAlignment(Qt.AlignCenter)
# task_operation_display.setMinimumSize(950, 50)  # width, height
task_operation_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
task_operation_display.setMaximumHeight(69)

# task_operation_display.setFixedHeight(57)

task_operation_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

contactor_state_display = QTextEdit()
contactor_state_display.setReadOnly(True)
contactor_state_display.setFont(QFont("Times New Roman", 9))
contactor_state_display.setAlignment(Qt.AlignCenter)
contactor_state_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
contactor_state_display.setMaximumHeight(32)

contactor_state_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

selected_protocol_version_display = QTextEdit()
selected_protocol_version_display.setReadOnly(True)
selected_protocol_version_display.setFont(QFont("Times New Roman", 9))
selected_protocol_version_display.setAlignment(Qt.AlignCenter)
selected_protocol_version_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
selected_protocol_version_display.setMaximumHeight(110)

selected_protocol_version_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

sesupported_protocol_versions_display = QTextEdit()
sesupported_protocol_versions_display.setReadOnly(True)
sesupported_protocol_versions_display.setFont(QFont("Times New Roman", 9))
sesupported_protocol_versions_display.setAlignment(Qt.AlignCenter)
sesupported_protocol_versions_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
sesupported_protocol_versions_display.setMaximumHeight(130)

sesupported_protocol_versions_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

ratings_display = QTextEdit()
ratings_display.setReadOnly(True)
ratings_display.setFont(QFont("Times New Roman", 9))
ratings_display.setAlignment(Qt.AlignCenter)
ratings_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

ratings_display.setFixedHeight(250)

ratings_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

seavailable_current_display = QTextEdit()
seavailable_current_display.setReadOnly(True)
seavailable_current_display.setFont(QFont("Times New Roman", 9))
seavailable_current_display.setAlignment(Qt.AlignCenter)
seavailable_current_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
seavailable_current_display.setMaximumHeight(94)

seavailable_current_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

evpresent_current_display = QTextEdit()
evpresent_current_display.setReadOnly(True)
evpresent_current_display.setFont(QFont("Times New Roman", 9))
evpresent_current_display.setAlignment(Qt.AlignCenter)
evpresent_current_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
evpresent_current_display.setMaximumHeight(90)

evpresent_current_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

evrequested_current_display = QTextEdit()
evrequested_current_display.setReadOnly(True)
evrequested_current_display.setFont(QFont("Times New Roman", 9))
evrequested_current_display.setAlignment(Qt.AlignCenter)
evrequested_current_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
evrequested_current_display.setMaximumHeight(90)

evrequested_current_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

EvInfo_display = QTextEdit()
EvInfo_display.setReadOnly(True)
EvInfo_display.setFont(QFont("Times New Roman", 9))
EvInfo_display.setAlignment(Qt.AlignCenter)
EvInfo_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
EvInfo_display.setMaximumHeight(150)

EvInfo_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

SeInfo_display = QTextEdit()
SeInfo_display.setReadOnly(True)
SeInfo_display.setFont(QFont("Times New Roman", 9))
SeInfo_display.setAlignment(Qt.AlignCenter)
SeInfo_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
SeInfo_display.setMaximumHeight(150)

SeInfo_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

cable_Node_display = QTextEdit()  # Not Implemented
cable_Node_display.setReadOnly(True)
cable_Node_display.setFont(QFont("Times New Roman", 9))
cable_Node_display.setAlignment(Qt.AlignCenter)
cable_Node_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

cable_Node_display.setFixedHeight(270)

globals.cable_Node_display = cable_Node_display

cable_Node_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

sleep_connection_display = QTextEdit()
sleep_connection_display.setReadOnly(True)
sleep_connection_display.setFont(QFont("Times New Roman", 9))
sleep_connection_display.setAlignment(Qt.AlignCenter)
sleep_connection_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
sleep_connection_display.setMaximumHeight(50)

sleep_connection_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

# OP3 Control Page dropdown part of J3068/1
control_page_display = QTextEdit()
control_page_display.setReadOnly(True)
control_page_display.setFont(QFont("Times New Roman", 9))
control_page_display.setAlignment(Qt.AlignCenter)
control_page_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
control_page_display.setMaximumHeight(130)  # Adjust height as needed
control_page_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
""")
globals.control_page_display = control_page_display

# OP252 Control Page dropdown part of J3068/2
OP252_control_page_display = QTextEdit()
OP252_control_page_display.setReadOnly(True)
OP252_control_page_display.setFont(QFont("Times New Roman", 9))
OP252_control_page_display.setAlignment(Qt.AlignCenter)
OP252_control_page_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
OP252_control_page_display.setMaximumHeight(130)  # Adjust height as needed
OP252_control_page_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
""")
globals.OP252_control_page_display = OP252_control_page_display

# EvModeCtrl dropdown part of J3068/2
EvModeCtrl_display = QTextEdit()
EvModeCtrl_display.setReadOnly(True)
EvModeCtrl_display.setFont(QFont("Times New Roman", 9))
EvModeCtrl_display.setAlignment(Qt.AlignCenter)
EvModeCtrl_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
EvModeCtrl_display.setMaximumHeight(130)  # Adjust height as needed
EvModeCtrl_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
""")
globals.EvModeCtrl_display = EvModeCtrl_display

# SeModeCtrl dropdown part of J3068/2
SeModeCtrl_display = QTextEdit()
SeModeCtrl_display.setReadOnly(True)
SeModeCtrl_display.setFont(QFont("Times New Roman", 9))
SeModeCtrl_display.setAlignment(Qt.AlignCenter)
SeModeCtrl_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
SeModeCtrl_display.setMaximumHeight(130)  # Adjust height as needed
SeModeCtrl_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
""")
globals.SeModeCtrl_display = SeModeCtrl_display

# SeTargets1 dropdown part of J3068/2
SeTargets1_display = QTextEdit()
SeTargets1_display.setReadOnly(True)
SeTargets1_display.setFont(QFont("Times New Roman", 9))
SeTargets1_display.setAlignment(Qt.AlignCenter)
SeTargets1_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
SeTargets1_display.setMaximumHeight(130)  # Adjust height as needed
SeTargets1_display.setStyleSheet("""
    QTextEdit {
        background-color: rgba(0, 0, 0, 0); 
        border: none;
    }
""")
globals.SeTargets1_display = SeTargets1_display

# --------------------------End Of OP dropdowns----------------------------------------

# --------------------------Start of displays for right-side tabs----------------------

transparent_text_edit_style = """
    QTextEdit {
        background-color: transparent;
        border: none;
    }
    QScrollBar:vertical {
        border: none;
        background: transparent;
        width: 8px;
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:vertical {
        background: #D0D0D0;
        min-height: 20px;
        border-radius: 4px;
    }
    QScrollBar::handle:vertical:hover {
        background: #B0B0B0;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
"""

op3_evid_display = QTextEdit()
op3_evid_display.setReadOnly(True)
op3_evid_display.setFont(QFont("Times New Roman", 9))
op3_evid_display.setStyleSheet(transparent_text_edit_style)

op3_seid_display = QTextEdit()
op3_seid_display.setReadOnly(True)
op3_seid_display.setFont(QFont("Times New Roman", 9))
op3_seid_display.setStyleSheet(transparent_text_edit_style)

ev_data_tab_display = QTextEdit()
ev_data_tab_display.setReadOnly(True)
ev_data_tab_display.setFont(QFont("Times New Roman", 9))
ev_data_tab_display.setStyleSheet(transparent_text_edit_style)

se_data_tab_display = QTextEdit()
se_data_tab_display.setReadOnly(True)
se_data_tab_display.setFont(QFont("Times New Roman", 9))
se_data_tab_display.setStyleSheet(transparent_text_edit_style)

EvJ3072_tab_display = QTextEdit()
EvJ3072_tab_display.setReadOnly(True)
EvJ3072_tab_display.setFont(QFont("Times New Roman", 9))
EvJ3072_tab_display.setStyleSheet(transparent_text_edit_style)

SeJ3072_tab_display = QTextEdit()
SeJ3072_tab_display.setReadOnly(True)
SeJ3072_tab_display.setFont(QFont("Times New Roman", 9))
SeJ3072_tab_display.setStyleSheet(transparent_text_edit_style)

# --------------------------End of displays for right-side tabs------------------------

def toggle_na_view():
    """Toggles the visibility of N/A data fields and refreshes the UI."""
    globals.na_toggle_active = not globals.na_toggle_active

    if globals.na_toggle_active:
        NA_toggle.setToolTip("Show N/A, Error, and Reserved values")
    else:
        NA_toggle.setToolTip("Hide N/A, Error, and Reserved values")

    refresh_all_displays(slider.value())

class FormatSelectionDialog(QDialog):
    def __init__(self, parent, guessed_spaced, guessed_binary):
        super().__init__(parent)
        self.setWindowTitle("Select Frame Format")
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Radio buttons
        self.radio_no_spaces = QRadioButton("No Spaces (24)")
        self.radio_spaces = QRadioButton("Spaces (36)")
        self.radio_binary = QRadioButton("Binary")

        # Set initial check states
        if guessed_binary:
            self.radio_binary.setChecked(True)
        elif guessed_spaced:
            self.radio_spaces.setChecked(True)
        else:
            self.radio_no_spaces.setChecked(True)

        layout.addWidget(QLabel("Please select the frame format:"))
        layout.addWidget(self.radio_no_spaces)
        layout.addWidget(self.radio_spaces)
        layout.addWidget(self.radio_binary)

        # Always visible buffer-frames input
        self.buffer_label = QLabel("Enter amount of buffer frames:")
        self.buffer_edit = QLineEdit()
        self.buffer_edit.setPlaceholderText("ex. 100")
        layout.addWidget(self.buffer_label)
        layout.addWidget(self.buffer_edit)

        # OK/Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.on_ok_pressed)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setStyleSheet("""
            font-size: 8pt;
            QRadioButton, QLabel {
                font-family: 'Times New Roman';
            }
            QPushButton {
                font-size: 8pt;
            }
        """)
        self.setLayout(layout)

    def on_ok_pressed(self):
        global LAST_N_FRAMES
        text = self.buffer_edit.text().strip()
        LAST_N_FRAMES = int(text) if text.isdigit() else 100
        self.accept()

    def selected_format(self):
        return (self.radio_spaces.isChecked(),
                self.radio_binary.isChecked())

    def on_binary_toggled(self, checked):
        """
        Show/hide the buffer label & text box depending on whether
        “Binary” is currently selected.
        """
        self.buffer_label.setVisible(checked)
        self.buffer_edit.setVisible(checked)


class SerialPortSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Serial Port")
        self.setModal(True)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select a serial port:"))

        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)   #allows yu to type into serial port box if not wanted, make False
        layout.addWidget(self.port_combo)

        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        self.port_combo.addItems(port_list)

        # Use QSettings to get the last selected serial port
        settings = QSettings("MyCompany", "MyApp")
        last_port = settings.value("lastSerialPort", "")
        if last_port in port_list:
            self.port_combo.setCurrentText(last_port)
        elif port_list:
            self.port_combo.setCurrentIndex(0)

        # Add buffer frames input below port selection
        self.buffer_label = QLabel(
            "----------------------------------------------------------\nEnter amount of buffer frames:")
        self.buffer_edit = QLineEdit()
        self.buffer_edit.setPlaceholderText("ex. 100")
        layout.addWidget(self.buffer_label)
        layout.addWidget(self.buffer_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setStyleSheet("""
            font-size: 8pt;
            QTextEdit {
                font-size: 9pt;
                font-family: 'Times New Roman';
            }
            QPushButton {
                font-size: 8pt;
            }
        """)

        self.setLayout(layout)

    def selected_port(self):
        return self.port_combo.currentText()

    def selected_buffer_frames(self):
        text = self.buffer_edit.text().strip()
        if text.isdigit():
            return int(text)
        else:
            return 100


class LoadingDialog(QDialog):
    """dialog to show a loading GIF"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)

        self.gif_label = QLabel(self)
        self.gif_label.setAlignment(Qt.AlignCenter)

        gif_path = resource_path("images/twiggy-loading.gif")
        self.movie = QMovie(gif_path)

        if not self.movie.isValid():
            # if GIF file is not found
            self.gif_label.setText("Loading...")
            self.gif_label.setStyleSheet("QLabel { background-color: #2E2E2E; color: white; font: 18pt; padding: 20px; border-radius: 15px; }")
            self.setFixedSize(200, 100)
            self.gif_label.setGeometry(0, 0, 200, 100)
        else:
            #GIF SIZE
            gif_width = 250
            gif_height = 300

            self.setFixedSize(gif_width, gif_height)
            self.gif_label.setGeometry(0, 0, gif_width, gif_height)
            self.movie.setScaledSize(QSize(gif_width, gif_height))
            self.gif_label.setMovie(self.movie)
            self.movie.start()

        #PLACEMENT
        # I tried to make this dynamically move with screen, but couldn't get to work
        pos_x = 650
        pos_y = 300
        self.move(pos_x, pos_y)



def color_if_na(label, value):
    if value == "N/A":
        return f"{label}: <span style='color:#cfcfcf;'>{value}</span>"
    else:
        return f"{label}: {value}"


def fsm_process_bytes(new_data_bytes):
    global fsm_state, fsm_buffer
    frames_found = []
    for b in new_data_bytes:
        hex_b = f"{b:02X}"
        if fsm_state == 0:
            fsm_buffer.append(hex_b)
            if len(fsm_buffer) >= 2:
                if fsm_buffer[-2:] in (["00", "55"], ["80", "55"]):
                    fsm_state = 1
                    fsm_buffer = fsm_buffer[-2:]
                else:
                    fsm_buffer = fsm_buffer[-1:]
        elif fsm_state == 1:
            fsm_buffer.append(hex_b)
            if len(fsm_buffer) >= 2 and fsm_buffer[-2:] in (["00", "55"], ["80", "55"]):
                frame = fsm_buffer[:-2]
                if frame:
                    frame = fsm_buffer[-2:] + frame
                    frames_found.append(frame)
                fsm_buffer = fsm_buffer[-2:]
    return frames_found


# -------------- update data ---------------------
def update_init_data(key, value):
    global frames_parsed
    current_init_data[key] = (value, frames_parsed)

def update_ver_data(key, value):
    global frames_parsed
    current_ver_data[key] = (value, frames_parsed)

def update_op_data(key, value):
    global frames_parsed
    current_op_data[key] = (value, frames_parsed)


def _assemble_and_update_field(page_buffer, field_name, expected_total_length):
    """Helper to assemble, decode, and update a completed field."""
    # Sort chunks by position to ensure correct order
    sorted_chunks = sorted(page_buffer[field_name].items())

    full_data_bytes = []
    for _, chunk_data in sorted_chunks:
        full_data_bytes.extend(chunk_data)

    # Trim to the exact length
    trimmed_bytes = full_data_bytes[:expected_total_length]

    try:
        byte_values = trimmed_bytes
        ascii_string = bytes(byte_values).split(b'\x00')[0].decode('ascii', errors='replace').strip()
        if not ascii_string:
            ascii_string = "N/A"
    except (TypeError, UnicodeDecodeError, IndexError, ValueError):
        # Added TypeError
        ascii_string = "Decode Error"

    # Update the global data and clean up the buffer
    update_op_data(field_name, ascii_string)
    del page_buffer[field_name]


def process_stage(page_buffer, field_name, string_position, data_bytes, field_total_length):
    """
    Buffers data for multi-page fields and processes them when the
    expected total length is reached.
    """
    # Buffer the received data chunk
    if field_name not in page_buffer:
        page_buffer[field_name] = {}
    page_buffer[field_name][string_position] = data_bytes

    # Check if the field is complete using the provided total length
    buffered_length = sum(len(chunk) for chunk in page_buffer[field_name].values())
    if buffered_length >= field_total_length:
        _assemble_and_update_field(page_buffer, field_name, field_total_length)


# --------------Display Frames -------------------
def display_frames(chunks):
    global frames_parsed, total_frames, last_valid_frame, recent_frame_types
    statuses = ["StatusVer", "StatusInit", "StatusOp"]
    statusvals = ["Incomplete", "Complete", "Error", "N/A", "Deny_V", "Permit_V", "Error"]
    lines = ["L1", "L2", "L3", "N"]
    frequencies = ["None Supported", "50 Hz", "60 Hz", "50 Hz or 60 Hz"]

    def get_status_values(prefix, d1, store_to_ver_data=False):
        temp = d1 >> 1
        for i in range(1, 4):
            if i < 3:
                val_index = temp & 3
            else:
                val_index = (temp & 3) + 4
            this_status = statusvals[val_index]
            result_display.append(f"    {prefix}{statuses[i - 1]}: {this_status}")
            if store_to_ver_data:
                update_ver_data(f"{prefix}{statuses[i - 1]}", this_status)
            temp >>= 2

    def read_voltage_high_low(d_low, d_high):
        return ((d_high << 8) | d_low) / 10.0

    # Helper functions for parsing multiplexed frames
    def le_bytes_to_int(byte_slice):
        val = 0
        for i, byte in enumerate(byte_slice):
            val |= byte << (i * 8)
        return val

    def bytes_to_ascii(byte_slice):
        try:
            return bytes(byte_slice).split(b'\x00')[0].decode('ascii')
        except (UnicodeDecodeError, IndexError):
            return "N/A"

    for chunk_type, chunk_data in chunks:

        if live_data_active == False:
            # lets loading screen load and background processes happen
            QApplication.processEvents()

        if chunk_type == 'garbage':
            if chunk_data:
                garbage_str = " ".join(chunk_data)
                result_display.append(f"<b><span style='color:#E67E22;'>Trash Bytes:</span></b> {garbage_str}")
                result_display.append("")
            continue

        # If we reach here, the chunk is a frame.
        frame_data = chunk_data
        frames_parsed += 1

        ftype = "Unknown"
        try:
            protframes = frame_data[2] if len(frame_data) > 2 else None
            if protframes is None:
                raise ValueError("Invalid frame structure")

            protected_id_original = int(protframes, 16)
            frame_id = protected_id_original & 0x3F

            if frame_id in frame_type_map:
                ftype = frame_type_map[frame_id]
            else:
                ftype = f"Unknown Frame {frame_id:02X}"

            if live_data_active:
                now = time.time()
                globals.frame_timestamps.setdefault(ftype, []).append((frames_parsed, now))
            globals.all_frame_types.append(ftype)

            frame_title = f"Frame {frames_parsed}:"
            if globals.frame_time_active:
                time_str = format_frame(frames_parsed)
                result_display.append(frame_title)
                result_display.append(f"  Time: {time_str}")
            else:
                result_display.append(frame_title)

            checksum_str = frame_data[-1]
            data_bytes = frame_data[3:-1]

            recent_frame_types.append(ftype)
            if len(recent_frame_types) > LAST_N_FRAMES:
                recent_frame_types.pop(0)

            databytes = [int(byte, 16) for byte in data_bytes]
            computed_checksum, computed_protected_id = compute_lin_enhanced_checksum(frame_id, databytes)
            file_checksum = int(checksum_str, 16)

            protected_id_valid = (computed_protected_id == protected_id_original)
            checksum_valid = (file_checksum == computed_checksum)

            if protected_id_valid and checksum_valid:
                result_display.append("  Frame is valid")
                frame_validity_map[frames_parsed] = True
                last_valid_frame = frames_parsed
            else:
                frame_validity_map[frames_parsed] = False
                result_display.append(f"  Frame is invalid")
                result_display.append(f"  Checksum from file: {file_checksum:02X}")
                result_display.append(f"  Computed Checksum: {computed_checksum:02X}")
                result_display.append(f"  Computed Protected ID: {computed_protected_id:02X}")
                result_display.append(f"  Original Protected ID: {protected_id_original:02X}")
                result_display.append(f"  Frame Type: {frame_id:02X}")
                data_bytes_str = " ".join(data_bytes)
                result_display.append(f"  Data Bytes: {data_bytes_str} ")
                result_display.append(f"  Frame Bytes: {" ".join(frame_data)} \n")

                continue

            if not (protected_id_valid and checksum_valid):
                result_display.append("  Skipping interpretation due to invalid frame.\n")
                continue

            result_display.append(f"  Checksum from file: {file_checksum:02X}")
            result_display.append(f"  Computed Checksum: {computed_checksum:02X}")
            result_display.append(f"  Computed Protected ID: {computed_protected_id:02X}")
            result_display.append(f"  Original Protected ID: {protected_id_original:02X}")
            result_display.append(f"  Frame Type: {frame_id:02X}")  # display in debug as hex
            data_bytes_str = " ".join(data_bytes)
            result_display.append(f"  Data Bytes: {data_bytes_str}")
            result_display.append(f"  Frame Bytes: {" ".join(frame_data)} ")

            # Interpret frames
            if frame_id == 0:  # SeVersionList
                result_display.append("  Interpretation: SeVersionList")

                if len(databytes) >= 8:
                    se_sel_ver_str = format_selected_version(databytes[0])
                    update_ver_data("SeSelectedVersion_SeVersionList", se_sel_ver_str)
                    d1 = databytes[1]
                    page_number = databytes[2]
                    result_display.append(f"    SeSelectedVersion: {se_sel_ver_str}")
                    get_status_values("Se", d1, store_to_ver_data=True)  # if you want them in ver_data
                    result_display.append(f"    SeVersionPageNumber: {page_number}")

                    for i in range(1, 6):
                        val = databytes[i + 2]
                        result_display.append(f"    SeSupportedVersion{i}: {val}")

                    update_ver_data("SeSelectedVersion", se_sel_ver_str)
                    update_ver_data("SeSelectedVersion", str(databytes[0]))
                    update_ver_data("SeVersionPageNumber", str(page_number))

                    for i in range(1, 6):
                        val = databytes[i + 2]
                        update_ver_data(f"SeSupportedVersion{i}", str(val))

                else:
                    result_display.append("    Not enough data bytes to interpret")

            elif frame_id == 1:  # EvVersionList
                result_display.append("  Interpretation: EvVersionList")

                if len(databytes) >= 8:
                    ev_sel_ver_str = format_selected_version(databytes[0])
                    update_ver_data("EvSelectedVersion_EvVersionList", ev_sel_ver_str)
                    d1 = databytes[1]  # Contains bits for EV statuses
                    page_number = databytes[2]
                    ev_response_error = "No Error" if (d1 & 1) == 0 else "Error"
                    ev_awake = "Awake" if ((d1 >> 7) & 1) == 1 else "Sleep_Req"

                    result_display.append(f"    EvSelectedVersion: {ev_sel_ver_str}")
                    result_display.append(f"    EvResponseError: {ev_response_error}")
                    get_status_values("Ev", d1, store_to_ver_data=True)
                    result_display.append(f"    EvAwake: {ev_awake}")
                    result_display.append(f"    EvVersionPageNumber: {page_number}")

                    for i in range(1, 6):
                        val = databytes[i + 2]
                        result_display.append(f"    EvSupportedVersion{i}: {val}")

                    update_ver_data("EvSelectedVersion", ev_sel_ver_str)
                    update_ver_data("EvSelectedVersion", str(databytes[0]))
                    update_ver_data("EvVersionPageNumber", str(page_number))

                    for i in range(1, 6):
                        val = databytes[i + 2]
                        update_ver_data(f"EvSupportedVersion{i}", str(val))

                    update_op_data("EvResponseError", ev_response_error)
                    update_op_data("EvAwake", ev_awake)

                else:
                    result_display.append("    Not enough data bytes to interpret")


            elif frame_id == 2:  # SeStatus
                result_display.append("  Interpretation: SeStatus")
                if len(databytes) >= 6:
                    # Format only SeSelectedVersion
                    se_sel_ver_str = format_selected_version(databytes[0])
                    update_ver_data("SeSelectedVersion_SeVersionList", se_sel_ver_str)
                    result_display.append(f"    SeSelectedVersion: {se_sel_ver_str}")

                    get_status_values("Se", databytes[1], store_to_ver_data=True)
                    # Retrieve updated ver_data to pass into determine_protocol_version
                    se_status_ver = current_ver_data.get("SeStatusVer", ("Unknown", 0))[0]
                    se_status_init = current_ver_data.get("SeStatusInit", ("Unknown", 0))[0]
                    se_status_op = current_ver_data.get("SeStatusOp", ("Unknown", 0))[0]

                    protocol_str = determine_protocol_version(
                        se_status_ver,
                        se_status_init,
                        se_status_op,
                        databytes[0]  # raw integer
                    )
                    result_display.append(f"    ProtocolVersion: {protocol_str}")
                    update_ver_data("ProtocolVersion", protocol_str)

                    # Format the amperage values
                    for i, line_name in enumerate(lines):
                        amps_str = format_amp_value(databytes[i + 2])
                        result_display.append(f"    SeAvailableCurrent{line_name}: {amps_str}")

                    # Update stored data
                    update_init_data("SeSelectedVersion", se_sel_ver_str)
                    for i, line_name in enumerate(lines):
                        amps_str = format_amp_value(databytes[i + 2])
                        update_init_data(f"SeAvailableCurrent_{line_name}", amps_str)

                    update_op_data("SeOpSelectedVersion", se_sel_ver_str)
                    for i, line_name in enumerate(lines):
                        amps_str = format_amp_value(databytes[i + 2])
                        update_op_data(f"SeOpAvailableCurrent_{line_name}", amps_str)
                else:
                    result_display.append("    Not enough data bytes to interpret")

            elif frame_id == 3:  # EvStatus
                result_display.append("  Interpretation: EvStatus")
                if len(databytes) >= 6:
                    ev_sel_ver_str = format_selected_version(databytes[0])
                    update_ver_data("EvSelectedVersion_EvVersionList", ev_sel_ver_str)
                    result_display.append(f"    EvSelectedVersion: {ev_sel_ver_str}")

                    ev_response_error = "No Error" if (databytes[1] & 1) == 0 else "Error"
                    result_display.append(f"    EvResponseError: {ev_response_error}")
                    get_status_values("Ev", databytes[1], store_to_ver_data=True)
                    ev_awake = "Awake" if ((databytes[1] >> 7) & 1) == 1 else "Sleep_Req"
                    result_display.append(f"    EvAwake: {ev_awake}")
                    update_ver_data("EvAwake", ev_awake)

                    # EV Present Current Dropdown Data
                    update_op_data("EvResponseError", ev_response_error)
                    update_op_data("EvAwake", ev_awake)

                    for i, line_name in enumerate(lines):
                        amps_str = format_amp_value(databytes[i + 2])
                        result_display.append(f"\t   &nbsp; &nbsp; EvRequestedCurrent{line_name}: {amps_str}")

                    update_init_data("EvSelectedVersion", ev_sel_ver_str)
                    for i, line_name in enumerate(lines):
                        amps_str = format_amp_value(databytes[i + 2])
                        update_init_data(f"EvRequestedCurrent_{line_name}", amps_str)

                    update_op_data("EvOpSelectedVersion", ev_sel_ver_str)
                    for i, line_name in enumerate(lines):
                        amps_str = format_amp_value(databytes[i + 2])
                        update_op_data(f"EvOpRequestedCurrent_{line_name}", amps_str)
                else:
                    result_display.append("    Not enough data bytes to interpret")

            elif frame_id == 4:  # EvPresentCurrents
                result_display.append("  Interpretation: EvPresentCurrents")
                if len(databytes) >= 5:
                    ev_sel_ver_str = format_selected_version(databytes[0])
                    result_display.append(f"    EvSelectedVersion: {ev_sel_ver_str}")
                    for i, line_name in enumerate(lines):
                        amps_str = format_amp_value(databytes[i + 1])
                        result_display.append(f"   &nbsp; &nbsp; EvPresentCurrent{line_name}: {amps_str}")

                    update_op_data("EvOpSelectedVersion", ev_sel_ver_str)
                    for i, line_name in enumerate(lines):
                        amps_str = format_amp_value(databytes[i + 1])
                        update_op_data(f"EvOpPresentCurrent_{line_name}", amps_str)
                else:
                    result_display.append("    Not enough data bytes to interpret")

            elif frame_id == 5:  # SeNomVoltages
                result_display.append("  Interpretation: SeNomVoltages")
                if len(databytes) >= 6:
                    se_sel_ver_str = format_selected_version(databytes[0])
                    update_ver_data("SeSelectedVersion_SeVersionList", se_sel_ver_str)
                    result_display.append(f"    SeSelectedVersion: {se_sel_ver_str}")

                    seNomVoltageL1N = read_voltage_high_low(databytes[1], databytes[2])
                    seNomVoltageLL = read_voltage_high_low(databytes[3], databytes[4])
                    freq_index = databytes[5]
                    freq_str = frequencies[freq_index] if freq_index < len(frequencies) else "Unknown"

                    # Format voltage
                    volt_l1n_str = format_voltage_value(seNomVoltageL1N)
                    volt_ll_str = format_voltage_value(seNomVoltageLL)

                    result_display.append(f"    SeNomVoltageL1N: {volt_l1n_str}")
                    result_display.append(f"    SeNomVoltageLL: {volt_ll_str}")
                    result_display.append(f"    SeFrequency: {freq_str} (raw = {freq_index})")

                    update_init_data("SeSelectedVersion", se_sel_ver_str)
                    update_init_data("SeNomVoltageL1N", volt_l1n_str)
                    update_init_data("SeNomVoltageLL", volt_ll_str)
                    update_init_data("SeFrequency", freq_str)
                else:
                    result_display.append("    Not enough data bytes to interpret")


            elif frame_id == 6:  # SeMaxCurrents
                result_display.append("  Interpretation: SeMaxCurrents")
                if len(databytes) >= 6:
                    se_sel_ver_str = format_selected_version(databytes[0])
                    update_ver_data("SeSelectedVersion_SeVersionList", se_sel_ver_str)
                    result_display.append(f"    SeMaXCurrents (SelectedVersion): {se_sel_ver_str}")
                    lines = ["L1", "L2", "L3", "N"]

                    for i, line_name in enumerate(lines):
                        amps_str = format_amp_value(databytes[i + 1])
                        result_display.append(f"    SeMaXCurrent{line_name}: {amps_str}")
                        update_init_data(f"SeMaxCurrent_{line_name}", amps_str)

                    se_connection_type_map = {
                        0x00: "SAE J3068 AC (IEC 62196-2 Type 2) or GB/T 20234.2 socket-outlet",
                        0x01: "SAE J1772 (IEC 62196-2 Type 1) connector",
                        0x02: "SAE J3068 AC (IEC 62196-2 Type 2) connector",
                        0x03: "CCS1 connector",
                        0x04: "CCS2 (SAE J3068 DC) connector",
                        0x05: "SAF J3400 connector",
                        0x06: "GB/T 20234.2 connector",
                        0xFE: "Error",
                        0xFF: "N/A"
                    }

                    se_conn_type_val = databytes[5]
                    se_conn_type_str = se_connection_type_map.get(
                        se_conn_type_val,
                        f"Reserved (0x{se_conn_type_val:02X})"
                    )

                    result_display.append(f"    SeConnectionType: {se_conn_type_str}")
                    update_op_data("SeConnectionType", se_conn_type_str)

                else:
                    result_display.append("    Not enough data bytes to interpret")


            elif frame_id == 7:  # EvMaxVoltages
                result_display.append("  Interpretation: EvMaxVoltages")
                if len(databytes) >= 6:
                    ev_sel_ver_str = format_selected_version(databytes[0])
                    update_ver_data("EvSelectedVersion_EvVersionList", ev_sel_ver_str)
                    result_display.append(f"    EvSelectedVersion: {ev_sel_ver_str}")

                    EvMaxVoltageL1N = read_voltage_high_low(databytes[1], databytes[2])
                    EvMaxVoltageLL = read_voltage_high_low(databytes[3], databytes[4])
                    freq_index = databytes[5]
                    freq_str = frequencies[freq_index] if freq_index < len(frequencies) else "Unknown"

                    volt_l1n_str = format_voltage_value(EvMaxVoltageL1N)
                    volt_ll_str = format_voltage_value(EvMaxVoltageLL)

                    result_display.append(f"    EvMaxVoltageL1N: {volt_l1n_str}")
                    result_display.append(f"    EvMaxVoltageLL: {volt_ll_str}")
                    result_display.append(f"    EvFrequencies: {freq_str} (raw = {freq_index})")

                    update_init_data("EvSelectedVersion", ev_sel_ver_str)
                    update_init_data("EvMaxVoltageL1N", volt_l1n_str)
                    update_init_data("EvMaxVoltageLL", volt_ll_str)
                    update_init_data("EvFrequencies", freq_str)
                else:
                    result_display.append("    Not enough data bytes to interpret")


            elif frame_id == 8:  # EvMinVoltages
                result_display.append("  Interpretation: EvMinVoltages")

                if len(databytes) >= 6:
                    ev_sel_ver_str = format_selected_version(databytes[0])
                    result_display.append(f"    EvSelectedVersion: {ev_sel_ver_str}")

                    EvMinVoltageL1N = read_voltage_high_low(databytes[1], databytes[2])
                    EvMinVoltageLL = read_voltage_high_low(databytes[3], databytes[4])

                    volt_l1n_str = format_voltage_value(EvMinVoltageL1N)
                    volt_ll_str = format_voltage_value(EvMinVoltageLL)

                    result_display.append(f"    EvMinVoltageL1N: {volt_l1n_str}")
                    result_display.append(f"    EvMinVoltageLL: {volt_ll_str}")

                    update_init_data("EvSelectedVersion", ev_sel_ver_str)
                    update_init_data("EvMinVoltageL1N", volt_l1n_str)
                    update_init_data("EvMinVoltageLL", volt_ll_str)

                    # EvConnectionType (byte 5)
                    ev_connection_type_map = {
                        0x00: "SAE J3068 AC (IEC 62196-2 Type 2 or GB/T 20234.2) socket-outlet",
                        0x01: "SAE J1772 (IEC 62196-2 Type 1) inlet",
                        0x02: "SAE J3068 AC (IEC 62196-2 Type 2) inlet",
                        0x03: "CCS1 connector",
                        0x04: "CCS2 (SAE J3068 DC/AC or DCa) inlet",
                        0x05: "SAE J3400 inlet",
                        0x06: "GB/T 20234.2 inlet",
                        0xFE: "Error",
                        0xFF: "N/A"
                    }

                    ev_conn_type_val = databytes[5]
                    ev_conn_type_str = ev_connection_type_map.get(
                        ev_conn_type_val,
                        f"Reserved (0x{ev_conn_type_val:02X})"
                    )

                    # Display and store EvConnectionType
                    result_display.append(f"    EvConnectionType: {ev_conn_type_str}")
                    update_op_data("EvConnectionType", ev_conn_type_str)

                else:
                    result_display.append("    Not enough data bytes to interpret")

            elif frame_id == 9:  # EvMaxMinCurrents
                result_display.append("  Interpretation: EvMaxMinCurrents")
                if len(databytes) >= 8:
                    ev_sel_ver_str = format_selected_version(databytes[0])
                    update_ver_data("EvSelectedVersion_EvVersionList", ev_sel_ver_str)
                    result_display.append(f"    EvSelectedVersion: {ev_sel_ver_str}")
                    for i, line_name in enumerate(lines):
                        amps_str = format_amp_value(databytes[i + 1])
                        result_display.append(f"    EvMaxCurrent{line_name}: {amps_str}")
                        update_init_data(f"EvMaxCurrent_{line_name}", amps_str)
                    for i, line_name in enumerate(lines[:3]):
                        amps_str = format_amp_value(databytes[i + 5])
                        result_display.append(f"    EvMinCurrent{line_name}: {amps_str}")
                        update_init_data(f"EvMinCurrent_{line_name}", amps_str)
                else:
                    result_display.append("    Not enough data bytes to interpret")


            elif frame_id == 0x0A:  # Cable Node (10)
                result_display.append("  Interpretation: Cable_Node.")
                if not hasattr(globals, "cable_node_frames"):
                    globals.cable_node_frames = []
                globals.cable_node_frames.append({
                    "frame": frames_parsed,  # current frame number
                    "data": databytes  # list of data bytes (as integers)
                })

                def fmt_val(val):
                    return "N/A" if val == 0xFF else str(val)

                frame_num = frames_parsed
                if databytes[0] == 0x01:
                    version = 1
                elif databytes[0] == 0x02:
                    version = 2
                else:
                    version = f"Unknown ({databytes[0]:02X})"
                result_display.append(f"    CaVersion: {fmt_val(databytes[0])}")
                if version == 1:
                    response_error = databytes[1] & 0x01
                    result_display.append(f"    CaResponseError: {fmt_val(response_error)}")
                    max_voltage = (databytes[3] << 8) | databytes[2]
                    voltage_str = "N/A" if max_voltage == 0xFFFF else f"{max_voltage / 10.0:.1f}"
                    result_display.append(f"    CaMaxVoltage: {voltage_str}")
                    result_display.append(f"    CaMaxCurrentL1: {fmt_val(databytes[4])}")
                    result_display.append(f"    CaMaxCurrentL2: {fmt_val(databytes[5])}")
                    result_display.append(f"    CaMaxCurrentL3: {fmt_val(databytes[6])}")
                    result_display.append(f"    CaMaxCurrentN: {fmt_val(databytes[7])}")

                elif version == 2:
                    response_error = databytes[1] & 0x01
                    connector_type = databytes[1] >> 1
                    result_display.append(f"    CaResponseError: {fmt_val(response_error)}")
                    result_display.append(f"    CaConnectorType: {fmt_val(connector_type)}")
                    insl_class_l1n = databytes[2] & 0x0F
                    insl_class_ll = databytes[2] >> 4
                    result_display.append(f"    CaInslClassL1N: {fmt_val(insl_class_l1n)}")
                    result_display.append(f"    CaInslClassLL: {fmt_val(insl_class_ll)}")
                    ca_prest_l1 = databytes[3] & 0x01
                    ca_prest_l2 = (databytes[3] >> 1) & 0x01
                    ca_prest_l3 = (databytes[3] >> 2) & 0x01
                    ca_prest_n = (databytes[3] >> 3) & 0x01
                    result_display.append(f"    CaPrestL1: {fmt_val(ca_prest_l1)}")
                    result_display.append(f"    CaPrestL2: {fmt_val(ca_prest_l2)}")
                    result_display.append(f"    CaPrestL3: {fmt_val(ca_prest_l3)}")
                    result_display.append(f"    CaPrestN: {fmt_val(ca_prest_n)}")
                    result_display.append(f"    CaMaxCurrentL: {fmt_val(databytes[4])}")
                    result_display.append(f"    CaMaxCurrentN: {fmt_val(databytes[5])}")
                    result_display.append(f"    CaPlugTemp: {fmt_val(databytes[6])}")
                    result_display.append(f"    CaConnectorTemp: {fmt_val(databytes[7])}")

                else:
                    for i, b in enumerate(databytes):
                        result_display.append(f"    Byte {i}: {fmt_val(b)} (Frame: {frame_num})")


            elif frame_id == 0x0B:  # SeInfoList (11)
                result_display.append("  Interpretation: SeInfoList")

                if len(databytes) >= 8:
                    se_sel_ver_str = format_selected_version(databytes[0])
                    update_ver_data("SeSelectedVersion_SeVersionList", se_sel_ver_str)
                    result_display.append(f"    SeSelectedVersion: {se_sel_ver_str}")
                    page_num = databytes[1]
                    result_display.append(f"    SeInfoPageNumber: {page_num}")
                    update_init_data("SeInfoPageNumber", str(page_num))  # store in current_init_data

                    for i in range(1, 7):
                        code_val = databytes[i + 1]
                        hex_str = f"{code_val:02X}"
                        result_display.append(f"    SeInfoEntry{i}: {hex_str}")
                        update_init_data(f"SeInfoEntry{i}", hex_str)

                    update_init_data("SeSelectedVersion", se_sel_ver_str)

                else:
                    result_display.append("    Not enough data bytes to interpret")

            elif frame_id == 0x0C:  # EvInfoList (12)
                result_display.append("  Interpretation: EvInfoList")

                if len(databytes) >= 8:
                    ev_sel_ver_str = format_selected_version(databytes[0])
                    update_ver_data("EvSelectedVersion_EvVersionList", ev_sel_ver_str)
                    result_display.append(f"    EvSelectedVersion: {ev_sel_ver_str}")
                    page_num = databytes[1]
                    result_display.append(f"    EvInfoPageNumber: {page_num}")
                    update_init_data("EvInfoPageNumber", str(page_num))

                    for i in range(1, 7):
                        code_val = databytes[i + 1]
                        hex_str = f"{code_val:02X}"
                        result_display.append(f"    EvInfoEntry{i}: {hex_str}")
                        update_init_data(f"EvInfoEntry{i}", hex_str)
                    update_init_data("EvSelectedVersion", ev_sel_ver_str)

                else:
                    result_display.append("    Not enough data bytes to interpret")



            # --------------OP3--------------
            elif frame_id == 0x0F:  # EvID (15)
                result_display.append("  Interpretation: EvID")
                page = databytes[0]
                update_op_data("EvIDPage", str(page))

                if 0 < page < 251:
                    evID_stage_bytes.extend(databytes)

                if page == 0:
                    result_display.append(f"    EvID Control Page: {page}")
                    if len(databytes) >= 7:
                        # As per Table 3 & Table 11
                        status_val = databytes[1]
                        status_str = format_id_status(status_val, "EV")
                        crc_status_val = databytes[5]
                        crc_status_str = format_crc_status(crc_status_val, "EV")
                        num_prop_pages_val = databytes[6]
                        num_prop_pages_str = format_Num_Prop_Pages(num_prop_pages_val, "EV")

                        update_op_data("EvIDStatus", status_str)
                        update_op_data("EvNumIDPages", str(databytes[2]))
                        update_op_data("EvFirstIDPage", str(databytes[3]))
                        update_op_data("EvLastIDPage", str(databytes[4]))
                        update_op_data("EvCrcStatus", crc_status_str)
                        update_op_data("EvNumPropPages", str(num_prop_pages_str))

                # Table 4: ID Stage
                elif page == 1:
                    result_display.append(f"    EvVIN Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvVIN", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 17)

                elif page == 2:
                    result_display.append(f"    EvVIN Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvVIN", string_position = 7,  data_bytes = databytes[1:8], field_total_length = 17)

                elif page == 3:
                    result_display.append(f"    EvVIN Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvVIN", string_position = 14,  data_bytes = databytes[1:4], field_total_length = 17)

                elif page == 4:
                    result_display.append(f"    EvEMAID Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvEMAID", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 18)

                elif page == 5:
                    result_display.append(f"    EvEMAID Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvEMAID", string_position = 7,  data_bytes = databytes[1:8], field_total_length = 18)

                elif page == 6:
                    result_display.append(f"    EvEMAID Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvEMAID", string_position = 14,  data_bytes = databytes[1:5], field_total_length = 18)

                elif page == 7:
                    result_display.append(f"    EvEVCCID Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvEVCCID", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 8:
                    result_display.append(f"    EvEVCCID Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvEVCCID", string_position = 7,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 9:
                    result_display.append(f"    EvEVCCID Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvEVCCID", string_position = 14,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 10:
                    result_display.append(f"    EvEVCCID Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvEVCCID", string_position = 21,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 11:
                    result_display.append(f"    EvEVCCID Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvEVCCID", string_position = 28,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 12:
                    result_display.append(f"    EvEVCCID Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvEVCCID", string_position = 35,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 13:
                    result_display.append(f"    EvEVCCID Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvEVCCID", string_position = 42,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 14:
                    result_display.append(f"    EvEVCCID Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvEVCCID", string_position = 49,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 15:
                    result_display.append(f"    EvEVCCID Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvEVCCID", string_position = 56,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 16:
                    result_display.append(f"    EvEVCCID Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvEVCCID", string_position = 63,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 17:
                    result_display.append(f"    EvSerialNum Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvSerialNum", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 18:
                    result_display.append(f"    EvSerialNum Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvSerialNum", string_position = 7,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 19:
                    result_display.append(f"    EvSerialNum Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvSerialNum", string_position = 14,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 20:
                    result_display.append(f"    EvSerialNum Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvSerialNum", string_position = 21,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 21:
                    result_display.append(f"    EvSerialNum Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvSerialNum", string_position = 28,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 22:
                    result_display.append(f"    EvSerialNum Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvSerialNum", string_position = 35,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 23:
                    result_display.append(f"    EvDriverID Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvDriverID", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 21)

                elif page == 24:
                    result_display.append(f"    EvDriverID Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvDriverID", string_position = 7,  data_bytes = databytes[1:8], field_total_length = 21)

                elif page == 25:
                    result_display.append(f"    EvDriverID Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvDriverID", string_position = 14,  data_bytes = databytes[1:8], field_total_length = 21)

                elif page == 26:
                    result_display.append(f"    EvVehicleName Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvVehicleName", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 21)

                elif page == 27:
                    result_display.append(f"    EvVehicleName Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvVehicleName", string_position = 7,  data_bytes = databytes[1:8], field_total_length = 21)

                elif page == 28:
                    result_display.append(f"    EvVehicleName Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvVehicleName", string_position = 14,  data_bytes = databytes[1:8], field_total_length = 21)

                elif page == 29:
                    result_display.append(f"    EvFirmwareRevision Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvFirmwareRevision", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 28)

                elif page == 30:
                    result_display.append(f"    EvFirmwareRevision Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvFirmwareRevision", string_position = 7,  data_bytes = databytes[1:8], field_total_length = 28)

                elif page == 31:
                    result_display.append(f"    EvFirmwareRevision Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvFirmwareRevision", string_position = 14,  data_bytes = databytes[1:8], field_total_length = 28)

                elif page == 32:
                    result_display.append(f"    EvFirmwareRevision Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvFirmwareRevision", string_position = 21,  data_bytes = databytes[1:8], field_total_length = 28)

                elif page == 33:
                    result_display.append(f"    EvManufacturer Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvManufacturer", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 34:
                    result_display.append(f"    EvManufacturer Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvManufacturer", string_position = 7,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 35:
                    result_display.append(f"    EvManufacturer Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvManufacturer", string_position = 14,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 36:
                    result_display.append(f"    EvManufacturer Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvManufacturer", string_position = 21,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 37:
                    result_display.append(f"    EvManufacturer Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvManufacturer", string_position = 28,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 38:
                    result_display.append(f"    EvManufacturer Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvManufacturer", string_position = 35,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 39:
                    EvPropDataIdent = (databytes[1])
                    result_display.append(f"    EvPropDataIdent Page: 39")
                    if EvPropDataIdent >= 0xFF:
                        update_op_data("EvPropDataIdent", f"N/A")
                    elif EvPropDataIdent >= 0xFF:
                        update_op_data("EvPropDataIdent", f"Error")
                    elif EvPropDataIdent >= 0xFB:
                        update_op_data("EvPropDataIdent", f"Reserved 0x{EvPropDataIdent:02X}")
                    else:
                        update_op_data("EvPropDataIdent", f"0x{(EvPropDataIdent):02X} ")

                    EvPropDataRev = (databytes[2])
                    result_display.append(f"    EvPropDataRev Page: 39")
                    if EvPropDataRev >= 0xFF:
                        update_op_data("EvPropDataRev", f"N/A")
                    elif EvPropDataRev >= 0xFF:
                        update_op_data("EvPropDataRev", f"Error")
                    elif EvPropDataRev >= 0xFB:
                        update_op_data("EvPropDataRev", f"Reserved 0x{EvPropDataRev:02X}")
                    else:
                        update_op_data("EvPropDataRev", f"0x{(EvPropDataRev):02X} ")

                    result_display.append(f"    EvPropDataSymb Page: {page} (Buffering Data)")
                    process_stage(evID_buffer, "EvPropDataSymb", string_position = 0,  data_bytes = databytes[1:6], field_total_length = 5)



#----------------- Code Gen display_frames paste for Ev_ID Here -----------------------------------------

                # Table 5: Data Stage
                elif page == 97:
                    EvOdometer = (databytes[4] << 24) | (databytes[3] << 16) | (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvOdometer Page: 97")
                    if EvOdometer >= 0xFF000000:
                        update_op_data("EvOdometer", f"N/A")
                    elif EvOdometer >= 0xFF000000:
                        update_op_data("EvOdometer", f"Error")
                    elif EvOdometer >= 0xFB000000:
                        update_op_data("EvOdometer", f"Reserved 0x{EvOdometer:02X}")
                    else:
                        update_op_data("EvOdometer", f"{(EvOdometer * 0.125000):.3f} km")

                    EvStatusInletLatch = (((databytes[5] >> 0) & 0x03))
                    result_display.append(f"    EvStatusInletLatch Page: 97")

                    match EvStatusInletLatch:
                        case 0x00:
                            update_op_data("EvStatusInletLatch", "released")
                        case 0x01:
                            update_op_data("EvStatusInletLatch", "engaged")
                        case 0x02:
                            update_op_data("EvStatusInletLatch", "Error")
                        case 0x03:
                            update_op_data("EvStatusInletLatch", "N/A")
                        case _:
                            update_op_data("EvStatusInletLatch", f"Reserved 0x{EvStatusInletLatch:02X}")

                    EvStatusInletOverride = (((databytes[5] >> 2) & 0x03))
                    result_display.append(f"    EvStatusInletOverride Page: 97")

                    match EvStatusInletOverride:
                        case 0x00:
                            update_op_data("EvStatusInletOverride", "not_active")
                        case 0x01:
                            update_op_data("EvStatusInletOverride", "active")
                        case 0x02:
                            update_op_data("EvStatusInletOverride", "Error")
                        case 0x03:
                            update_op_data("EvStatusInletOverride", "N/A")
                        case _:
                            update_op_data("EvStatusInletOverride", f"Reserved 0x{EvStatusInletOverride:02X}")

                    EvStatusInletLock = (((databytes[5] >> 4) & 0x07))
                    result_display.append(f"    EvStatusInletLock Page: 97")

                    match EvStatusInletLock:
                        case 0x00:
                            update_op_data("EvStatusInletLock", "Unlocked")
                        case 0x01:
                            update_op_data("EvStatusInletLock", "Locked")
                        case 0x02:
                            update_op_data("EvStatusInletLock", "In_transition")
                        case 0x05:
                            update_op_data("EvStatusInletLock", "No_lock")
                        case 0x06:
                            update_op_data("EvStatusInletLock", "Error")
                        case 0x07:
                            update_op_data("EvStatusInletLock", "N/A")
                        case _:
                            update_op_data("EvStatusInletLock", f"Reserved 0x{EvStatusInletLock:02X}")

                elif page == 98:
                    EvNumberJ2012Dtcs = (databytes[1])
                    result_display.append(f"    EvNumberJ2012Dtcs Page: 98")
                    if EvNumberJ2012Dtcs >= 0xFF:
                        update_op_data("EvNumberJ2012Dtcs", f"N/A")
                    elif EvNumberJ2012Dtcs >= 0xFF:
                        update_op_data("EvNumberJ2012Dtcs", f"Error")
                    elif EvNumberJ2012Dtcs >= 0xFB:
                        update_op_data("EvNumberJ2012Dtcs", f"Reserved 0x{EvNumberJ2012Dtcs:02X}")
                    else:
                        update_op_data("EvNumberJ2012Dtcs", f"{(EvNumberJ2012Dtcs)} count")

                    EvJ2012DtcStatus = (((databytes[7] >> 0) & 0x01))
                    result_display.append(f"    EvJ2012DtcStatus Page: 98")

                    match EvJ2012DtcStatus:
                        case 0x00:
                            update_op_data("EvJ2012DtcStatus", "previously_active")
                        case 0x01:
                            update_op_data("EvJ2012DtcStatus", "active")
                        case _:
                            update_op_data("EvJ2012DtcStatus", f"Reserved 0x{EvJ2012DtcStatus:02X}")

                    EvJ2012DtcCount = (((databytes[7] >> 1) & 0x7F))
                    result_display.append(f"    EvJ2012DtcCount Page: 98")
                    if EvJ2012DtcCount >= 0x7F:
                        update_op_data("EvJ2012DtcCount", f"N/A")
                    elif EvJ2012DtcCount >= 0x7F:
                        update_op_data("EvJ2012DtcCount", f"Error")
                    else:
                        update_op_data("EvJ2012DtcCount", f"{(EvJ2012DtcCount)} count")

                elif page == 99:
                    EvHVESSDishargeCapacity = (databytes[3] << 16) | (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvHVESSDishargeCapacity Page: 99")
                    if EvHVESSDishargeCapacity >= 0xFF0000:
                        update_op_data("EvHVESSDishargeCapacity", f"N/A")
                    elif EvHVESSDishargeCapacity >= 0xFF0000:
                        update_op_data("EvHVESSDishargeCapacity", f"Error")
                    elif EvHVESSDishargeCapacity >= 0xFB0000:
                        update_op_data("EvHVESSDishargeCapacity", f"Reserved 0x{EvHVESSDishargeCapacity:02X}")
                    else:
                        update_op_data("EvHVESSDishargeCapacity", f"{(EvHVESSDishargeCapacity * 0.001000):.3f} kWh")

                    EvHVESSChargeCapacity = (databytes[6] << 16) | (databytes[5] << 8) | (databytes[4])
                    result_display.append(f"    EvHVESSChargeCapacity Page: 99")
                    if EvHVESSChargeCapacity >= 0xFF0000:
                        update_op_data("EvHVESSChargeCapacity", f"N/A")
                    elif EvHVESSChargeCapacity >= 0xFF0000:
                        update_op_data("EvHVESSChargeCapacity", f"Error")
                    elif EvHVESSChargeCapacity >= 0xFB0000:
                        update_op_data("EvHVESSChargeCapacity", f"Reserved 0x{EvHVESSChargeCapacity:02X}")
                    else:
                        update_op_data("EvHVESSChargeCapacity", f"{(EvHVESSChargeCapacity * 0.001000):.3f} kWh")

                elif page == 100:
                    EvEnergyForDeparture = (databytes[3] << 16) | (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvEnergyForDeparture Page: 100")
                    if EvEnergyForDeparture >= 0xFF0000:
                        update_op_data("EvEnergyForDeparture", f"N/A")
                    elif EvEnergyForDeparture >= 0xFF0000:
                        update_op_data("EvEnergyForDeparture", f"Error")
                    elif EvEnergyForDeparture >= 0xFB0000:
                        update_op_data("EvEnergyForDeparture", f"Reserved 0x{EvEnergyForDeparture:02X}")
                    else:
                        update_op_data("EvEnergyForDeparture", f"{(EvEnergyForDeparture * 0.001000):.3f} kWh")

                    EvTimeToDeparture = (databytes[5] << 8) | (databytes[4])
                    result_display.append(f"    EvTimeToDeparture Page: 100")
                    if EvTimeToDeparture >= 0xFF00:
                        update_op_data("EvTimeToDeparture", f"N/A")
                    elif EvTimeToDeparture >= 0xFF00:
                        update_op_data("EvTimeToDeparture", f"Error")
                    elif EvTimeToDeparture >= 0xFB00:
                        update_op_data("EvTimeToDeparture", f"Reserved 0x{EvTimeToDeparture:02X}")
                    else:
                        update_op_data("EvTimeToDeparture", f"{(EvTimeToDeparture)} min")

                elif page == 101:
                    EvHVESSRange = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvHVESSRange Page: 101")
                    if EvHVESSRange >= 0xFF00:
                        update_op_data("EvHVESSRange", f"N/A")
                    elif EvHVESSRange >= 0xFF00:
                        update_op_data("EvHVESSRange", f"Error")
                    elif EvHVESSRange >= 0xFB00:
                        update_op_data("EvHVESSRange", f"Reserved 0x{EvHVESSRange:02X}")
                    else:
                        update_op_data("EvHVESSRange", f"{(EvHVESSRange)} km")

                    EvFuelRange = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    EvFuelRange Page: 101")
                    if EvFuelRange >= 0xFF00:
                        update_op_data("EvFuelRange", f"N/A")
                    elif EvFuelRange >= 0xFF00:
                        update_op_data("EvFuelRange", f"Error")
                    elif EvFuelRange >= 0xFB00:
                        update_op_data("EvFuelRange", f"Reserved 0x{EvFuelRange:02X}")
                    else:
                        update_op_data("EvFuelRange", f"{(EvFuelRange)} km")

                    EvEVTimeToEnergyForDept = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    EvEVTimeToEnergyForDept Page: 101")
                    if EvEVTimeToEnergyForDept >= 0xFF00:
                        update_op_data("EvEVTimeToEnergyForDept", f"N/A")
                    elif EvEVTimeToEnergyForDept >= 0xFF00:
                        update_op_data("EvEVTimeToEnergyForDept", f"Error")
                    elif EvEVTimeToEnergyForDept >= 0xFB00:
                        update_op_data("EvEVTimeToEnergyForDept", f"Reserved 0x{EvEVTimeToEnergyForDept:02X}")
                    else:
                        update_op_data("EvEVTimeToEnergyForDept", f"{(EvEVTimeToEnergyForDept)} min")

                elif page == 102:
                    EvDurMin = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvDurMin Page: 102")
                    if EvDurMin >= 0xFF00:
                        update_op_data("EvDurMin", f"N/A")
                    elif EvDurMin >= 0xFF00:
                        update_op_data("EvDurMin", f"Error")
                    elif EvDurMin >= 0xFB00:
                        update_op_data("EvDurMin", f"Reserved 0x{EvDurMin:02X}")
                    else:
                        update_op_data("EvDurMin", f"{(EvDurMin * 10)} s")

                    EvChaDurMax = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    EvChaDurMax Page: 102")
                    if EvChaDurMax >= 0xFF00:
                        update_op_data("EvChaDurMax", f"N/A")
                    elif EvChaDurMax >= 0xFF00:
                        update_op_data("EvChaDurMax", f"Error")
                    elif EvChaDurMax >= 0xFB00:
                        update_op_data("EvChaDurMax", f"Reserved 0x{EvChaDurMax:02X}")
                    else:
                        update_op_data("EvChaDurMax", f"{(EvChaDurMax * 10)} s")

                    EvDschDurMax = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    EvDschDurMax Page: 102")
                    if EvDschDurMax >= 0xFF00:
                        update_op_data("EvDschDurMax", f"N/A")
                    elif EvDschDurMax >= 0xFF00:
                        update_op_data("EvDschDurMax", f"Error")
                    elif EvDschDurMax >= 0xFB00:
                        update_op_data("EvDschDurMax", f"Reserved 0x{EvDschDurMax:02X}")
                    else:
                        update_op_data("EvDschDurMax", f"{(EvDschDurMax * 10)} s")

                elif page == 103:
                    EvTimeReqNum = (databytes[1])
                    result_display.append(f"    EvTimeReqNum Page: 103")
                    if EvTimeReqNum >= 0xFF:
                        update_op_data("EvTimeReqNum", f"N/A")
                    elif EvTimeReqNum >= 0xFF:
                        update_op_data("EvTimeReqNum", f"Error")
                    elif EvTimeReqNum >= 0xFB:
                        update_op_data("EvTimeReqNum", f"Reserved 0x{EvTimeReqNum:02X}")
                    else:
                        update_op_data("EvTimeReqNum", f"0x{(EvTimeReqNum):02X} ")

                    EvEVTimeToRange = (databytes[3] << 8) | (databytes[2])
                    result_display.append(f"    EvEVTimeToRange Page: 103")
                    if EvEVTimeToRange >= 0xFF00:
                        update_op_data("EvEVTimeToRange", f"N/A")
                    elif EvEVTimeToRange >= 0xFF00:
                        update_op_data("EvEVTimeToRange", f"Error")
                    elif EvEVTimeToRange >= 0xFB00:
                        update_op_data("EvEVTimeToRange", f"Reserved 0x{EvEVTimeToRange:02X}")
                    else:
                        update_op_data("EvEVTimeToRange", f"{(EvEVTimeToRange)} min")

                    EvEVTimeToEnergy = (databytes[5] << 8) | (databytes[4])
                    result_display.append(f"    EvEVTimeToEnergy Page: 103")
                    if EvEVTimeToEnergy >= 0xFF00:
                        update_op_data("EvEVTimeToEnergy", f"N/A")
                    elif EvEVTimeToEnergy >= 0xFF00:
                        update_op_data("EvEVTimeToEnergy", f"Error")
                    elif EvEVTimeToEnergy >= 0xFB00:
                        update_op_data("EvEVTimeToEnergy", f"Reserved 0x{EvEVTimeToEnergy:02X}")
                    else:
                        update_op_data("EvEVTimeToEnergy", f"{(EvEVTimeToEnergy)} min")

                elif page == 104:
                    EvHVESSVoltage = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvHVESSVoltage Page: 104")
                    if EvHVESSVoltage >= 0xFF00:
                        update_op_data("EvHVESSVoltage", f"N/A")
                    elif EvHVESSVoltage >= 0xFF00:
                        update_op_data("EvHVESSVoltage", f"Error")
                    elif EvHVESSVoltage >= 0xFB00:
                        update_op_data("EvHVESSVoltage", f"Reserved 0x{EvHVESSVoltage:02X}")
                    else:
                        update_op_data("EvHVESSVoltage", f"{(EvHVESSVoltage * 0.050000):.3f} ")

                    EvHVESSCurrent = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    EvHVESSCurrent Page: 104")
                    if EvHVESSCurrent >= 0xFF00:
                        update_op_data("EvHVESSCurrent", f"N/A")
                    elif EvHVESSCurrent >= 0xFF00:
                        update_op_data("EvHVESSCurrent", f"Error")
                    elif EvHVESSCurrent >= 0xFB00:
                        update_op_data("EvHVESSCurrent", f"Reserved 0x{EvHVESSCurrent:02X}")
                    else:
                        update_op_data("EvHVESSCurrent", f"{(EvHVESSCurrent * 0.050000) - 1600:.3f} ")

                    EvHVESSHealth = (databytes[5])
                    result_display.append(f"    EvHVESSHealth Page: 104")
                    if EvHVESSHealth >= 0xFF:
                        update_op_data("EvHVESSHealth", f"N/A")
                    elif EvHVESSHealth >= 0xFF:
                        update_op_data("EvHVESSHealth", f"Error")
                    elif EvHVESSHealth >= 0xFB:
                        update_op_data("EvHVESSHealth", f"Reserved 0x{EvHVESSHealth:02X}")
                    else:
                        update_op_data("EvHVESSHealth", f"{(EvHVESSHealth * 0.400000):.3f} %")

                    EvHVESSUserSOC = (databytes[6])
                    result_display.append(f"    EvHVESSUserSOC Page: 104")
                    if EvHVESSUserSOC >= 0xFF:
                        update_op_data("EvHVESSUserSOC", f"N/A")
                    elif EvHVESSUserSOC >= 0xFF:
                        update_op_data("EvHVESSUserSOC", f"Error")
                    elif EvHVESSUserSOC >= 0xFB:
                        update_op_data("EvHVESSUserSOC", f"Reserved 0x{EvHVESSUserSOC:02X}")
                    else:
                        update_op_data("EvHVESSUserSOC", f"{(EvHVESSUserSOC * 0.400000):.3f} %")

                elif page == 105:
                    EvACActivePower = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvACActivePower Page: 105")
                    if EvACActivePower >= 0xFF00:
                        update_op_data("EvACActivePower", f"N/A")
                    elif EvACActivePower >= 0xFF00:
                        update_op_data("EvACActivePower", f"Error")
                    elif EvACActivePower >= 0xFB00:
                        update_op_data("EvACActivePower", f"Reserved 0x{EvACActivePower:02X}")
                    else:
                        update_op_data("EvACActivePower", f"{(EvACActivePower * 16) - 500000} W")

                    EvACReactivePower = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    EvACReactivePower Page: 105")
                    if EvACReactivePower >= 0xFF00:
                        update_op_data("EvACReactivePower", f"N/A")
                    elif EvACReactivePower >= 0xFF00:
                        update_op_data("EvACReactivePower", f"Error")
                    elif EvACReactivePower >= 0xFB00:
                        update_op_data("EvACReactivePower", f"Reserved 0x{EvACReactivePower:02X}")
                    else:
                        update_op_data("EvACReactivePower", f"{(EvACReactivePower * 16) - 500000} VA")

                    EvACFrequency = (databytes[5])
                    result_display.append(f"    EvACFrequency Page: 105")
                    if EvACFrequency >= 0xFF:
                        update_op_data("EvACFrequency", f"N/A")
                    elif EvACFrequency >= 0xFF:
                        update_op_data("EvACFrequency", f"Error")
                    elif EvACFrequency >= 0xFB:
                        update_op_data("EvACFrequency", f"Reserved 0x{EvACFrequency:02X}")
                    else:
                        update_op_data("EvACFrequency", f"{(EvACFrequency * 0.100000) - -42.500000:.3f} Hz")

                elif page == 106:
                    EvL1NVolts = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvL1NVolts Page: 106")
                    if EvL1NVolts >= 0xFF00:
                        update_op_data("EvL1NVolts", f"N/A")
                    elif EvL1NVolts >= 0xFF00:
                        update_op_data("EvL1NVolts", f"Error")
                    elif EvL1NVolts >= 0xFB00:
                        update_op_data("EvL1NVolts", f"Reserved 0x{EvL1NVolts:02X}")
                    else:
                        update_op_data("EvL1NVolts", f"{(EvL1NVolts * 0.050000):.3f} Volts")

                    EvL2NVolts = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    EvL2NVolts Page: 106")
                    if EvL2NVolts >= 0xFF00:
                        update_op_data("EvL2NVolts", f"N/A")
                    elif EvL2NVolts >= 0xFF00:
                        update_op_data("EvL2NVolts", f"Error")
                    elif EvL2NVolts >= 0xFB00:
                        update_op_data("EvL2NVolts", f"Reserved 0x{EvL2NVolts:02X}")
                    else:
                        update_op_data("EvL2NVolts", f"{(EvL2NVolts * 0.050000):.3f} Volts")

                    EvL3NVolts = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    EvL3NVolts Page: 106")
                    if EvL3NVolts >= 0xFF00:
                        update_op_data("EvL3NVolts", f"N/A")
                    elif EvL3NVolts >= 0xFF00:
                        update_op_data("EvL3NVolts", f"Error")
                    elif EvL3NVolts >= 0xFB00:
                        update_op_data("EvL3NVolts", f"Reserved 0x{EvL3NVolts:02X}")
                    else:
                        update_op_data("EvL3NVolts", f"{(EvL3NVolts * 0.050000):.3f} Volts")

                elif page == 107:
                    EvAmbientTemp = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvAmbientTemp Page: 107")
                    if EvAmbientTemp >= 0xFF00:
                        update_op_data("EvAmbientTemp", f"N/A")
                    elif EvAmbientTemp >= 0xFF00:
                        update_op_data("EvAmbientTemp", f"Error")
                    elif EvAmbientTemp >= 0xFB00:
                        update_op_data("EvAmbientTemp", f"Reserved 0x{EvAmbientTemp:02X}")
                    else:
                        update_op_data("EvAmbientTemp", f"{(EvAmbientTemp * 0.031250) - 273:.3f} C")

                    EvCabinTemp = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    EvCabinTemp Page: 107")
                    if EvCabinTemp >= 0xFF00:
                        update_op_data("EvCabinTemp", f"N/A")
                    elif EvCabinTemp >= 0xFF00:
                        update_op_data("EvCabinTemp", f"Error")
                    elif EvCabinTemp >= 0xFB00:
                        update_op_data("EvCabinTemp", f"Reserved 0x{EvCabinTemp:02X}")
                    else:
                        update_op_data("EvCabinTemp", f"{(EvCabinTemp * 0.031250) - 273:.3f} C")

                elif page == 108:
                    EvHVESSCellTemp = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvHVESSCellTemp Page: 108")
                    if EvHVESSCellTemp >= 0xFF00:
                        update_op_data("EvHVESSCellTemp", f"N/A")
                    elif EvHVESSCellTemp >= 0xFF00:
                        update_op_data("EvHVESSCellTemp", f"Error")
                    elif EvHVESSCellTemp >= 0xFB00:
                        update_op_data("EvHVESSCellTemp", f"Reserved 0x{EvHVESSCellTemp:02X}")
                    else:
                        update_op_data("EvHVESSCellTemp", f"{(EvHVESSCellTemp * 0.031250) - 273:.3f} C")

                    EvMaxHVESSTemp = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    EvMaxHVESSTemp Page: 108")
                    if EvMaxHVESSTemp >= 0xFF00:
                        update_op_data("EvMaxHVESSTemp", f"N/A")
                    elif EvMaxHVESSTemp >= 0xFF00:
                        update_op_data("EvMaxHVESSTemp", f"Error")
                    elif EvMaxHVESSTemp >= 0xFB00:
                        update_op_data("EvMaxHVESSTemp", f"Reserved 0x{EvMaxHVESSTemp:02X}")
                    else:
                        update_op_data("EvMaxHVESSTemp", f"{(EvMaxHVESSTemp * 0.031250) - 273:.3f} C")

                    EvMinHVESSTemp = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    EvMinHVESSTemp Page: 108")
                    if EvMinHVESSTemp >= 0xFF00:
                        update_op_data("EvMinHVESSTemp", f"N/A")
                    elif EvMinHVESSTemp >= 0xFF00:
                        update_op_data("EvMinHVESSTemp", f"Error")
                    elif EvMinHVESSTemp >= 0xFB00:
                        update_op_data("EvMinHVESSTemp", f"Reserved 0x{EvMinHVESSTemp:02X}")
                    else:
                        update_op_data("EvMinHVESSTemp", f"{(EvMinHVESSTemp * 0.031250) - 273:.3f} C")

                    EvHVESSElecTemp = (databytes[7])
                    result_display.append(f"    EvHVESSElecTemp Page: 108")
                    if EvHVESSElecTemp >= 0xFF:
                        update_op_data("EvHVESSElecTemp", f"N/A")
                    elif EvHVESSElecTemp >= 0xFF:
                        update_op_data("EvHVESSElecTemp", f"Error")
                    elif EvHVESSElecTemp >= 0xFB:
                        update_op_data("EvHVESSElecTemp", f"Reserved 0x{EvHVESSElecTemp:02X}")
                    else:
                        update_op_data("EvHVESSElecTemp", f"{(EvHVESSElecTemp) - 40} C")

                elif page == 109:
                    EvMaxHVESSCellVolt = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvMaxHVESSCellVolt Page: 109")
                    if EvMaxHVESSCellVolt >= 0xFF00:
                        update_op_data("EvMaxHVESSCellVolt", f"N/A")
                    elif EvMaxHVESSCellVolt >= 0xFF00:
                        update_op_data("EvMaxHVESSCellVolt", f"Error")
                    elif EvMaxHVESSCellVolt >= 0xFB00:
                        update_op_data("EvMaxHVESSCellVolt", f"Reserved 0x{EvMaxHVESSCellVolt:02X}")
                    else:
                        update_op_data("EvMaxHVESSCellVolt", f"{(EvMaxHVESSCellVolt * 0.001000):.3f} V")

                    EvMinHVESSCellVolt = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    EvMinHVESSCellVolt Page: 109")
                    if EvMinHVESSCellVolt >= 0xFF00:
                        update_op_data("EvMinHVESSCellVolt", f"N/A")
                    elif EvMinHVESSCellVolt >= 0xFF00:
                        update_op_data("EvMinHVESSCellVolt", f"Error")
                    elif EvMinHVESSCellVolt >= 0xFB00:
                        update_op_data("EvMinHVESSCellVolt", f"Reserved 0x{EvMinHVESSCellVolt:02X}")
                    else:
                        update_op_data("EvMinHVESSCellVolt", f"{(EvMinHVESSCellVolt * 0.001000):.3f} V")

                    EvNumHVESSCellBalancing = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    EvNumHVESSCellBalancing Page: 109")
                    if EvNumHVESSCellBalancing >= 0xFF00:
                        update_op_data("EvNumHVESSCellBalancing", f"N/A")
                    elif EvNumHVESSCellBalancing >= 0xFF00:
                        update_op_data("EvNumHVESSCellBalancing", f"Error")
                    elif EvNumHVESSCellBalancing >= 0xFB00:
                        update_op_data("EvNumHVESSCellBalancing", f"Reserved 0x{EvNumHVESSCellBalancing:02X}")
                    else:
                        update_op_data("EvNumHVESSCellBalancing", f"{(EvNumHVESSCellBalancing)} ")

                    EvStatusCellVoltDiff = (((databytes[7] >> 0) & 0x0F))
                    result_display.append(f"    EvStatusCellVoltDiff Page: 109")

                    match EvStatusCellVoltDiff:
                        case 0x00:
                            update_op_data("EvStatusCellVoltDiff", "within_acceptable_limits")
                        case 0x01:
                            update_op_data("EvStatusCellVoltDiff", "can_be_corrected")
                        case 0x02:
                            update_op_data("EvStatusCellVoltDiff", "maintenance_can_restore_performance")
                        case 0x03:
                            update_op_data("EvStatusCellVoltDiff", "maintenance_cannot_restore_performance")
                        case 0x04:
                            update_op_data("EvStatusCellVoltDiff", "performance_restoration_unknown")
                        case 0x0E:
                            update_op_data("EvStatusCellVoltDiff", "Error")
                        case 0x0F:
                            update_op_data("EvStatusCellVoltDiff", "N/A")
                        case _:
                            update_op_data("EvStatusCellVoltDiff", f"Reserved 0x{EvStatusCellVoltDiff:02X}")

                    EvStatusCellBal = (((databytes[7] >> 4) & 0x03))
                    result_display.append(f"    EvStatusCellBal Page: 109")

                    match EvStatusCellBal:
                        case 0x00:
                            update_op_data("EvStatusCellBal", "balanced")
                        case 0x01:
                            update_op_data("EvStatusCellBal", "unbalanced")
                        case 0x02:
                            update_op_data("EvStatusCellBal", "Error")
                        case 0x03:
                            update_op_data("EvStatusCellBal", "N/A")
                        case _:
                            update_op_data("EvStatusCellBal", f"Reserved 0x{EvStatusCellBal:02X}")

                    EvActiveCellBal = (((databytes[7] >> 6) & 0x03))
                    result_display.append(f"    EvActiveCellBal Page: 109")

                    match EvActiveCellBal:
                        case 0x00:
                            update_op_data("EvActiveCellBal", "not_active")
                        case 0x01:
                            update_op_data("EvActiveCellBal", "active")
                        case 0x02:
                            update_op_data("EvActiveCellBal", "Error")
                        case 0x03:
                            update_op_data("EvActiveCellBal", "N/A")
                        case _:
                            update_op_data("EvActiveCellBal", f"Reserved 0x{EvActiveCellBal:02X}")

                elif page == 110:
                    EvChargerTemp = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvChargerTemp Page: 110")
                    if EvChargerTemp >= 0xFF00:
                        update_op_data("EvChargerTemp", f"N/A")
                    elif EvChargerTemp >= 0xFF00:
                        update_op_data("EvChargerTemp", f"Error")
                    elif EvChargerTemp >= 0xFB00:
                        update_op_data("EvChargerTemp", f"Reserved 0x{EvChargerTemp:02X}")
                    else:
                        update_op_data("EvChargerTemp", f"{(EvChargerTemp * 0.031250) - 273:.3f} C")

                    EvMaxChargerTemp = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    EvMaxChargerTemp Page: 110")
                    if EvMaxChargerTemp >= 0xFF00:
                        update_op_data("EvMaxChargerTemp", f"N/A")
                    elif EvMaxChargerTemp >= 0xFF00:
                        update_op_data("EvMaxChargerTemp", f"Error")
                    elif EvMaxChargerTemp >= 0xFB00:
                        update_op_data("EvMaxChargerTemp", f"Reserved 0x{EvMaxChargerTemp:02X}")
                    else:
                        update_op_data("EvMaxChargerTemp", f"{(EvMaxChargerTemp * 0.031250) - 273:.3f} C")

                    EvInletTemp = (databytes[5])
                    result_display.append(f"    EvInletTemp Page: 110")
                    if EvInletTemp >= 0xFF:
                        update_op_data("EvInletTemp", f"N/A")
                    elif EvInletTemp >= 0xFF:
                        update_op_data("EvInletTemp", f"Error")
                    elif EvInletTemp >= 0xFB:
                        update_op_data("EvInletTemp", f"Reserved 0x{EvInletTemp:02X}")
                    else:
                        update_op_data("EvInletTemp", f"{(EvInletTemp) - 40} C")

                    EvHVESSTemp = (databytes[6])
                    result_display.append(f"    EvHVESSTemp Page: 110")
                    if EvHVESSTemp >= 0xFF:
                        update_op_data("EvHVESSTemp", f"N/A")
                    elif EvHVESSTemp >= 0xFF:
                        update_op_data("EvHVESSTemp", f"Error")
                    elif EvHVESSTemp >= 0xFB:
                        update_op_data("EvHVESSTemp", f"Reserved 0x{EvHVESSTemp:02X}")
                    else:
                        update_op_data("EvHVESSTemp", f"{(EvHVESSTemp) - 40} C")

                elif page == 251:
                    EvCrc32 = (databytes[4] << 24) | (databytes[3] << 16) | (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"   EvCrc32 Page: 251")
                    result_display.append(f"   EvCrc32 from frame = 0x{EvCrc32:08X}")
                    is_match, computed_crc = crc_check( EvCrc32, evID_stage_bytes)
                    if is_match:
                        result_display.append(f"    <b><span style='color:green;'>    &nbsp;&nbsp;&nbsp;CRC Check: MATCH</span></b> (Computed: 0x{computed_crc:08X})")
                    else:
                        result_display.append(f"    <b><span style='color:red;'>    &nbsp;&nbsp;&nbsp;CRC Check: MISMATCH</span></b> (Computed: 0x{computed_crc:08X})")

                    evID_stage_bytes.clear()


# ----------------- End of Code Gen display_frames paste for Ev_ID Here -----------------------------------------

            elif frame_id == 0x10:  # SeID (16)
                result_display.append("  Interpretation: SeID")
                page = databytes[0]
                update_op_data("SeIDPage", str(page))

                if 0 < page < 251:
                    seID_stage_bytes.extend(databytes)

                if page == 0:
                    result_display.append(f"    SeID Control Page: {page}")
                    if len(databytes) >= 7:
                        # As per Table 6 & Table 14
                        status_val = databytes[1]
                        status_str = format_id_status(status_val, "SE")
                        crc_status_val = databytes[5]
                        crc_status_str = format_crc_status(crc_status_val, "SE")
                        num_prop_pages_val = databytes[6]
                        num_prop_pages_str = format_Num_Prop_Pages(num_prop_pages_val, "SE")

                        update_op_data("SeIDStatus", status_str)
                        update_op_data("SeNumIDPages", str(databytes[2]))
                        update_op_data("SeFirstIDPage", str(databytes[3]))
                        update_op_data("SeLastIDPage", str(databytes[4]))
                        update_op_data("SeCrcStatus", crc_status_str)
                        update_op_data("SeNumPropPages", str(num_prop_pages_str))

                # Table 7: ID Stage
                elif page == 1:
                    result_display.append(f"    SeEVSEID Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeEVSEID", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 40)

                elif page == 2:
                    result_display.append(f"    SeEVSEID Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeEVSEID", string_position = 7,  data_bytes = databytes[1:8], field_total_length = 40)

                elif page == 3:
                    result_display.append(f"    SeEVSEID Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeEVSEID", string_position = 14,  data_bytes = databytes[1:8], field_total_length = 40)

                elif page == 4:
                    result_display.append(f"    SeEVSEID Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeEVSEID", string_position = 21,  data_bytes = databytes[1:8], field_total_length = 40)

                elif page == 5:
                    result_display.append(f"    SeEVSEID Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeEVSEID", string_position = 28,  data_bytes = databytes[1:8], field_total_length = 40)

                elif page == 6:
                    result_display.append(f"    SeEVSEID Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeEVSEID", string_position = 35,  data_bytes = databytes[1:6], field_total_length = 40)

                elif page == 7:
                    result_display.append(f"    SeSECCID Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeSECCID", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 8:
                    result_display.append(f"    SeSECCID Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeSECCID", string_position = 7,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 9:
                    result_display.append(f"    SeSECCID Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeSECCID", string_position = 14,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 10:
                    result_display.append(f"    SeSECCID Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeSECCID", string_position = 21,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 11:
                    result_display.append(f"    SeSECCID Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeSECCID", string_position = 28,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 12:
                    result_display.append(f"    SeSECCID Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeSECCID", string_position = 35,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 13:
                    result_display.append(f"    SeSECCID Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeSECCID", string_position = 42,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 14:
                    result_display.append(f"    SeSECCID Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeSECCID", string_position = 49,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 15:
                    result_display.append(f"    SeSECCID Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeSECCID", string_position = 56,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 16:
                    result_display.append(f"    SeSECCID Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeSECCID", string_position = 63,  data_bytes = databytes[1:8], field_total_length = 70)

                elif page == 17:
                    result_display.append(f"    SeSerialNum Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeSerialNum", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 18:
                    result_display.append(f"    SeSerialNum Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeSerialNum", string_position = 7,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 19:
                    result_display.append(f"    SeSerialNum Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeSerialNum", string_position = 14,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 20:
                    result_display.append(f"    SeSerialNum Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeSerialNum", string_position = 21,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 21:
                    result_display.append(f"    SeSerialNum Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeSerialNum", string_position = 28,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 22:
                    result_display.append(f"    SeSerialNum Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeSerialNum", string_position = 35,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 23:
                    result_display.append(f"    SeFirmwareRevision Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeFirmwareRevision", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 28)

                elif page == 24:
                    result_display.append(f"    SeFirmwareRevision Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeFirmwareRevision", string_position = 7,  data_bytes = databytes[1:8], field_total_length = 28)

                elif page == 25:
                    result_display.append(f"    SeFirmwareRevision Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeFirmwareRevision", string_position = 14,  data_bytes = databytes[1:8], field_total_length = 28)

                elif page == 26:
                    result_display.append(f"    SeFirmwareRevision Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeFirmwareRevision", string_position = 21,  data_bytes = databytes[1:8], field_total_length = 28)

                elif page == 27:
                    result_display.append(f"    SeManufacturer Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeManufacturer", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 28:
                    result_display.append(f"    SeManufacturer Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeManufacturer", string_position = 7,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 29:
                    result_display.append(f"    SeManufacturer Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeManufacturer", string_position = 14,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 30:
                    result_display.append(f"    SeManufacturer Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeManufacturer", string_position = 21,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 31:
                    result_display.append(f"    SeManufacturer Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeManufacturer", string_position = 28,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 32:
                    result_display.append(f"    SeManufacturer Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeManufacturer", string_position = 35,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 33:
                    result_display.append(f"    SePublicName Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SePublicName", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 34:
                    result_display.append(f"    SePublicName Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SePublicName", string_position = 7,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 35:
                    result_display.append(f"    SePublicName Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SePublicName", string_position = 14,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 36:
                    result_display.append(f"    SePublicName Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SePublicName", string_position = 21,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 37:
                    result_display.append(f"    SePublicName Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SePublicName", string_position = 28,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 38:
                    result_display.append(f"    SePublicName Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SePublicName", string_position = 35,  data_bytes = databytes[1:8], field_total_length = 42)

                elif page == 39:
                    result_display.append(f"    SePlcMac48Address Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SePlcMac48Address", string_position = 0,  data_bytes = databytes[1:7], field_total_length = 6)

                elif page == 40:
                    result_display.append(f"    SeWiFiMac64Address1 Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeWiFiMac64Address1", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 8)

                elif page == 41:
                    result_display.append(f"    SeWiFiMac64Address1 Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeWiFiMac64Address1", string_position = 7,  data_bytes = databytes[1:2], field_total_length = 8)

                    result_display.append(f"    SeWiFiMac64Address2 Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeWiFiMac64Address2", string_position = 0,  data_bytes = databytes[1:7], field_total_length = 8)

                elif page == 42:
                    result_display.append(f"    SeWiFiMac64Address2 Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeWiFiMac64Address2", string_position = 6,  data_bytes = databytes[1:3], field_total_length = 8)

                    result_display.append(f"    SeWiFiMac64Address3 Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeWiFiMac64Address3", string_position = 0,  data_bytes = databytes[1:6], field_total_length = 8)

                elif page == 43:
                    result_display.append(f"    SeWiFiMac64Address3 Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeWiFiMac64Address3", string_position = 5,  data_bytes = databytes[1:4], field_total_length = 8)

                    result_display.append(f"    SeWiFiMac64Address4 Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeWiFiMac64Address4", string_position = 0,  data_bytes = databytes[1:5], field_total_length = 8)

                elif page == 44:
                    result_display.append(f"    SeWiFiMac64Address4 Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeWiFiMac64Address4", string_position = 4,  data_bytes = databytes[1:5], field_total_length = 8)

                    result_display.append(f"    SeWiFiMac64Address5 Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeWiFiMac64Address5", string_position = 0,  data_bytes = databytes[1:4], field_total_length = 8)

                elif page == 45:
                    result_display.append(f"    SeWiFiMac64Address5 Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeWiFiMac64Address5", string_position = 3,  data_bytes = databytes[1:6], field_total_length = 8)

                    result_display.append(f"    SeWiFiMac64Address6 Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeWiFiMac64Address6", string_position = 0,  data_bytes = databytes[1:3], field_total_length = 8)

                elif page == 46:
                    result_display.append(f"    SeWiFiMac64Address6 Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeWiFiMac64Address6", string_position = 2,  data_bytes = databytes[1:7], field_total_length = 8)

                    result_display.append(f"    SeWiFiMac64Address7 Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeWiFiMac64Address7", string_position = 0,  data_bytes = databytes[1:2], field_total_length = 8)

                elif page == 47:
                    result_display.append(f"    SeWiFiMac64Address7 Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SeWiFiMac64Address7", string_position = 1,  data_bytes = databytes[1:8], field_total_length = 8)

                elif page == 48:
                    SePropDataIdent = (databytes[1])
                    result_display.append(f"    SePropDataIdent Page: 48")
                    if SePropDataIdent >= 0xFF:
                        update_op_data("SePropDataIdent", f"N/A")
                    elif SePropDataIdent >= 0xFF:
                        update_op_data("SePropDataIdent", f"Error")
                    elif SePropDataIdent >= 0xFB:
                        update_op_data("SePropDataIdent", f"Reserved 0x{SePropDataIdent:02X}")
                    else:
                        update_op_data("SePropDataIdent", f"0x{(SePropDataIdent):02X} ")

                    SePropDataRev = (databytes[2])
                    result_display.append(f"    SePropDataRev Page: 48")
                    if SePropDataRev >= 0xFF:
                        update_op_data("SePropDataRev", f"N/A")
                    elif SePropDataRev >= 0xFF:
                        update_op_data("SePropDataRev", f"Error")
                    elif SePropDataRev >= 0xFB:
                        update_op_data("SePropDataRev", f"Reserved 0x{SePropDataRev:02X}")
                    else:
                        update_op_data("SePropDataRev", f"{(SePropDataRev)} count")

                    result_display.append(f"    SePropDataSymb Page: {page} (Buffering Data)")
                    process_stage(seID_buffer, "SePropDataSymb", string_position = 0,  data_bytes = databytes[1:6], field_total_length = 5)


# ----------------- Code Gen display_frames paste for Se_ID Here -----------------------------------------
                # Table 8: Data Stage
                elif page == 97:
                    SeAmbientTemp = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    SeAmbientTemp Page: 97")
                    if SeAmbientTemp >= 0xFF00:
                        update_op_data("SeAmbientTemp", f"N/A")
                    elif SeAmbientTemp >= 0xFF00:
                        update_op_data("SeAmbientTemp", f"Error")
                    elif SeAmbientTemp >= 0xFB00:
                        update_op_data("SeAmbientTemp", f"Reserved 0x{SeAmbientTemp:02X}")
                    else:
                        update_op_data("SeAmbientTemp", f"{(SeAmbientTemp * 0.031250) - 273:.3f} C")

                    SeConnectorTemp = (databytes[3])
                    result_display.append(f"    SeConnectorTemp Page: 97")
                    if SeConnectorTemp >= 0xFF:
                        update_op_data("SeConnectorTemp", f"N/A")
                    elif SeConnectorTemp >= 0xFF:
                        update_op_data("SeConnectorTemp", f"Error")
                    elif SeConnectorTemp >= 0xFB:
                        update_op_data("SeConnectorTemp", f"Reserved 0x{SeConnectorTemp:02X}")
                    else:
                        update_op_data("SeConnectorTemp", f"{(SeConnectorTemp) - 40} C")

                    SeOutletTemp = (databytes[4])
                    result_display.append(f"    SeOutletTemp Page: 97")
                    if SeOutletTemp >= 0xFF:
                        update_op_data("SeOutletTemp", f"N/A")
                    elif SeOutletTemp >= 0xFF:
                        update_op_data("SeOutletTemp", f"Error")
                    elif SeOutletTemp >= 0xFB:
                        update_op_data("SeOutletTemp", f"Reserved 0x{SeOutletTemp:02X}")
                    else:
                        update_op_data("SeOutletTemp", f"{(SeOutletTemp) - 40} C")

                    SeEvStatusOutletOverride = (((databytes[5] >> 0) & 0x03))
                    result_display.append(f"    SeEvStatusOutletOverride Page: 97")

                    match SeEvStatusOutletOverride:
                        case 0x00:
                            update_op_data("SeEvStatusOutletOverride", "not_active")
                        case 0x01:
                            update_op_data("SeEvStatusOutletOverride", "active")
                        case 0x02:
                            update_op_data("SeEvStatusOutletOverride", "Error")
                        case 0x03:
                            update_op_data("SeEvStatusOutletOverride", "N/A")
                        case _:
                            update_op_data("SeEvStatusOutletOverride", f"Reserved 0x{SeEvStatusOutletOverride:02X}")

                    SeEvStatusOutletLock = (((databytes[5] >> 2) & 0x07))
                    result_display.append(f"    SeEvStatusOutletLock Page: 97")

                    match SeEvStatusOutletLock:
                        case 0x00:
                            update_op_data("SeEvStatusOutletLock", "Unlocked")
                        case 0x01:
                            update_op_data("SeEvStatusOutletLock", "Locked")
                        case 0x02:
                            update_op_data("SeEvStatusOutletLock", "In_transition")
                        case 0x05:
                            update_op_data("SeEvStatusOutletLock", "No_lock")
                        case 0x06:
                            update_op_data("SeEvStatusOutletLock", "Error")
                        case 0x07:
                            update_op_data("SeEvStatusOutletLock", "N/A")
                        case _:
                            update_op_data("SeEvStatusOutletLock", f"Reserved 0x{SeEvStatusOutletLock:02X}")

                elif page == 98:
                    SeRmtMgmtStatus = (databytes[1])
                    result_display.append(f"    SeRmtMgmtStatus Page: 98")

                    match SeRmtMgmtStatus:
                        case 0x00:
                            update_op_data("SeRmtMgmtStatus", "connected")
                        case 0x01:
                            update_op_data("SeRmtMgmtStatus", "connecting")
                        case 0x02:
                            update_op_data("SeRmtMgmtStatus", "not_connected")
                        case 0x03:
                            update_op_data("SeRmtMgmtStatus", "fallback")
                        case 0x04:
                            update_op_data("SeRmtMgmtStatus", "local")
                        case 0xFE:
                            update_op_data("SeRmtMgmtStatus", "error")
                        case 0xFF:
                            update_op_data("SeRmtMgmtStatus", "none_or_status_unknown")
                        case _:
                            update_op_data("SeRmtMgmtStatus", f"Reserved 0x{SeRmtMgmtStatus:02X}")

                    SeEvTripStatus = (databytes[2])
                    result_display.append(f"    SeEvTripStatus Page: 98")

                    match SeEvTripStatus:
                        case 0x00:
                            update_op_data("SeEvTripStatus", "not_present")
                        case 0x01:
                            update_op_data("SeEvTripStatus", "following")
                        case 0x02:
                            update_op_data("SeEvTripStatus", "cannot_be_met")
                        case 0xFE:
                            update_op_data("SeEvTripStatus", "invalid")
                        case 0xFF:
                            update_op_data("SeEvTripStatus", "not_supported")
                        case _:
                            update_op_data("SeEvTripStatus", f"Reserved 0x{SeEvTripStatus:02X}")

                    SeSeTripStatus = (databytes[3])
                    result_display.append(f"    SeSeTripStatus Page: 98")

                    match SeSeTripStatus:
                        case 0x00:
                            update_op_data("SeSeTripStatus", "not_present")
                        case 0x01:
                            update_op_data("SeSeTripStatus", "following")
                        case 0x02:
                            update_op_data("SeSeTripStatus", "cannot_be_met")
                        case 0x03:
                            update_op_data("SeSeTripStatus", "EV_precedence")
                        case 0xFE:
                            update_op_data("SeSeTripStatus", "cannot_retrieve")
                        case 0xFF:
                            update_op_data("SeSeTripStatus", "not_supported")
                        case _:
                            update_op_data("SeSeTripStatus", f"Reserved 0x{SeSeTripStatus:02X}")

                    SeExptTripPerct = (databytes[4])
                    result_display.append(f"    SeExptTripPerct Page: 98")
                    if SeExptTripPerct >= 0xFF:
                        update_op_data("SeExptTripPerct", f"N/A")
                    elif SeExptTripPerct >= 0xFF:
                        update_op_data("SeExptTripPerct", f"Error")
                    elif SeExptTripPerct >= 0xFB:
                        update_op_data("SeExptTripPerct", f"Reserved 0x{SeExptTripPerct:02X}")
                    else:
                        update_op_data("SeExptTripPerct", f"{(SeExptTripPerct * 0.400000):.3f} %")

                elif page == 99:
                    SeTimeReqNum = (databytes[1])
                    result_display.append(f"    SeTimeReqNum Page: 99")
                    if SeTimeReqNum >= 0xFF:
                        update_op_data("SeTimeReqNum", f"N/A")
                    elif SeTimeReqNum >= 0xFF:
                        update_op_data("SeTimeReqNum", f"Error")
                    elif SeTimeReqNum >= 0xFB:
                        update_op_data("SeTimeReqNum", f"Reserved 0x{SeTimeReqNum:02X}")
                    else:
                        update_op_data("SeTimeReqNum", f"{(SeTimeReqNum)} count")

                    SeHVESSRangeCalc = (databytes[3] << 8) | (databytes[2])
                    result_display.append(f"    SeHVESSRangeCalc Page: 99")
                    if SeHVESSRangeCalc >= 0xFF00:
                        update_op_data("SeHVESSRangeCalc", f"N/A")
                    elif SeHVESSRangeCalc >= 0xFF00:
                        update_op_data("SeHVESSRangeCalc", f"Error")
                    elif SeHVESSRangeCalc >= 0xFB00:
                        update_op_data("SeHVESSRangeCalc", f"Reserved 0x{SeHVESSRangeCalc:02X}")
                    else:
                        update_op_data("SeHVESSRangeCalc", f"{(SeHVESSRangeCalc)} km")

                    SeHVESSEnergyCalc = (databytes[6] << 16) | (databytes[5] << 8) | (databytes[4])
                    result_display.append(f"    SeHVESSEnergyCalc Page: 99")
                    if SeHVESSEnergyCalc >= 0xFF0000:
                        update_op_data("SeHVESSEnergyCalc", f"N/A")
                    elif SeHVESSEnergyCalc >= 0xFF0000:
                        update_op_data("SeHVESSEnergyCalc", f"Error")
                    elif SeHVESSEnergyCalc >= 0xFB0000:
                        update_op_data("SeHVESSEnergyCalc", f"Reserved 0x{SeHVESSEnergyCalc:02X}")
                    else:
                        update_op_data("SeHVESSEnergyCalc", f"{(SeHVESSEnergyCalc * 0.001000):.3f} kWh")

                elif page == 251:
                    SeCrc32 = (databytes[4] << 24) | (databytes[3] << 16) | (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"   SeCrc32 Page: 251")
                    result_display.append(f"   SeCrc32 from frame = 0x{SeCrc32:08X}")
                    is_match, computed_crc = crc_check( SeCrc32, seID_stage_bytes)
                    if is_match:
                        result_display.append(f"    <b><span style='color:green;'>    &nbsp;&nbsp;&nbsp;CRC Check: MATCH</span></b> (Computed: 0x{computed_crc:08X})")
                    else:
                        result_display.append(f"    <b><span style='color:red;'>    &nbsp;&nbsp;&nbsp;CRC Check: MISMATCH</span></b> (Computed: 0x{computed_crc:08X})")

                    seID_stage_bytes.clear()

# ----------------- End of Code Gen display_frames paste for Se_ID Here -----------------------------------------

            elif frame_id == 0x15:  # EvModeCtrl (21)
                result_display.append("  Interpretation: EvModeCtrl")
                if len(databytes) >= 8:
                    # --- EvGridCodeStatus & EvGridCodeStatusMod (Bytes 0-1) ---
                    raw_grid_code = (databytes[1] << 8) | databytes[0]
                    grid_code_mod_val = (raw_grid_code >> 15) & 0x01
                    grid_code_status_val = raw_grid_code & 0x7FFF

                    grid_code_mod_str = "Modified" if grid_code_mod_val == 0 else "Unmodified/Not Configured"

                    grid_code_status_map = {
                        0x0000: "not_supported", 0x0001: "Basic V2G settings A configured",
                        0x0002: "Basic V2X settings B configured", 0x0003: "UL 1741-SA defaults configured",
                        0x0004: "IEEE 1547-2018/UL 1741-SB defaults configured", 0x7FFE: "Error",
                        0x7FFF: "Unconfigured (start value)"
                    }
                    grid_code_status_str = grid_code_status_map.get(grid_code_status_val, f"Manufacturer-defined ({grid_code_status_val:04X})")

                    result_display.append(f"    EvGridCodeStatus: {grid_code_status_str}")
                    result_display.append(f"    EvGridCodeStatusMod: {grid_code_mod_str}")
                    update_op_data("EvGridCodeStatus", grid_code_status_str)
                    update_op_data("EvGridCodeStatusMod", grid_code_mod_str)

                    # --- EvInverterState (Byte 2) ---
                    inverter_state_val = databytes[2] & 0x0F
                    inverter_state_map = {
                        0: "Disconnected/Off", 1: "Deep Sleep Offline", 2: "Deep Sleep Online",
                        3: "Light/Transparent Sleep", 4: "Active/On", 5: "In transition",
                        0x0E: "Error", 0x0F: "Not Available"
                    }
                    inverter_state_str = inverter_state_map.get(inverter_state_val, "Reserved")
                    result_display.append(f"    EvInverterState: {inverter_state_str}")
                    update_op_data("EvInverterState", inverter_state_str)

                    # --- EvPwrCtrlModeAck (Byte 3) ---
                    ack_val = databytes[3]
                    ack_map = {
                        0xFF: "Normal Charging", 0xB4: "CCL", 0xA3: "TC (P-)",
                        0x9A: "TGC (P±)", 0x8D: "TC+R (II & III)", 0x72: "TGC+R (I, II, III, & IV)",
                        0x39: "Autonomous/External Control", 0x17: "Local EPS Forming (V2L/H)",
                        0x00: "Processing", 0xE8: "RESERVED", 0xD1: "RESERVED", 0xC6: "RESERVED",
                        0x65: "RESERVED", 0x5C: "RESERVED", 0x2E: "RESERVED"
                    }
                    ack_str = ack_map.get(ack_val, "Invalid/Reserved")
                    result_display.append(f"    EvPwrCtrlModeAck: {ack_str}")
                    update_op_data("EvPwrCtrlModeAck", ack_str)

                    # --- EvPwrCtrlUnitsAvail (Bytes 4-5) ---
                    units_val = (databytes[5] << 8) | databytes[4]
                    units_list = []
                    if units_val & 0x0001: units_list.append("% Max Watt")
                    if units_val & 0x0002: units_list.append("Current per phase")
                    if units_val & 0x0004: units_list.append("Total Watt")
                    if units_val & 0x0100: units_list.append("% Max Watt + % Max VAR")
                    if units_val & 0x0200: units_list.append("Current per phase + PF")
                    if units_val & 0x0400: units_list.append("Current per phase + Phase Angle")
                    if units_val & 0x0800: units_list.append("Total Watt + Total VAR")
                    units_str = ", ".join(units_list) if units_list else "None"
                    result_display.append(f"    EvPwrCtrlUnitsAvail: {units_str}")
                    update_op_data("EvPwrCtrlUnitsAvail", units_str)

                    # --- EvPwrCtrlModesAvail (Bytes 6-7) ---
                    modes_val = (databytes[7] << 8) | databytes[6]
                    modes_list = []
                    if modes_val & 0x8000: modes_list.append("CCL")
                    if modes_val & 0x4000: modes_list.append("TC (P-)")
                    if modes_val & 0x2000: modes_list.append("TGC (P±)")
                    if modes_val & 0x1000: modes_list.append("TC+R")
                    if modes_val & 0x0800: modes_list.append("TGC+R")
                    if modes_val & 0x0008: modes_list.append("Autonomous/External")
                    if modes_val & 0x0002: modes_list.append("Local EPS Forming (V2L/H)")
                    modes_str = ", ".join(modes_list) if modes_list else "None (Normal Charging Only)"
                    result_display.append(f"    EvPwrCtrlModesAvail: {modes_str}")
                    update_op_data("EvPwrCtrlModesAvail", modes_str)
                else:
                    result_display.append("    Not enough data bytes to interpret")


            elif frame_id == 0x16:  # SeModeCtrl (22)
                result_display.append("  Interpretation: SeModeCtrl")
                if len(databytes) >= 8:
                    # --- SeGridCodeRequest (Bytes 0-1) ---
                    raw_grid_req = (databytes[1] << 8) | databytes[0]
                    grid_req_val = (raw_grid_req >> 2) & 0x3FFF # Extract 14 bits

                    grid_req_map = {
                        0x0001: "Request basic V2G settings A",
                        0x0002: "Request basic V2X settings B",
                        0x0003: "Request UL 1741-SA defaults",
                        0x0004: "Request IEEE 1547-2018/UL 1741-SB defaults",
                        0x7FFE: "Error",
                        0x7FFF: "No request, follow SunSpec"
                    }
                    grid_req_str = grid_req_map.get(grid_req_val, f"Manufacturer-defined ({grid_req_val:04X})")
                    result_display.append(f"    SeGridCodeRequest: {grid_req_str}")
                    update_op_data("SeGridCodeRequest", grid_req_str)

                    # --- SeInverterRequest (Byte 2) ---
                    inverter_req_val = databytes[2] & 0x0F
                    inverter_req_map = {
                        0: "Disconnected/Off", 1: "Deep Sleep Offline",
                        2: "Deep Sleep Online", 3: "Light/Transparent Sleep",
                        4: "Active/On", 0x0F: "No Request"
                    }
                    inverter_req_str = inverter_req_map.get(inverter_req_val, "Reserved")
                    result_display.append(f"    SeInverterRequest: {inverter_req_str}")
                    update_op_data("SeInverterRequest", inverter_req_str)

                    # --- SePwrCtrlMode (Byte 3) ---
                    mode_val = databytes[3]
                    mode_map = {
                        0xFF: "Normal Charging", 0xB4: "CCL", 0xA3: "TC (P-)",
                        0x9A: "TGC (P±)", 0x8D: "TC+R (II & III)", 0x72: "TGC+R (I, II, III, & IV)",
                        0x39: "Autonomous/External Control", 0x17: "Local EPS Forming (V2L/H)",
                        0x00: "Processing", 0xE8: "RESERVED", 0xD1: "RESERVED", 0xC6: "RESERVED",
                        0x65: "RESERVED", 0x5C: "RESERVED", 0x2E: "RESERVED"
                    }
                    mode_str = mode_map.get(mode_val, "Invalid")
                    result_display.append(f"    SePwrCtrlMode: {mode_str}")
                    update_op_data("SePwrCtrlMode", mode_str)

                    # --- SePwrCtrlUnits & SePwrCtrlAuth (Byte 4) ---
                    units_val = databytes[4] & 0x0F
                    auth_val = (databytes[4] >> 4) & 0x0F

                    units_map = {
                        0: "% Max Watt", 1: "Current per phase", 2: "Total Watt",
                        8: "% Max Watt + % Max VAR", 9: "Current per phase + power factor",
                        10: "Current per phase + phase angle", 11: "Total Watt + Total VAR",
                        15: "N/A"
                    }
                    units_str = units_map.get(units_val, "Reserved")
                    result_display.append(f"    SePwrCtrlUnits: {units_str}")
                    update_op_data("SePwrCtrlUnits", units_str)

                    auth_map = {
                        0: "Processing", 5: "Authorization to Discharge",
                        10: "Authorization to Form Local EPS", 15: "No authorization",
                        6: "RESERVED", 9: "RESERVED"
                    }
                    auth_str = auth_map.get(auth_val, "Invalid")
                    result_display.append(f"    SePwrCtrlAuth: {auth_str}")
                    update_op_data("SePwrCtrlAuth", auth_str)

                    # --- SeTimeStamp (Byte 7) ---
                    timestamp_val = databytes[7]
                    timestamp_str = "N/A" if timestamp_val == 0xFF else f"{timestamp_val} (Time base determined by SE)"
                    result_display.append(f"    SeTimeStamp: {timestamp_str}")
                    update_op_data("SeTimeStamp", timestamp_str)

                else:
                    result_display.append("    Not enough data bytes to interpret")

#-------------------------- J3072 Code Gen -----------------------------------------------------
            elif frame_id == 0x17:  # EvJ3072 (23)
                result_display.append("  Interpretation: EvJ3072")
                page = databytes[0]
                update_op_data("EvJ3072Page", str(page))

                if page == 0:  # Control Page
                    result_display.append(f"    EvJ3072 Control Page: {page}")
                    if len(databytes) >= 6:
                        status_str = format_j3072_status(databytes[1], "EV")
                        crc_status_str = format_j3072_crc_status(databytes[5], "EV")

                        update_op_data("EvJ3072Status", status_str)
                        update_op_data("EvNumJ3072Pages", str(databytes[2]))
                        update_op_data("EvFirstJ3072Page", str(databytes[3]))
                        update_op_data("EvLastJ3072Page", str(databytes[4]))
                        update_op_data("EvJ3072CrcStatus", crc_status_str)

                elif page == 1:
                    EvPwrCtrlModesSpt = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvPwrCtrlModesSpt Page: 1")
                    if EvPwrCtrlModesSpt >= 0xFF00:
                        update_op_data("EvPwrCtrlModesSpt", f"N/A")
                    elif EvPwrCtrlModesSpt >= 0xFF00:
                        update_op_data("EvPwrCtrlModesSpt", f"Error")
                    elif EvPwrCtrlModesSpt >= 0xFB00:
                        update_op_data("EvPwrCtrlModesSpt", f"Reserved 0x{EvPwrCtrlModesSpt:02X}")
                    else:
                        update_op_data("EvPwrCtrlModesSpt", f"0x{(EvPwrCtrlModesSpt):02X} ")

                    EvSupGridCode1 = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    EvSupGridCode1 Page: 1")
                    if EvSupGridCode1 >= 0xFF00:
                        update_op_data("EvSupGridCode1", f"N/A")
                    elif EvSupGridCode1 >= 0xFF00:
                        update_op_data("EvSupGridCode1", f"Error")
                    elif EvSupGridCode1 >= 0xFB00:
                        update_op_data("EvSupGridCode1", f"Reserved 0x{EvSupGridCode1:02X}")
                    else:
                        update_op_data("EvSupGridCode1", f"0x{(EvSupGridCode1):02X} ")

                    EvSupGridCode2 = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    EvSupGridCode2 Page: 1")
                    if EvSupGridCode2 >= 0xFF00:
                        update_op_data("EvSupGridCode2", f"N/A")
                    elif EvSupGridCode2 >= 0xFF00:
                        update_op_data("EvSupGridCode2", f"Error")
                    elif EvSupGridCode2 >= 0xFB00:
                        update_op_data("EvSupGridCode2", f"Reserved 0x{EvSupGridCode2:02X}")
                    else:
                        update_op_data("EvSupGridCode2", f"0x{(EvSupGridCode2):02X} ")

                elif page == 2:
                    EvSupGridCode3 = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvSupGridCode3 Page: 2")
                    if EvSupGridCode3 >= 0xFF00:
                        update_op_data("EvSupGridCode3", f"N/A")
                    elif EvSupGridCode3 >= 0xFF00:
                        update_op_data("EvSupGridCode3", f"Error")
                    elif EvSupGridCode3 >= 0xFB00:
                        update_op_data("EvSupGridCode3", f"Reserved 0x{EvSupGridCode3:02X}")
                    else:
                        update_op_data("EvSupGridCode3", f"0x{(EvSupGridCode3):02X} ")

                    EvSupGridCode4 = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    EvSupGridCode4 Page: 2")
                    if EvSupGridCode4 >= 0xFF00:
                        update_op_data("EvSupGridCode4", f"N/A")
                    elif EvSupGridCode4 >= 0xFF00:
                        update_op_data("EvSupGridCode4", f"Error")
                    elif EvSupGridCode4 >= 0xFB00:
                        update_op_data("EvSupGridCode4", f"Reserved 0x{EvSupGridCode4:02X}")
                    else:
                        update_op_data("EvSupGridCode4", f"0x{(EvSupGridCode4):02X} ")

                    EvSupGridCode5 = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    EvSupGridCode5 Page: 2")
                    if EvSupGridCode5 >= 0xFF00:
                        update_op_data("EvSupGridCode5", f"N/A")
                    elif EvSupGridCode5 >= 0xFF00:
                        update_op_data("EvSupGridCode5", f"Error")
                    elif EvSupGridCode5 >= 0xFB00:
                        update_op_data("EvSupGridCode5", f"Reserved 0x{EvSupGridCode5:02X}")
                    else:
                        update_op_data("EvSupGridCode5", f"0x{(EvSupGridCode5):02X} ")

                elif page == 3:
                    EvSupGridCode6 = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvSupGridCode6 Page: 3")
                    if EvSupGridCode6 >= 0xFF00:
                        update_op_data("EvSupGridCode6", f"N/A")
                    elif EvSupGridCode6 >= 0xFF00:
                        update_op_data("EvSupGridCode6", f"Error")
                    elif EvSupGridCode6 >= 0xFB00:
                        update_op_data("EvSupGridCode6", f"Reserved 0x{EvSupGridCode6:02X}")
                    else:
                        update_op_data("EvSupGridCode6", f"0x{(EvSupGridCode6):02X} ")

                    EvSupGridCode7 = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    EvSupGridCode7 Page: 3")
                    if EvSupGridCode7 >= 0xFF00:
                        update_op_data("EvSupGridCode7", f"N/A")
                    elif EvSupGridCode7 >= 0xFF00:
                        update_op_data("EvSupGridCode7", f"Error")
                    elif EvSupGridCode7 >= 0xFB00:
                        update_op_data("EvSupGridCode7", f"Reserved 0x{EvSupGridCode7:02X}")
                    else:
                        update_op_data("EvSupGridCode7", f"0x{(EvSupGridCode7):02X} ")

                    EvSupGridCode8 = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    EvSupGridCode8 Page: 3")
                    if EvSupGridCode8 >= 0xFF00:
                        update_op_data("EvSupGridCode8", f"N/A")
                    elif EvSupGridCode8 >= 0xFF00:
                        update_op_data("EvSupGridCode8", f"Error")
                    elif EvSupGridCode8 >= 0xFB00:
                        update_op_data("EvSupGridCode8", f"Reserved 0x{EvSupGridCode8:02X}")
                    else:
                        update_op_data("EvSupGridCode8", f"0x{(EvSupGridCode8):02X} ")

                elif page == 4:
                    EvSupGridCode9 = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvSupGridCode9 Page: 4")
                    if EvSupGridCode9 >= 0xFF00:
                        update_op_data("EvSupGridCode9", f"N/A")
                    elif EvSupGridCode9 >= 0xFF00:
                        update_op_data("EvSupGridCode9", f"Error")
                    elif EvSupGridCode9 >= 0xFB00:
                        update_op_data("EvSupGridCode9", f"Reserved 0x{EvSupGridCode9:02X}")
                    else:
                        update_op_data("EvSupGridCode9", f"0x{(EvSupGridCode9):02X} ")

                    EvSupGridCode10 = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    EvSupGridCode10 Page: 4")
                    if EvSupGridCode10 >= 0xFF00:
                        update_op_data("EvSupGridCode10", f"N/A")
                    elif EvSupGridCode10 >= 0xFF00:
                        update_op_data("EvSupGridCode10", f"Error")
                    elif EvSupGridCode10 >= 0xFB00:
                        update_op_data("EvSupGridCode10", f"Reserved 0x{EvSupGridCode10:02X}")
                    else:
                        update_op_data("EvSupGridCode10", f"0x{(EvSupGridCode10):02X} ")

                    EvSupGridCode11 = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    EvSupGridCode11 Page: 4")
                    if EvSupGridCode11 >= 0xFF00:
                        update_op_data("EvSupGridCode11", f"N/A")
                    elif EvSupGridCode11 >= 0xFF00:
                        update_op_data("EvSupGridCode11", f"Error")
                    elif EvSupGridCode11 >= 0xFB00:
                        update_op_data("EvSupGridCode11", f"Reserved 0x{EvSupGridCode11:02X}")
                    else:
                        update_op_data("EvSupGridCode11", f"0x{(EvSupGridCode11):02X} ")

                    EvRemGridCode = (databytes[7])
                    result_display.append(f"    EvRemGridCode Page: 4")
                    if EvRemGridCode >= 0xFF:
                        update_op_data("EvRemGridCode", f"N/A")
                    elif EvRemGridCode >= 0xFF:
                        update_op_data("EvRemGridCode", f"Error")
                    elif EvRemGridCode >= 0xFB:
                        update_op_data("EvRemGridCode", f"Reserved 0x{EvRemGridCode:02X}")
                    else:
                        update_op_data("EvRemGridCode", f"{(EvRemGridCode)} count")

                elif page == 5:
                    EvVRefL1N = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvVRefL1N Page: 5")
                    if EvVRefL1N >= 0xFF00:
                        update_op_data("EvVRefL1N", f"N/A")
                    elif EvVRefL1N >= 0xFF00:
                        update_op_data("EvVRefL1N", f"Error")
                    elif EvVRefL1N >= 0xFB00:
                        update_op_data("EvVRefL1N", f"Reserved 0x{EvVRefL1N:02X}")
                    else:
                        update_op_data("EvVRefL1N", f"{(EvVRefL1N * 0.050000):.3f} Volts")

                    EvVRefLL = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    EvVRefLL Page: 5")
                    if EvVRefLL >= 0xFF00:
                        update_op_data("EvVRefLL", f"N/A")
                    elif EvVRefLL >= 0xFF00:
                        update_op_data("EvVRefLL", f"Error")
                    elif EvVRefLL >= 0xFB00:
                        update_op_data("EvVRefLL", f"Reserved 0x{EvVRefLL:02X}")
                    else:
                        update_op_data("EvVRefLL", f"{(EvVRefLL * 0.050000):.3f} Volts")

                elif page == 6:
                    EvWMaxRtg = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvWMaxRtg Page: 6")
                    if EvWMaxRtg >= 0xFF00:
                        update_op_data("EvWMaxRtg", f"N/A")
                    elif EvWMaxRtg >= 0xFF00:
                        update_op_data("EvWMaxRtg", f"Error")
                    elif EvWMaxRtg >= 0xFB00:
                        update_op_data("EvWMaxRtg", f"Reserved 0x{EvWMaxRtg:02X}")
                    else:
                        update_op_data("EvWMaxRtg", f"{(EvWMaxRtg * 16) - 500000} W")

                    EvVAMaxRtg = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    EvVAMaxRtg Page: 6")
                    if EvVAMaxRtg >= 0xFF00:
                        update_op_data("EvVAMaxRtg", f"N/A")
                    elif EvVAMaxRtg >= 0xFF00:
                        update_op_data("EvVAMaxRtg", f"Error")
                    elif EvVAMaxRtg >= 0xFB00:
                        update_op_data("EvVAMaxRtg", f"Reserved 0x{EvVAMaxRtg:02X}")
                    else:
                        update_op_data("EvVAMaxRtg", f"{(EvVAMaxRtg * 16) - 500000} VA")

                    EvIvarMaxRtg = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    EvIvarMaxRtg Page: 6")
                    if EvIvarMaxRtg >= 0xFF00:
                        update_op_data("EvIvarMaxRtg", f"N/A")
                    elif EvIvarMaxRtg >= 0xFF00:
                        update_op_data("EvIvarMaxRtg", f"Error")
                    elif EvIvarMaxRtg >= 0xFB00:
                        update_op_data("EvIvarMaxRtg", f"Reserved 0x{EvIvarMaxRtg:02X}")
                    else:
                        update_op_data("EvIvarMaxRtg", f"{(EvIvarMaxRtg * 16) - 500000} VA")

                elif page == 7:
                    EvAvarMaxRtg = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    EvAvarMaxRtg Page: 7")
                    if EvAvarMaxRtg >= 0xFF00:
                        update_op_data("EvAvarMaxRtg", f"N/A")
                    elif EvAvarMaxRtg >= 0xFF00:
                        update_op_data("EvAvarMaxRtg", f"Error")
                    elif EvAvarMaxRtg >= 0xFB00:
                        update_op_data("EvAvarMaxRtg", f"Reserved 0x{EvAvarMaxRtg:02X}")
                    else:
                        update_op_data("EvAvarMaxRtg", f"{(EvAvarMaxRtg * 16) - 500000} VA")

                    EvChaWMaxRtg = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    EvChaWMaxRtg Page: 7")
                    if EvChaWMaxRtg >= 0xFF00:
                        update_op_data("EvChaWMaxRtg", f"N/A")
                    elif EvChaWMaxRtg >= 0xFF00:
                        update_op_data("EvChaWMaxRtg", f"Error")
                    elif EvChaWMaxRtg >= 0xFB00:
                        update_op_data("EvChaWMaxRtg", f"Reserved 0x{EvChaWMaxRtg:02X}")
                    else:
                        update_op_data("EvChaWMaxRtg", f"{(EvChaWMaxRtg * 16) - 500000} W")

                    EvChaVAMaxRtg = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    EvChaVAMaxRtg Page: 7")
                    if EvChaVAMaxRtg >= 0xFF00:
                        update_op_data("EvChaVAMaxRtg", f"N/A")
                    elif EvChaVAMaxRtg >= 0xFF00:
                        update_op_data("EvChaVAMaxRtg", f"Error")
                    elif EvChaVAMaxRtg >= 0xFB00:
                        update_op_data("EvChaVAMaxRtg", f"Reserved 0x{EvChaVAMaxRtg:02X}")
                    else:
                        update_op_data("EvChaVAMaxRtg", f"{(EvChaVAMaxRtg * 16) - 500000} VA")

                elif page == 8:
                    result_display.append(f"    EvInverterSMN Page: {page} (Buffering Data)")
                    process_stage(evJ3072_buffer, "EvInverterSMN", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 32)

                elif page == 9:
                    result_display.append(f"    EvInverterSMN Page: {page} (Buffering Data)")
                    process_stage(evJ3072_buffer, "EvInverterSMN", string_position = 7,  data_bytes = databytes[1:8], field_total_length = 32)

                elif page == 10:
                    result_display.append(f"    EvInverterSMN Page: {page} (Buffering Data)")
                    process_stage(evJ3072_buffer, "EvInverterSMN", string_position = 14,  data_bytes = databytes[1:8], field_total_length = 32)

                elif page == 11:
                    result_display.append(f"    EvInverterSMN Page: {page} (Buffering Data)")
                    process_stage(evJ3072_buffer, "EvInverterSMN", string_position = 21,  data_bytes = databytes[1:8], field_total_length = 32)

                elif page == 12:
                    result_display.append(f"    EvInverterSMN Page: {page} (Buffering Data)")
                    process_stage(evJ3072_buffer, "EvInverterSMN", string_position = 28,  data_bytes = databytes[1:5], field_total_length = 32)

                elif page == 13:
                    result_display.append(f"    EvCertificationDate Page: {page} (Buffering Data)")
                    process_stage(evJ3072_buffer, "EvCertificationDate", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 7)

                elif page == 14:
                    result_display.append(f"    EvUpdateTime Page: {page} (Buffering Data)")
                    process_stage(evJ3072_buffer, "EvUpdateTime", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 7)


            elif frame_id == 0x18:  # SeJ3072 (24)
                result_display.append("  Interpretation: SeJ3072")
                page = databytes[0]
                update_op_data("SeJ3072Page", str(page))

                if page == 0:  # Control Page
                    result_display.append(f"    SeJ3072 Control Page: {page}")
                    if len(databytes) >= 6:
                        status_str = format_j3072_status(databytes[1], "SE")
                        crc_status_str = format_j3072_crc_status(databytes[5], "SE")

                        update_op_data("SeJ3072Status", status_str)
                        update_op_data("SeNumJ3072Pages", str(databytes[2]))
                        update_op_data("SeFirstJ3072Page", str(databytes[3]))
                        update_op_data("SeLastJ3072Page", str(databytes[4]))
                        update_op_data("SeJ3072CrcStatus", crc_status_str)

                elif page == 1:
                    SePwrCtrlModesSpt = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    SePwrCtrlModesSpt Page: 1")
                    if SePwrCtrlModesSpt >= 0xFF00:
                        update_op_data("SePwrCtrlModesSpt", f"N/A")
                    elif SePwrCtrlModesSpt >= 0xFF00:
                        update_op_data("SePwrCtrlModesSpt", f"Error")
                    elif SePwrCtrlModesSpt >= 0xFB00:
                        update_op_data("SePwrCtrlModesSpt", f"Reserved 0x{SePwrCtrlModesSpt:02X}")
                    else:
                        update_op_data("SePwrCtrlModesSpt", f"0x{(SePwrCtrlModesSpt):02X} ")

                    SeWMaxEVSE = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    SeWMaxEVSE Page: 1")
                    if SeWMaxEVSE >= 0xFF00:
                        update_op_data("SeWMaxEVSE", f"N/A")
                    elif SeWMaxEVSE >= 0xFF00:
                        update_op_data("SeWMaxEVSE", f"Error")
                    elif SeWMaxEVSE >= 0xFB00:
                        update_op_data("SeWMaxEVSE", f"Reserved 0x{SeWMaxEVSE:02X}")
                    else:
                        update_op_data("SeWMaxEVSE", f"{(SeWMaxEVSE * 16) - 500000} W")

                    SeChaWMaxEVSE = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    SeChaWMaxEVSE Page: 1")
                    if SeChaWMaxEVSE >= 0xFF00:
                        update_op_data("SeChaWMaxEVSE", f"N/A")
                    elif SeChaWMaxEVSE >= 0xFF00:
                        update_op_data("SeChaWMaxEVSE", f"Error")
                    elif SeChaWMaxEVSE >= 0xFB00:
                        update_op_data("SeChaWMaxEVSE", f"Reserved 0x{SeChaWMaxEVSE:02X}")
                    else:
                        update_op_data("SeChaWMaxEVSE", f"{(SeChaWMaxEVSE * 16) - 500000} W")

                elif page == 2:
                    SeIvarMaxEVSE = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    SeIvarMaxEVSE Page: 2")
                    if SeIvarMaxEVSE >= 0xFF00:
                        update_op_data("SeIvarMaxEVSE", f"N/A")
                    elif SeIvarMaxEVSE >= 0xFF00:
                        update_op_data("SeIvarMaxEVSE", f"Error")
                    elif SeIvarMaxEVSE >= 0xFB00:
                        update_op_data("SeIvarMaxEVSE", f"Reserved 0x{SeIvarMaxEVSE:02X}")
                    else:
                        update_op_data("SeIvarMaxEVSE", f"{(SeIvarMaxEVSE * 16) - 500000} VA")

                    SeAvarMaxEVSE = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    SeAvarMaxEVSE Page: 2")
                    if SeAvarMaxEVSE >= 0xFF00:
                        update_op_data("SeAvarMaxEVSE", f"N/A")
                    elif SeAvarMaxEVSE >= 0xFF00:
                        update_op_data("SeAvarMaxEVSE", f"Error")
                    elif SeAvarMaxEVSE >= 0xFB00:
                        update_op_data("SeAvarMaxEVSE", f"Reserved 0x{SeAvarMaxEVSE:02X}")
                    else:
                        update_op_data("SeAvarMaxEVSE", f"{(SeAvarMaxEVSE * 16) - 500000} VA")

                elif page == 3:
                    result_display.append(f"    SeUpdateTimeEVSE Page: {page} (Buffering Data)")
                    process_stage(seJ3072_buffer, "SeUpdateTimeEVSE", string_position = 0,  data_bytes = databytes[1:8], field_total_length = 7)

                elif page == 4:
                    SeFreqOver1FreqA = (databytes[1])
                    result_display.append(f"    SeFreqOver1FreqA Page: 4")
                    if SeFreqOver1FreqA >= 0xFF:
                        update_op_data("SeFreqOver1FreqA", f"N/A")
                    elif SeFreqOver1FreqA >= 0xFF:
                        update_op_data("SeFreqOver1FreqA", f"Error")
                    elif SeFreqOver1FreqA >= 0xFB:
                        update_op_data("SeFreqOver1FreqA", f"Reserved 0x{SeFreqOver1FreqA:02X}")
                    else:
                        update_op_data("SeFreqOver1FreqA", f"{(SeFreqOver1FreqA * 0.100000) - -42.500000:.3f} Hz")

                    SeFreqOver1TimeA = (databytes[3] << 8) | (databytes[2])
                    result_display.append(f"    SeFreqOver1TimeA Page: 4")
                    if SeFreqOver1TimeA >= 0xFF00:
                        update_op_data("SeFreqOver1TimeA", f"N/A")
                    elif SeFreqOver1TimeA >= 0xFF00:
                        update_op_data("SeFreqOver1TimeA", f"Error")
                    elif SeFreqOver1TimeA >= 0xFB00:
                        update_op_data("SeFreqOver1TimeA", f"Reserved 0x{SeFreqOver1TimeA:02X}")
                    else:
                        update_op_data("SeFreqOver1TimeA", f"{(SeFreqOver1TimeA * 0.010000):.3f} seconds")

                    SeFreqOver2FreqA = (databytes[4])
                    result_display.append(f"    SeFreqOver2FreqA Page: 4")
                    if SeFreqOver2FreqA >= 0xFF:
                        update_op_data("SeFreqOver2FreqA", f"N/A")
                    elif SeFreqOver2FreqA >= 0xFF:
                        update_op_data("SeFreqOver2FreqA", f"Error")
                    elif SeFreqOver2FreqA >= 0xFB:
                        update_op_data("SeFreqOver2FreqA", f"Reserved 0x{SeFreqOver2FreqA:02X}")
                    else:
                        update_op_data("SeFreqOver2FreqA", f"{(SeFreqOver2FreqA * 0.100000) - -42.500000:.3f} Hz")

                    SeFreqOver2TimeA = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    SeFreqOver2TimeA Page: 4")
                    if SeFreqOver2TimeA >= 0xFF00:
                        update_op_data("SeFreqOver2TimeA", f"N/A")
                    elif SeFreqOver2TimeA >= 0xFF00:
                        update_op_data("SeFreqOver2TimeA", f"Error")
                    elif SeFreqOver2TimeA >= 0xFB00:
                        update_op_data("SeFreqOver2TimeA", f"Reserved 0x{SeFreqOver2TimeA:02X}")
                    else:
                        update_op_data("SeFreqOver2TimeA", f"{(SeFreqOver2TimeA * 0.010000):.3f} seconds")

                elif page == 5:
                    SeFreqUnder1FreqA = (databytes[1])
                    result_display.append(f"    SeFreqUnder1FreqA Page: 5")
                    if SeFreqUnder1FreqA >= 0xFF:
                        update_op_data("SeFreqUnder1FreqA", f"N/A")
                    elif SeFreqUnder1FreqA >= 0xFF:
                        update_op_data("SeFreqUnder1FreqA", f"Error")
                    elif SeFreqUnder1FreqA >= 0xFB:
                        update_op_data("SeFreqUnder1FreqA", f"Reserved 0x{SeFreqUnder1FreqA:02X}")
                    else:
                        update_op_data("SeFreqUnder1FreqA", f"{(SeFreqUnder1FreqA * 0.100000) - -42.500000:.3f} Hz")

                    SeFreqUnder1TimeA = (databytes[3] << 8) | (databytes[2])
                    result_display.append(f"    SeFreqUnder1TimeA Page: 5")
                    if SeFreqUnder1TimeA >= 0xFF00:
                        update_op_data("SeFreqUnder1TimeA", f"N/A")
                    elif SeFreqUnder1TimeA >= 0xFF00:
                        update_op_data("SeFreqUnder1TimeA", f"Error")
                    elif SeFreqUnder1TimeA >= 0xFB00:
                        update_op_data("SeFreqUnder1TimeA", f"Reserved 0x{SeFreqUnder1TimeA:02X}")
                    else:
                        update_op_data("SeFreqUnder1TimeA", f"{(SeFreqUnder1TimeA * 0.010000):.3f} seconds")

                    SeFreqUnder2FreqA = (databytes[4])
                    result_display.append(f"    SeFreqUnder2FreqA Page: 5")
                    if SeFreqUnder2FreqA >= 0xFF:
                        update_op_data("SeFreqUnder2FreqA", f"N/A")
                    elif SeFreqUnder2FreqA >= 0xFF:
                        update_op_data("SeFreqUnder2FreqA", f"Error")
                    elif SeFreqUnder2FreqA >= 0xFB:
                        update_op_data("SeFreqUnder2FreqA", f"Reserved 0x{SeFreqUnder2FreqA:02X}")
                    else:
                        update_op_data("SeFreqUnder2FreqA", f"{(SeFreqUnder2FreqA * 0.100000) - -42.500000:.3f} Hz")

                    SeFreqUnder2TimeA = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    SeFreqUnder2TimeA Page: 5")
                    if SeFreqUnder2TimeA >= 0xFF00:
                        update_op_data("SeFreqUnder2TimeA", f"N/A")
                    elif SeFreqUnder2TimeA >= 0xFF00:
                        update_op_data("SeFreqUnder2TimeA", f"Error")
                    elif SeFreqUnder2TimeA >= 0xFB00:
                        update_op_data("SeFreqUnder2TimeA", f"Reserved 0x{SeFreqUnder2TimeA:02X}")
                    else:
                        update_op_data("SeFreqUnder2TimeA", f"{(SeFreqUnder2TimeA * 0.010000):.3f} seconds")

                elif page == 6:
                    SeLV3hLV2lLNA = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    SeLV3hLV2lLNA Page: 6")
                    if SeLV3hLV2lLNA >= 0xFF00:
                        update_op_data("SeLV3hLV2lLNA", f"N/A")
                    elif SeLV3hLV2lLNA >= 0xFF00:
                        update_op_data("SeLV3hLV2lLNA", f"Error")
                    elif SeLV3hLV2lLNA >= 0xFB00:
                        update_op_data("SeLV3hLV2lLNA", f"Reserved 0x{SeLV3hLV2lLNA:02X}")
                    else:
                        update_op_data("SeLV3hLV2lLNA", f"{(SeLV3hLV2lLNA * 0.050000):.3f} Volts")

                    SeLV3TimeA = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    SeLV3TimeA Page: 6")
                    if SeLV3TimeA >= 0xFF00:
                        update_op_data("SeLV3TimeA", f"N/A")
                    elif SeLV3TimeA >= 0xFF00:
                        update_op_data("SeLV3TimeA", f"Error")
                    elif SeLV3TimeA >= 0xFB00:
                        update_op_data("SeLV3TimeA", f"Reserved 0x{SeLV3TimeA:02X}")
                    else:
                        update_op_data("SeLV3TimeA", f"{(SeLV3TimeA * 0.010000):.3f} seconds")

                    SeLV2hLV1lLNA = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    SeLV2hLV1lLNA Page: 6")
                    if SeLV2hLV1lLNA >= 0xFF00:
                        update_op_data("SeLV2hLV1lLNA", f"N/A")
                    elif SeLV2hLV1lLNA >= 0xFF00:
                        update_op_data("SeLV2hLV1lLNA", f"Error")
                    elif SeLV2hLV1lLNA >= 0xFB00:
                        update_op_data("SeLV2hLV1lLNA", f"Reserved 0x{SeLV2hLV1lLNA:02X}")
                    else:
                        update_op_data("SeLV2hLV1lLNA", f"{(SeLV2hLV1lLNA * 0.050000):.3f} Volts")

                elif page == 7:
                    SeLV2TimeA = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    SeLV2TimeA Page: 7")
                    if SeLV2TimeA >= 0xFF00:
                        update_op_data("SeLV2TimeA", f"N/A")
                    elif SeLV2TimeA >= 0xFF00:
                        update_op_data("SeLV2TimeA", f"Error")
                    elif SeLV2TimeA >= 0xFB00:
                        update_op_data("SeLV2TimeA", f"Reserved 0x{SeLV2TimeA:02X}")
                    else:
                        update_op_data("SeLV2TimeA", f"{(SeLV2TimeA * 0.010000):.3f} seconds")

                    SeLV1hLNA = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    SeLV1hLNA Page: 7")
                    if SeLV1hLNA >= 0xFF00:
                        update_op_data("SeLV1hLNA", f"N/A")
                    elif SeLV1hLNA >= 0xFF00:
                        update_op_data("SeLV1hLNA", f"Error")
                    elif SeLV1hLNA >= 0xFB00:
                        update_op_data("SeLV1hLNA", f"Reserved 0x{SeLV1hLNA:02X}")
                    else:
                        update_op_data("SeLV1hLNA", f"{(SeLV1hLNA * 0.050000):.3f} Volts")

                    SeLV1TimeA = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    SeLV1TimeA Page: 7")
                    if SeLV1TimeA >= 0xFF00:
                        update_op_data("SeLV1TimeA", f"N/A")
                    elif SeLV1TimeA >= 0xFF00:
                        update_op_data("SeLV1TimeA", f"Error")
                    elif SeLV1TimeA >= 0xFB00:
                        update_op_data("SeLV1TimeA", f"Reserved 0x{SeLV1TimeA:02X}")
                    else:
                        update_op_data("SeLV1TimeA", f"{(SeLV1TimeA * 0.010000):.3f} seconds")

                elif page == 8:
                    SeHV1lLNA = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    SeHV1lLNA Page: 8")
                    if SeHV1lLNA >= 0xFF00:
                        update_op_data("SeHV1lLNA", f"N/A")
                    elif SeHV1lLNA >= 0xFF00:
                        update_op_data("SeHV1lLNA", f"Error")
                    elif SeHV1lLNA >= 0xFB00:
                        update_op_data("SeHV1lLNA", f"Reserved 0x{SeHV1lLNA:02X}")
                    else:
                        update_op_data("SeHV1lLNA", f"{(SeHV1lLNA * 0.050000):.3f} Volts")

                    SeHV1TimeA = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    SeHV1TimeA Page: 8")
                    if SeHV1TimeA >= 0xFF00:
                        update_op_data("SeHV1TimeA", f"N/A")
                    elif SeHV1TimeA >= 0xFF00:
                        update_op_data("SeHV1TimeA", f"Error")
                    elif SeHV1TimeA >= 0xFB00:
                        update_op_data("SeHV1TimeA", f"Reserved 0x{SeHV1TimeA:02X}")
                    else:
                        update_op_data("SeHV1TimeA", f"{(SeHV1TimeA * 0.010000):.3f} seconds")

                elif page == 9:
                    SeHV1hHV2lLNA = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    SeHV1hHV2lLNA Page: 9")
                    if SeHV1hHV2lLNA >= 0xFF00:
                        update_op_data("SeHV1hHV2lLNA", f"N/A")
                    elif SeHV1hHV2lLNA >= 0xFF00:
                        update_op_data("SeHV1hHV2lLNA", f"Error")
                    elif SeHV1hHV2lLNA >= 0xFB00:
                        update_op_data("SeHV1hHV2lLNA", f"Reserved 0x{SeHV1hHV2lLNA:02X}")
                    else:
                        update_op_data("SeHV1hHV2lLNA", f"{(SeHV1hHV2lLNA * 0.050000):.3f} Volts")

                    SeHV2TimeA = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    SeHV2TimeA Page: 9")
                    if SeHV2TimeA >= 0xFF00:
                        update_op_data("SeHV2TimeA", f"N/A")
                    elif SeHV2TimeA >= 0xFF00:
                        update_op_data("SeHV2TimeA", f"Error")
                    elif SeHV2TimeA >= 0xFB00:
                        update_op_data("SeHV2TimeA", f"Reserved 0x{SeHV2TimeA:02X}")
                    else:
                        update_op_data("SeHV2TimeA", f"{(SeHV2TimeA * 0.010000):.3f} seconds")

                elif page == 10:
                    SeFreqOver1FreqB = (databytes[1])
                    result_display.append(f"    SeFreqOver1FreqB Page: 10")
                    if SeFreqOver1FreqB >= 0xFF:
                        update_op_data("SeFreqOver1FreqB", f"N/A")
                    elif SeFreqOver1FreqB >= 0xFF:
                        update_op_data("SeFreqOver1FreqB", f"Error")
                    elif SeFreqOver1FreqB >= 0xFB:
                        update_op_data("SeFreqOver1FreqB", f"Reserved 0x{SeFreqOver1FreqB:02X}")
                    else:
                        update_op_data("SeFreqOver1FreqB", f"{(SeFreqOver1FreqB * 0.100000) - -42.500000:.3f} Hz")

                    SeFreqOver1TimeB = (databytes[3] << 8) | (databytes[2])
                    result_display.append(f"    SeFreqOver1TimeB Page: 10")
                    if SeFreqOver1TimeB >= 0xFF00:
                        update_op_data("SeFreqOver1TimeB", f"N/A")
                    elif SeFreqOver1TimeB >= 0xFF00:
                        update_op_data("SeFreqOver1TimeB", f"Error")
                    elif SeFreqOver1TimeB >= 0xFB00:
                        update_op_data("SeFreqOver1TimeB", f"Reserved 0x{SeFreqOver1TimeB:02X}")
                    else:
                        update_op_data("SeFreqOver1TimeB", f"{(SeFreqOver1TimeB * 0.010000):.3f} seconds")

                    SeFreqOver2FreqB = (databytes[4])
                    result_display.append(f"    SeFreqOver2FreqB Page: 10")
                    if SeFreqOver2FreqB >= 0xFF:
                        update_op_data("SeFreqOver2FreqB", f"N/A")
                    elif SeFreqOver2FreqB >= 0xFF:
                        update_op_data("SeFreqOver2FreqB", f"Error")
                    elif SeFreqOver2FreqB >= 0xFB:
                        update_op_data("SeFreqOver2FreqB", f"Reserved 0x{SeFreqOver2FreqB:02X}")
                    else:
                        update_op_data("SeFreqOver2FreqB", f"{(SeFreqOver2FreqB * 0.100000) - -42.500000:.3f} Hz")

                    SeFreqOver2TimeB = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    SeFreqOver2TimeB Page: 10")
                    if SeFreqOver2TimeB >= 0xFF00:
                        update_op_data("SeFreqOver2TimeB", f"N/A")
                    elif SeFreqOver2TimeB >= 0xFF00:
                        update_op_data("SeFreqOver2TimeB", f"Error")
                    elif SeFreqOver2TimeB >= 0xFB00:
                        update_op_data("SeFreqOver2TimeB", f"Reserved 0x{SeFreqOver2TimeB:02X}")
                    else:
                        update_op_data("SeFreqOver2TimeB", f"{(SeFreqOver2TimeB * 0.010000):.3f} seconds")

                elif page == 11:
                    SeFreqUnder1FreqB = (databytes[1])
                    result_display.append(f"    SeFreqUnder1FreqB Page: 11")
                    if SeFreqUnder1FreqB >= 0xFF:
                        update_op_data("SeFreqUnder1FreqB", f"N/A")
                    elif SeFreqUnder1FreqB >= 0xFF:
                        update_op_data("SeFreqUnder1FreqB", f"Error")
                    elif SeFreqUnder1FreqB >= 0xFB:
                        update_op_data("SeFreqUnder1FreqB", f"Reserved 0x{SeFreqUnder1FreqB:02X}")
                    else:
                        update_op_data("SeFreqUnder1FreqB", f"{(SeFreqUnder1FreqB * 0.100000) - -42.500000:.3f} Hz")

                    SeFreqUnder1TimeB = (databytes[3] << 8) | (databytes[2])
                    result_display.append(f"    SeFreqUnder1TimeB Page: 11")
                    if SeFreqUnder1TimeB >= 0xFF00:
                        update_op_data("SeFreqUnder1TimeB", f"N/A")
                    elif SeFreqUnder1TimeB >= 0xFF00:
                        update_op_data("SeFreqUnder1TimeB", f"Error")
                    elif SeFreqUnder1TimeB >= 0xFB00:
                        update_op_data("SeFreqUnder1TimeB", f"Reserved 0x{SeFreqUnder1TimeB:02X}")
                    else:
                        update_op_data("SeFreqUnder1TimeB", f"{(SeFreqUnder1TimeB * 0.010000):.3f} seconds")

                    SeFreqUnder2FreqB = (databytes[4])
                    result_display.append(f"    SeFreqUnder2FreqB Page: 11")
                    if SeFreqUnder2FreqB >= 0xFF:
                        update_op_data("SeFreqUnder2FreqB", f"N/A")
                    elif SeFreqUnder2FreqB >= 0xFF:
                        update_op_data("SeFreqUnder2FreqB", f"Error")
                    elif SeFreqUnder2FreqB >= 0xFB:
                        update_op_data("SeFreqUnder2FreqB", f"Reserved 0x{SeFreqUnder2FreqB:02X}")
                    else:
                        update_op_data("SeFreqUnder2FreqB", f"{(SeFreqUnder2FreqB * 0.100000) - -42.500000:.3f} Hz")

                    SeFreqUnder2TimeB = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    SeFreqUnder2TimeB Page: 11")
                    if SeFreqUnder2TimeB >= 0xFF00:
                        update_op_data("SeFreqUnder2TimeB", f"N/A")
                    elif SeFreqUnder2TimeB >= 0xFF00:
                        update_op_data("SeFreqUnder2TimeB", f"Error")
                    elif SeFreqUnder2TimeB >= 0xFB00:
                        update_op_data("SeFreqUnder2TimeB", f"Reserved 0x{SeFreqUnder2TimeB:02X}")
                    else:
                        update_op_data("SeFreqUnder2TimeB", f"{(SeFreqUnder2TimeB * 0.010000):.3f} seconds")

                elif page == 12:
                    SeLV3hLV2lLNB = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    SeLV3hLV2lLNB Page: 12")
                    if SeLV3hLV2lLNB >= 0xFF00:
                        update_op_data("SeLV3hLV2lLNB", f"N/A")
                    elif SeLV3hLV2lLNB >= 0xFF00:
                        update_op_data("SeLV3hLV2lLNB", f"Error")
                    elif SeLV3hLV2lLNB >= 0xFB00:
                        update_op_data("SeLV3hLV2lLNB", f"Reserved 0x{SeLV3hLV2lLNB:02X}")
                    else:
                        update_op_data("SeLV3hLV2lLNB", f"{(SeLV3hLV2lLNB * 0.050000):.3f} Volts")

                    SeLV3TimeB = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    SeLV3TimeB Page: 12")
                    if SeLV3TimeB >= 0xFF00:
                        update_op_data("SeLV3TimeB", f"N/A")
                    elif SeLV3TimeB >= 0xFF00:
                        update_op_data("SeLV3TimeB", f"Error")
                    elif SeLV3TimeB >= 0xFB00:
                        update_op_data("SeLV3TimeB", f"Reserved 0x{SeLV3TimeB:02X}")
                    else:
                        update_op_data("SeLV3TimeB", f"{(SeLV3TimeB * 0.010000):.3f} seconds")

                    SeLV2hLV1lLNB = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    SeLV2hLV1lLNB Page: 12")
                    if SeLV2hLV1lLNB >= 0xFF00:
                        update_op_data("SeLV2hLV1lLNB", f"N/A")
                    elif SeLV2hLV1lLNB >= 0xFF00:
                        update_op_data("SeLV2hLV1lLNB", f"Error")
                    elif SeLV2hLV1lLNB >= 0xFB00:
                        update_op_data("SeLV2hLV1lLNB", f"Reserved 0x{SeLV2hLV1lLNB:02X}")
                    else:
                        update_op_data("SeLV2hLV1lLNB", f"{(SeLV2hLV1lLNB * 0.050000):.3f} Volts")

                elif page == 13:
                    SeLV2TimeB = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    SeLV2TimeB Page: 13")
                    if SeLV2TimeB >= 0xFF00:
                        update_op_data("SeLV2TimeB", f"N/A")
                    elif SeLV2TimeB >= 0xFF00:
                        update_op_data("SeLV2TimeB", f"Error")
                    elif SeLV2TimeB >= 0xFB00:
                        update_op_data("SeLV2TimeB", f"Reserved 0x{SeLV2TimeB:02X}")
                    else:
                        update_op_data("SeLV2TimeB", f"{(SeLV2TimeB * 0.010000):.3f} seconds")

                    SeLV1hLNB = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    SeLV1hLNB Page: 13")
                    if SeLV1hLNB >= 0xFF00:
                        update_op_data("SeLV1hLNB", f"N/A")
                    elif SeLV1hLNB >= 0xFF00:
                        update_op_data("SeLV1hLNB", f"Error")
                    elif SeLV1hLNB >= 0xFB00:
                        update_op_data("SeLV1hLNB", f"Reserved 0x{SeLV1hLNB:02X}")
                    else:
                        update_op_data("SeLV1hLNB", f"{(SeLV1hLNB * 0.050000):.3f} Volts")

                    SeLV1TimeB = (databytes[6] << 8) | (databytes[5])
                    result_display.append(f"    SeLV1TimeB Page: 13")
                    if SeLV1TimeB >= 0xFF00:
                        update_op_data("SeLV1TimeB", f"N/A")
                    elif SeLV1TimeB >= 0xFF00:
                        update_op_data("SeLV1TimeB", f"Error")
                    elif SeLV1TimeB >= 0xFB00:
                        update_op_data("SeLV1TimeB", f"Reserved 0x{SeLV1TimeB:02X}")
                    else:
                        update_op_data("SeLV1TimeB", f"{(SeLV1TimeB * 0.010000):.3f} seconds")

                elif page == 14:
                    SeHV1lLNB = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    SeHV1lLNB Page: 14")
                    if SeHV1lLNB >= 0xFF00:
                        update_op_data("SeHV1lLNB", f"N/A")
                    elif SeHV1lLNB >= 0xFF00:
                        update_op_data("SeHV1lLNB", f"Error")
                    elif SeHV1lLNB >= 0xFB00:
                        update_op_data("SeHV1lLNB", f"Reserved 0x{SeHV1lLNB:02X}")
                    else:
                        update_op_data("SeHV1lLNB", f"{(SeHV1lLNB * 0.050000):.3f} Volts")

                    SeHV1TimeB = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    SeHV1TimeB Page: 14")
                    if SeHV1TimeB >= 0xFF00:
                        update_op_data("SeHV1TimeB", f"N/A")
                    elif SeHV1TimeB >= 0xFF00:
                        update_op_data("SeHV1TimeB", f"Error")
                    elif SeHV1TimeB >= 0xFB00:
                        update_op_data("SeHV1TimeB", f"Reserved 0x{SeHV1TimeB:02X}")
                    else:
                        update_op_data("SeHV1TimeB", f"{(SeHV1TimeB * 0.010000):.3f} seconds")

                elif page == 15:
                    SeHV1hHV2lLNB = (databytes[2] << 8) | (databytes[1])
                    result_display.append(f"    SeHV1hHV2lLNB Page: 15")
                    if SeHV1hHV2lLNB >= 0xFF00:
                        update_op_data("SeHV1hHV2lLNB", f"N/A")
                    elif SeHV1hHV2lLNB >= 0xFF00:
                        update_op_data("SeHV1hHV2lLNB", f"Error")
                    elif SeHV1hHV2lLNB >= 0xFB00:
                        update_op_data("SeHV1hHV2lLNB", f"Reserved 0x{SeHV1hHV2lLNB:02X}")
                    else:
                        update_op_data("SeHV1hHV2lLNB", f"{(SeHV1hHV2lLNB * 0.050000):.3f} Volts")

                    SeHV2TimeB = (databytes[4] << 8) | (databytes[3])
                    result_display.append(f"    SeHV2TimeB Page: 15")
                    if SeHV2TimeB >= 0xFF00:
                        update_op_data("SeHV2TimeB", f"N/A")
                    elif SeHV2TimeB >= 0xFF00:
                        update_op_data("SeHV2TimeB", f"Error")
                    elif SeHV2TimeB >= 0xFB00:
                        update_op_data("SeHV2TimeB", f"Reserved 0x{SeHV2TimeB:02X}")
                    else:
                        update_op_data("SeHV2TimeB", f"{(SeHV2TimeB * 0.010000):.3f} seconds")

# -------------------------- J3072 Code Gen end -----------------------------------------------------

            elif frame_id == 0x19:  # SeTargets1 (25)
                result_display.append("  Interpretation: SeTargets1")
                if len(databytes) >= 8:
                    element_a = (databytes[1] << 8) | databytes[0]
                    element_b = (databytes[3] << 8) | databytes[2]
                    element_c = (databytes[5] << 8) | databytes[4]
                    element_d = (databytes[7] << 8) | databytes[6]

                    update_op_data("SeTargets1ElementA", element_a)
                    update_op_data("SeTargets1ElementB", element_b)
                    update_op_data("SeTargets1ElementC", element_c)
                    update_op_data("SeTargets1ElementD", element_d)

                    update_op_data("SeTargets1_SelectedVersion", format_selected_version(databytes[0]))

                    result_display.append(f"    SeTargets1ElementA: 0x{element_a:04X}")
                    result_display.append(f"    SeTargets1ElementB: 0x{element_b:04X}")
                    result_display.append(f"    SeTargets1ElementC: 0x{element_c:04X}")
                    result_display.append(f"    SeTargets1ElementD: 0x{element_d:04X}")
                else:
                    result_display.append("    Not enough data bytes to interpret")

            result_display.append("")

            if frame_validity_map[frames_parsed]:
                snapshot_init = copy.deepcopy(current_init_data)
                init_data_timeline.append((frames_parsed, snapshot_init))
                snapshot_op = copy.deepcopy(current_op_data)
                op_data_timeline.append((frames_parsed, snapshot_op))
                snapshot_ver = copy.deepcopy(current_ver_data)
                ver_data_timeline.append((frames_parsed, snapshot_ver))

        except Exception as e:
            result_display.append(f"  Error processing frame: {e}")
            result_display.append("")
            frame_validity_map[frames_parsed] = False
        if auto_update1:
            slider.setValue(total_frames)
            update_slider_label(slider.value(), frame_validity_map, label)


# ----------------- data processing -------------------
def process_live_data(new_data, is_spaced):
    global raw_file_buffer, total_frames
    raw_file_buffer += new_data
    byte_list = parse_hex_data(raw_file_buffer, is_spaced)
    chunks, remainder = parse_data_stream(byte_list, live_data_active)

    # Count new frames to update the slider range
    num_new_frames = sum(1 for chunk_type, _ in chunks if chunk_type == 'frame')
    if num_new_frames > 0:
        total_frames += num_new_frames
        slider.setMinimum(1)
        slider.setMaximum(total_frames)

        pattern = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
        interval = pattern[-1]
        for candidate in pattern:
            if total_frames / candidate < 20:
                interval = candidate
                break

        slider.setRange(1, total_frames)
        slider.setTickInterval(interval)
        slider_label_bar.setRange(1, total_frames)
        slider_label_bar.setTickInterval(interval)

    display_frames(chunks)

    if is_spaced:
        raw_file_buffer = " ".join(remainder)
    else:
        raw_file_buffer = "".join(remainder)


def parse_file(file_content, chosen_spaced):
    global raw_file_buffer, frames_parsed, total_frames, is_spaced_format
    global current_init_data, init_data_timeline
    global current_op_data, op_data_timeline
    global current_ver_data, ver_data_timeline

    current_max = slider.maximum()
    slider.setValue(current_max)
    update_slider_label(current_max, frame_validity_map, label)
    frames_parsed = 0
    total_frames = 0
    raw_file_buffer = ""
    is_spaced_format = chosen_spaced
    current_init_data.clear()
    init_data_timeline.clear()
    current_op_data.clear()
    op_data_timeline.clear()
    current_ver_data.clear()
    ver_data_timeline.clear()
    result_display.clear()
    globals.cable_node_frames = []
    evID_buffer.clear()
    seID_buffer.clear()
    evJ3072_buffer.clear()
    seJ3072_buffer.clear()
    process_live_data(file_content, is_spaced_format)
    slider.setValue(total_frames)
    refresh_all_displays(slider.value())
    update_slider_label(slider.value(), frame_validity_map, label)
    evID_stage_bytes.clear()
    seID_stage_bytes.clear()


# ---------- Start of Button Functions -----------
def open_file_dialog():
    global live_data_active
    if live_data_active:
        result_display.append("Live data is active. Turn it off to parse a file.")
        return

    options = QFileDialog.Options()
    options |= QFileDialog.ReadOnly
    fileName, _ = QFileDialog.getOpenFileName(
        window,
        "Select File",
        "",
        "All Files (*);;Text Files (*.txt);;Binary Files (*.bin)",
        options=options
    )
    if fileName:

        window.setWindowTitle(f"LIN_GUI - {os.path.basename(fileName)}")

        result_display.clear()
        result_display.append(f"Selected file: {fileName}\n")
        try:
            with open(fileName, 'rb') as f:
                file_bytes = f.read()
        except Exception as e:
            result_display.append(f"Error reading file: {e}")
            return

        is_binary = any(b < 9 or (13 < b < 32) or b > 126 for b in file_bytes)
        if is_binary:
            result_display.append("Detected binary file. Interpreting as binary data...")
            file_content = ' '.join([f"{b:02X}" for b in file_bytes])
        else:
            try:
                file_content = file_bytes.decode('utf-8', errors='replace')
            except Exception as e:
                result_display.append(f"Error decoding file: {e}")
                return

        guessed_spaced = guess_format(file_content)
        dialog = FormatSelectionDialog(window, guessed_spaced, guessed_binary=is_binary)
        if dialog.exec_() == QDialog.Accepted:
            chosen_spaced, chosen_binary = dialog.selected_format()
            if chosen_binary:
                chosen_spaced = True

            # Show loading dialog
            loading_dialog = LoadingDialog(window)
            loading_dialog.show()
            QApplication.processEvents() # Ensure the dialog is displayed before parsing

        else:
            result_display.append("Format selection canceled. No parsing done.")
            return

        result_display.clear()
        parse_file(file_content, chosen_spaced)

        # Close loading dialog after parsing is done
        loading_dialog.close()


def toggle_live_data():
    global live_data_active, is_spaced_format, ser, auto_update1, LAST_N_FRAMES
    live_data_active = live_data_button.isChecked()

    if live_data_active:
        # --- Live data is being TURNED ON ---
        live_data_button.setIcon(QIcon(resource_path(r"images/toggle-on.png")))
        auto_update1 = True
        file_button.setEnabled(False)
        reset_time_button.setEnabled(False)

        port_dialog = SerialPortSelectionDialog(window)
        if port_dialog.exec_() == QDialog.Accepted:
            selected_port = port_dialog.selected_port()
            buffer_frames = port_dialog.selected_buffer_frames()

            settings = QSettings("MyCompany", "MyApp")
            settings.setValue("lastSerialPort", selected_port)

            LAST_N_FRAMES = int(buffer_frames)
            globals.frame_timestamps.clear()

            result_display.append(
                f"Live data mode activated. Will read binary from {selected_port} with LAST_N_FRAMES = {LAST_N_FRAMES}."
            )
            try:
                # --- SUCCESSFUL start ---
                ser = serial.Serial(selected_port, 19200, timeout=0.1)

                window.setWindowTitle("LIN_GUI - Live Data Mode")

                try:
                    timer.timeout.disconnect(read_from_serial)
                except TypeError:
                    pass
                timer.timeout.connect(read_from_serial)
                timer.start(100)
                # start timer when live data enabled [will reset the timer to 0]
                globals.live_data_start_time = time.time()

                # Enable buttons now that we have a connection
                save_log_button.setEnabled(True)
                frame_time_toggle_button.setEnabled(True)
                reset_time_button.setEnabled(True)
                frame_time_toggle_button.setChecked(True)
                frame_time_toggle()

            except Exception as e:
                # --- FAILED to turn on live data ---
                result_display.append(f"Error opening {selected_port}: {e}")
                live_data_button.setChecked(False)
                live_data_active = False
                live_data_button.setIcon(QIcon(resource_path(r"images/toggle-off.png")))
                frame_time_toggle_button.setEnabled(True)
                file_button.setEnabled(True)

                reset_time_button.setEnabled(False)
        else:
            # --- User CANCELLED turning on live data ---
            result_display.append("Serial port selection canceled.")
            live_data_button.setChecked(False)
            live_data_active = False
            live_data_button.setIcon(QIcon(resource_path(r"images/toggle-off.png")))
            frame_time_toggle_button.setEnabled(True)
            file_button.setEnabled(True)

            reset_time_button.setEnabled(False)
    else:
        window.setWindowTitle("LIN_GUI")

        # --- Live data is being TURNED OFF by the user ---
        live_data_button.setIcon(QIcon(resource_path(r"images/toggle-off.png")))
        result_display.append("Live data mode deactivated.")
        timer.stop()
        if ser and ser.is_open:
            ser.close()

        # Disable related buttons and reset states
        frame_time_toggle_button.setEnabled(True)
        reset_time_button.setEnabled(False)

        frame_time_toggle()
        file_button.setEnabled(True)



def frame_time_toggle():
    # This function now controls the global display mode for frames vs. timing
    globals.frame_time_active = frame_time_toggle_button.isChecked()

    if globals.frame_time_active:
        frame_time_toggle_button.setIcon(QIcon(resource_path(r"images/frame-time-toggle-on.png")))
    else:
        frame_time_toggle_button.setIcon(QIcon(resource_path(r"images/frame-time-toggle-off.png")))

    # Refresh all displays
    refresh_all_displays(slider.value())


def open_clear_data_dialog():
    dialog = QDialog(window)
    dialog.setWindowTitle("Confirm Clear Data")
    layout = QVBoxLayout()
    message = QLabel("Are you sure you would like to clear all of the data?")
    message.setAlignment(Qt.AlignCenter)
    layout.addWidget(message)

    button_box = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
    layout.addWidget(button_box)

    button_box.accepted.connect(lambda: clear_all_data(dialog))
    button_box.rejected.connect(dialog.reject)

    dialog.setStyleSheet("QLabel, QPushButton { font-size: 8pt; }")

    dialog.setLayout(layout)
    dialog.exec_()


# Define a list of all display widgets
display_widgets = [
    result_display,
    task_operation_display,
    contactor_state_display,
    selected_protocol_version_display,
    sesupported_protocol_versions_display,
    ratings_display,
    seavailable_current_display,
    evpresent_current_display,
    evrequested_current_display,
    EvInfo_display,
    SeInfo_display,
    cable_Node_display,
    sleep_connection_display,
    control_page_display,
    OP252_control_page_display,
    EvModeCtrl_display,
    SeModeCtrl_display,
    SeTargets1_display,
    op3_evid_display,
    op3_seid_display,
    EvJ3072_tab_display,
    SeJ3072_tab_display,
    ev_data_tab_display,
    se_data_tab_display
]


def clear_all_data(dialog):

    window.setWindowTitle("LIN_GUI")

    initial_frame = 50
    slider.setRange(0, 100)
    slider.setTickInterval(10)
    slider.setValue(initial_frame)
    slider_label_bar.setRange(0, 100)
    slider_label_bar.setTickInterval(10)

    global raw_file_buffer, frames_parsed, total_frames
    global frame_validity_map, init_data_timeline, op_data_timeline, ver_data_timeline
    global live_data_log, live_data_active
    raw_file_buffer = ""
    frames_parsed = 0
    total_frames = 0
    frame_validity_map.clear()
    globals.cable_node_frames = []
    evID_buffer.clear()
    seID_buffer.clear()
    evJ3072_buffer.clear()
    seJ3072_buffer.clear()

    evID_stage_bytes.clear()
    seID_stage_bytes.clear()

    # If live data is active, reset the start time to now. Otherwise, set to 0.
    if live_data_active:
        globals.live_data_start_time = time.time()
    else:
        globals.live_data_start_time = 0

    # Reset Label
    global label
    label.setText("Frame Number: 50 Unknown")
    label.setStyleSheet("color: black;")

    # Recent Data Debug Tab
    global LAST_N_FRAMES, recent_frame_types
    LAST_N_FRAMES = 100
    recent_frame_types = []
    globals.all_frame_types.clear()
    globals.frame_timestamps.clear()

    # Clear all data timelines and current data
    init_data_timeline.clear()
    op_data_timeline.clear()
    ver_data_timeline.clear()
    current_init_data.clear()
    current_op_data.clear()
    current_ver_data.clear()

    # Clear Dropdown labels
    collapsible_task.label_header.setText("")
    collapsible_contactor_state.label_header.setText("")
    collapsible_selected_protocol_version.label_header.setText("")
    collapsible_ratings.label_header.setText("")
    collapsible_seavailable_current.label_header.setText("")
    collapsible_evpresent_current.label_header.setText("")
    collapsible_evrequested_current.label_header.setText("")
    collapsible_control_page.label_header.setText("")
    collapsible_EvModeCtrl.label_header.setText("")
    collapsible_SeModeCtrl_page.label_header.setText("")
    collapsible_SeTargets1_page.label_header.setText("")

    # Clear all display widgets using a loop
    for widget in display_widgets:
        widget.clear()

    collapsible_task.toggle_button.setText("Task")
    collapsible_contactor_state.toggle_button.setText("Contactor State")
    collapsible_selected_protocol_version.toggle_button.setText("Protocol Version")
    collapsible_sesupported_protocol_versions.toggle_button.setText("Supported Versions")
    collapsible_ratings.toggle_button.setText("Ratings")
    collapsible_seavailable_current.toggle_button.setText("SeAvailableCurrent")
    collapsible_evpresent_current.toggle_button.setText("EvPresentCurrent")
    collapsible_evrequested_current.toggle_button.setText("EvRequestedCurrent")
    collapsible_EvInfo.toggle_button.setText("EvInfo")
    collapsible_SeInfo.toggle_button.setText("SeInfo")
    collapsible_cable_Node.toggle_button.setText("CaProperties")
    collapsible_sleep_Connection.toggle_button.setText("Sleep and Connection")
    collapsible_control_page.toggle_button.setText("OP3 Control Page")
    collapsible_EvModeCtrl.toggle_button.setText("EvModeCtrl")
    collapsible_SeModeCtrl_page.toggle_button.setText("SeModeCtrl")
    collapsible_SeTargets1_page.toggle_button.setText("SeTargets1")

    reset_time_button.setEnabled(live_data_active)

    '''
    #   If you want live data to toggle off when clear button is hit uncomment this

    if live_data_active:
        live_data_active = False
        live_data_button.setChecked(False)
        live_data_button.setIcon(QIcon(resource_path(r"images/toggle-off.png")))
        timer.stop()
        if ser and ser.is_open:
            ser.close()
    '''

    live_data_log.clear()
    dialog.accept()


def read_from_serial():
    """
    Called by a timer to read and process data from the serial port during a live session.
    Includes error handling for unexpected device disconnection.
    """
    global ser, live_data_active, live_data_log, raw_byte_list, auto_update1, total_frames
    if ser and ser.is_open and live_data_active:
        try:
            # USB is pulled out
            data_bytes = ser.read_all()

        except (serial.serialutil.SerialException,OSError) as e:
            # Stop the timer
            timer.stop()
            if ser and ser.is_open:
                ser.close()

            result_display.append(f"\n--- Serial Port Error ---")
            result_display.append("Live data stopped: Device disconnected or unavailable.")

            live_data_button.setChecked(False)
            live_data_button.setIcon(QIcon(resource_path(r"images/toggle-off.png")))

            file_button.setEnabled(True)
            reset_time_button.setEnabled(False)
            live_data_active = False
            auto_update1 = False

            refresh_all_displays(slider.value())
            return

        # if no error
        if data_bytes:
            live_data_log.append(' '.join(f"{b:02X}" for b in data_bytes))
            incoming_hex_list = [f"{b:02X}" for b in data_bytes]
            raw_byte_list += incoming_hex_list

            chunks, remainder = parse_data_stream(raw_byte_list)

            if chunks:
                raw_byte_list = remainder
                num_new_frames = sum(1 for chunk_type, _ in chunks if chunk_type == 'frame')
                if num_new_frames > 0:
                    total_frames += num_new_frames
                    slider.setMinimum(1)
                    slider.setMaximum(total_frames)

                    pattern = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
                    interval = pattern[-1]
                    for candidate in pattern:
                        if total_frames / candidate < 20:
                            interval = candidate
                            break

                    slider.setRange(1, total_frames)
                    slider.setTickInterval(interval)
                    slider_label_bar.setRange(1, total_frames)
                    slider_label_bar.setTickInterval(interval)

                display_frames(chunks)
            elif len(raw_byte_list) > 100:  # Threshold to clear junk data
                display_frames([('garbage', raw_byte_list)])
                raw_byte_list = []
            else:
                raw_byte_list = remainder


def process_live_binary_data(new_data_bytes):
    global raw_byte_list, live_data_log
    incoming_hex_list = [f"{b:02X}" for b in new_data_bytes]
    live_data_log.append(' '.join(incoming_hex_list))
    raw_byte_list += incoming_hex_list
    frames, remainder = parse_data_stream(raw_byte_list)
    display_frames(frames)
    raw_byte_list = remainder


save_log_button = QPushButton()
save_log_button.setIcon(QIcon(resource_path(r"images/save-icon.png")))

save_log_button.setFixedSize(40, 40)
save_log_button.setIconSize(QSize(25, 25))

save_log_button.setToolTip("Save Current Cached Data")

save_log_button.setStyleSheet("""
    QPushButton {
        background-color: transparent;
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")


def save_live_data_log():
    global live_data_log
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getSaveFileName(
        window,
        "Save Live Data Log",
        "",
        "Text Files (*.log);;All Files (*)",
        options=options
    )
    if file_path:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for entry in live_data_log:
                    f.write(entry + "\n")
            result_display.append(f"Live data log saved to {file_path}")
        except Exception as e:
            result_display.append(f"Error saving log: {e}")

save_log_button.clicked.connect(save_live_data_log)

debug_button = QPushButton()
debug_button.setIcon(QIcon(resource_path(r"images/debug-icon.png")))

debug_button.setFixedSize(40, 40)
debug_button.setIconSize(QSize(30, 30))

debug_button.setToolTip("Open Debug Window")
debug_button.setFont(font)
debug_button.setStyleSheet("""
    QPushButton {
        background-color: transparent;
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

trash_button = QPushButton()
trash_button.setIcon(QIcon(resource_path(r"images/trash-bin.png")))

trash_button.setFixedSize(40, 40)
trash_button.setIconSize(QSize(40, 40))

trash_button.setToolTip("Clear All Data")
trash_button.setFont(font)
trash_button.setStyleSheet("""
    QPushButton {
        background-color: transparent;
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

file_button = QPushButton()
file_button.setIcon(QIcon(resource_path(r"images/Add-file.png")))

file_button.setFixedSize(40, 40)
file_button.setIconSize(QSize(27, 27))

file_button.setToolTip("Select File")
file_button.setFont(font)
file_button.setStyleSheet("""
    QPushButton {
        background-color: transparent;
        border:  none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

live_data_button = QPushButton()
live_data_button.setIcon(QIcon(resource_path(r"images/toggle-off.png")))

live_data_button.setFixedSize(45, 45)
live_data_button.setIconSize(QSize(40, 40))

live_data_button.setToolTip("Toggle Live Data")
live_data_button.setFont(font)
live_data_button.setCheckable(True)
live_data_button.setChecked(False)
live_data_button.setStyleSheet("""
    QPushButton {
        background-color: transparent;
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

reset_time_button = QPushButton()
reset_time_button.setIcon(QIcon(resource_path(r"images/timer.png")))
reset_time_button.setFixedSize(40, 40)
reset_time_button.setIconSize(QSize(27, 27))
reset_time_button.setToolTip("Reset Timer")
reset_time_button.setFont(font)
reset_time_button.setEnabled(False)
reset_time_button.setStyleSheet("""
    QPushButton {
        background-color: transparent;
        border:  none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

NA_toggle = QPushButton()
NA_toggle.setIcon(QIcon(resource_path(r"images/NA_toggle.png")))
NA_toggle.setFixedSize(40, 40)
NA_toggle.setIconSize(QSize(31, 31))
NA_toggle.setToolTip("Toggle on or off viewable N/A values")
NA_toggle.setFont(font)
NA_toggle.setStyleSheet("""
    QPushButton {
        background-color: transparent;
        border:  none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")

frame_time_toggle_button = QPushButton()
frame_time_toggle_button.setIcon(QIcon(resource_path(r"images/frame-time-toggle-off.png")))

frame_time_toggle_button.setFixedSize(45, 45)
frame_time_toggle_button.setIconSize(QSize(40, 40))

frame_time_toggle_button.setToolTip("Toggle on to View Frames off for Timing")
frame_time_toggle_button.setFont(font)
frame_time_toggle_button.setCheckable(True)
frame_time_toggle_button.setEnabled(True)
frame_time_toggle_button.setStyleSheet("""
    QPushButton {
        background-color: transparent;
        border: none;
    }
    QPushButton:hover {
        background-color: rgba(150, 150, 150, 50);
    }
""")


def reset_live_data_timer():
    """
    Resets the session start time to the timestamp of the frame currently under the slider,
    making that frame the new "zero" point for time calculations.
    """
    if not live_data_active:
        result_display.append("Timer can only be reset during a live data session.")
        return

    fno_at_slider = slider.value()

    try:
        # Find the frame type for the selected frame number
        ftype = globals.all_frame_types[fno_at_slider - 1]

        # Find the specific timestamp for that frame
        ts_at_slider = None
        for fno, ts in globals.frame_timestamps.get(ftype, []):
            if fno == fno_at_slider:
                ts_at_slider = ts
                break

        if ts_at_slider:
            globals.live_data_start_time = ts_at_slider
            result_display.append(f"Timer zero point has been set to Frame {fno_at_slider}.")
            refresh_all_displays(slider.value())  # Refresh all displays to show new relative times
        else:
            result_display.append(f"Could not find a timestamp for Frame {fno_at_slider}.")

    except IndexError:
        result_display.append(f"No frame data available for Frame {fno_at_slider} to reset timer.")

NA_toggle.clicked.connect(toggle_na_view)
frame_time_toggle_button.clicked.connect(frame_time_toggle)
trash_button.clicked.connect(open_clear_data_dialog)
file_button.clicked.connect(open_file_dialog)
live_data_button.clicked.connect(toggle_live_data)
reset_time_button.clicked.connect(reset_live_data_timer)

button_layout = QHBoxLayout()
button_layout.addWidget(file_button)
button_layout.addWidget(debug_button)
button_layout.addWidget(live_data_button)
button_layout.addWidget(frame_time_toggle_button)
button_layout.addWidget(reset_time_button)
button_layout.addWidget(NA_toggle)
button_layout.addWidget(save_log_button)
button_layout.addWidget(trash_button)
button_layout.addStretch(1)


# Subclass QLineEdit so that the Enter key is handled locally.
class FindLineEdit(QLineEdit):
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.returnPressed.emit()
            event.accept()
        else:
            super().keyPressEvent(event)


class DebugDialog(QDialog):
    def __init__(self, parent, debug_text):
        super().__init__(parent)
        self.setWindowTitle("Debug Info")
        self.setModal(True)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint)

        self.resize(450, 450)

        # List of match starting positions and pointer to the current match (0-indexed)
        self.matches = []
        self.current_match_index = 0

        # TAB WIDGET
        self.tab_widget = QTabWidget()

        # tab debug info
        self.tab_debug = QWidget()
        self.tab_debug_layout = QVBoxLayout(self.tab_debug)

        # tab recent data
        self.tab_recent = QWidget()
        self.tab_recent_layout = QVBoxLayout(self.tab_recent)
        self.recent_data_edit = QTextEdit()
        self.recent_data_edit.setReadOnly(True)
        self.tab_recent_layout.addWidget(self.recent_data_edit)
        self.tab_recent.setLayout(self.tab_recent_layout)

        # Add both tabs to the QTabWidget
        self.tab_widget.addTab(self.tab_debug, "Debug Info")
        self.tab_widget.addTab(self.tab_recent, "Recent Data")

        # --- Find Bar (as a QWidget) ---
        self.find_bar_widget = QWidget()
        self.find_bar_layout = QHBoxLayout(self.find_bar_widget)
        self.find_label = QLabel("Find:")
        self.find_line_edit = FindLineEdit()
        self.find_status_label = QLabel("0/0")

        # Configure them as before
        self.find_label.setFont(QFont("SansSerif", 8))
        self.find_line_edit.setFont(QFont("SansSerif", 8))
        self.find_line_edit.setPlaceholderText("Enter text to search")
        self.find_bar_layout.addWidget(self.find_label)
        self.find_bar_layout.addWidget(self.find_line_edit)
        self.find_bar_layout.addWidget(self.find_status_label)
        self.find_bar_widget.setStyleSheet("background-color: #eee;")

        # --- Main Text Display ---
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setFont(QFont("Times New Roman", 9))
        self.text_display.setPlainText(debug_text)

        # Force highlight color for searching
        palette = self.text_display.palette()
        palette.setColor(QPalette.Active, QPalette.Highlight, QColor(135, 206, 250))
        palette.setColor(QPalette.Inactive, QPalette.Highlight, QColor(135, 206, 250))
        self.text_display.setPalette(palette)

        # --- Button Box ---
        self.button_box = QDialogButtonBox()
        self.save_button = self.button_box.addButton("Save", QDialogButtonBox.ActionRole)
        self.close_button = self.button_box.addButton(QDialogButtonBox.Close)
        self.close_button.clicked.connect(self.close)

        # Put it all into the debug tab’s layout
        self.tab_debug_layout.addWidget(self.find_bar_widget)
        self.tab_debug_layout.addWidget(self.text_display)
        self.tab_debug_layout.addWidget(self.button_box)
        self.tab_debug.setLayout(self.tab_debug_layout)

        # MAIN LAYOUT
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

        self.save_button.clicked.connect(self.save_debug_info)

        self.find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.find_shortcut.activated.connect(self.toggle_find_bar)
        self.find_line_edit.textChanged.connect(self.update_highlighting)
        self.find_line_edit.returnPressed.connect(self.find_next)

        self.setStyleSheet("""
                    QTextEdit {
                        font-size: 9pt;
                        font-family: 'Times New Roman';
                    }
                    QPushButton {
                        font-size: 8pt;
                    }
                """)

        self.update_recent_data_tab()
        slider.valueChanged.connect(self.update_recent_data_tab)

    def update_recent_data_tab(self):
        from collections import Counter
        global slider, LAST_N_FRAMES, frame_type_map

        end = min(slider.value(), len(globals.all_frame_types))
        start = max(0, end - LAST_N_FRAMES)
        window = globals.all_frame_types[start:end]
        counts = Counter(window)

        html = (
            "<table border='1' "
            "style='border-collapse:collapse; width:100%; text-align:center;'>"
            "<tr>"
            "<th>Frame Type</th>"
            "<th>Count</th>"
            "<th>Avg Time Between Copies</th>"
            "</tr>"
        )

        seen = set()
        for ftype in frame_type_map.values():
            seen.add(ftype)
            cnt = counts.get(ftype, 0)

            times = [
                ts
                for (fno, ts) in globals.frame_timestamps.get(ftype, [])
                if start < fno <= end
            ]

            if len(times) > 1:
                diffs = [t2 - t1 for t1, t2 in zip(times, times[1:])]
                avg_str = f"{sum(diffs) / len(diffs):.3f}s"
            else:
                avg_str = "--"

            html += f"<tr><td>{ftype}</td><td>{cnt}</td><td>{avg_str}</td></tr>"

        # append any unknown labels that actually occurred
        for ftype, cnt in counts.items():
            if ftype not in seen:
                times = [
                    ts
                    for (fno, ts) in globals.frame_timestamps.get(ftype, [])
                    if start < fno <= end
                ]
                if len(times) > 1:
                    diffs = [t2 - t1 for t1, t2 in zip(times, times[1:])]
                    avg_str = f"{sum(diffs) / len(diffs):.3f}s"
                else:
                    avg_str = "--"

                html += f"<tr><td>{ftype}</td><td>{cnt}</td><td>{avg_str}</td></tr>"

        # Close table and push into the widget
        html += "</table>"
        self.recent_data_edit.setHtml(html)

    def save_debug_info(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Debug Info", "", "Text Files (*.txt);;All Files (*)", options=options
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.text_display.toPlainText())
            except Exception as e:
                print(f"Error saving file: {e}")

    def toggle_find_bar(self):
        """Toggle the visibility of the find bar."""
        if self.find_bar_widget.isVisible():
            self.find_bar_widget.hide()
            self.text_display.setExtraSelections([])
        else:
            self.find_bar_widget.show()
            self.find_line_edit.setFocus()
            self.update_highlighting(self.find_line_edit.text())

    def update_highlighting(self, search_text):
        """Find all instances of the search text and highlight them.
           The current match is highlighted in light blue; all other matches are highlighted in yellow."""
        self.matches = []
        if search_text:
            cursor = QTextCursor(self.text_display.document())
            cursor.movePosition(QTextCursor.Start)
            while True:
                cursor = self.text_display.document().find(search_text, cursor)
                if cursor.isNull():
                    break
                self.matches.append(cursor.selectionStart())
            self.current_match_index = 0
        self.updateExtraSelections()
        total = len(self.matches)
        self.find_status_label.setText(f"{1 if total > 0 else 0}/{total}")

    def updateExtraSelections(self):
        """Set extra selections so that the current match is highlighted in light blue and others in yellow."""
        extra_selections = []
        search_text = self.find_line_edit.text()
        if search_text:
            doc = self.text_display.document()
            for idx, pos in enumerate(self.matches):
                cursor = QTextCursor(doc)
                cursor.setPosition(pos)
                cursor.setPosition(pos + len(search_text), QTextCursor.KeepAnchor)
                selection = QTextEdit.ExtraSelection()
                if idx == self.current_match_index:
                    selection.format.setBackground(QColor(135, 206, 250))
                else:
                    selection.format.setBackground(Qt.yellow)
                selection.cursor = cursor
                extra_selections.append(selection)
        self.text_display.setExtraSelections(extra_selections)

    def find_next(self):
        """Scroll to and center the current occurrence of the search term.
           The current match remains highlighted until the next Enter press."""
        search_text = self.find_line_edit.text()
        if not search_text or not self.matches:
            return

        self.updateExtraSelections()
        pos = self.matches[self.current_match_index]
        cursor = self.text_display.textCursor()
        cursor.setPosition(pos)
        cursor.setPosition(pos + len(search_text), QTextCursor.KeepAnchor)
        self.text_display.setTextCursor(cursor)
        QTimer.singleShot(0, lambda: self.center_cursor(cursor))
        total = len(self.matches)
        self.find_status_label.setText(f"{self.current_match_index + 1}/{total}")
        self.current_match_index = (self.current_match_index + 1) % total

    def center_cursor(self, cursor):
        """Center the given cursor in the text display by adjusting the vertical scrollbar."""
        rect = self.text_display.cursorRect(cursor)
        viewport_height = self.text_display.viewport().height()
        new_value = rect.top() - (viewport_height - rect.height()) // 2
        scrollbar = self.text_display.verticalScrollBar()
        new_value = max(scrollbar.minimum(), min(new_value, scrollbar.maximum()))
        scrollbar.setValue(new_value)
        self.text_display.ensureCursorVisible()


def open_debug_dialog():
    global debug_dialog
    debug_text = result_display.toPlainText()

    debug_dialog = DebugDialog(window, debug_text)
    debug_dialog.setModal(False)

    slider.valueChanged.connect(debug_dialog.update_recent_data_tab)

    #   Uncomment this code below to live update debug info I have commented it out it made it very laggy
    #   This will not stop recent data from updating live
    '''
    result_display.textChanged.connect(
        lambda: debug_dialog.text_display.setPlainText(result_display.toPlainText())
    )
    '''

    debug_dialog.show()


debug_button.clicked.connect(open_debug_dialog)

# --- Create the main container widget and the top-level vertical layout ---
central_widget = QWidget()
top_level_layout = QVBoxLayout(central_widget)

# --- Top section (Buttons and Slider) ---
top_level_layout.addLayout(button_layout)
top_level_layout.addLayout(top_bar)
top_level_layout.addLayout(slider_container_layout)

# --- Bottom section (Split into two panes) ---
content_area = QWidget()
content_hbox = QHBoxLayout(content_area)

# --- Left Pane (Collapsible boxes in a scroll area) ---
left_scroll_area = QScrollArea()
left_scroll_area.setWidgetResizable(True)
left_scroll_area.setStyleSheet("""
    QScrollArea {
        border: none;
    }
    QScrollBar:vertical {
        border: none;
        background: transparent;
        width: 8px;
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:vertical {
        background: #D0D0D0;
        min-height: 20px;
        border-radius: 4px;
    }
    QScrollBar::handle:vertical:hover {
        background: #B0B0B0;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
""")

left_container = QWidget()
left_vbox_layout = QVBoxLayout(left_container)  # This will hold the collapsible boxes
# Collapsible panel for "Task Operation"
collapsible_task = CollapsibleBox("Task")
collapsible_task.toggle_button.setText("Task")
task_layout = QVBoxLayout()
task_layout.addWidget(task_operation_display)
collapsible_task.setContentLayout(task_layout)
left_vbox_layout.addWidget(collapsible_task)
globals.collapsible_task = collapsible_task

# Collapsible panel for "Contactor State"
collapsible_contactor_state = CollapsibleBox("Contactor State")
collapsible_contactor_state.toggle_button.setText("Contactor State")
contactor_state_layout = QVBoxLayout()
contactor_state_layout.addWidget(contactor_state_display)
collapsible_contactor_state.setContentLayout(contactor_state_layout)
left_vbox_layout.addWidget(collapsible_contactor_state)
globals.collapsible_contactor_state = collapsible_contactor_state

# Open box on startup
collapsible_contactor_state.toggle_button.setChecked(True)
collapsible_contactor_state.on_toggle()

# Collapsible panel for "Selected Protocol Version"
collapsible_selected_protocol_version = CollapsibleBox("Protocol Version")
collapsible_selected_protocol_version.toggle_button.setText("Protocol Version")
selected_protocol_version_layout = QVBoxLayout()
selected_protocol_version_layout.addWidget(selected_protocol_version_display)
collapsible_selected_protocol_version.setContentLayout(selected_protocol_version_layout)
left_vbox_layout.addWidget(collapsible_selected_protocol_version)
globals.collapsible_selected_protocol_version = collapsible_selected_protocol_version

# Collapsible panel for "SeSupported Protocol Versions"
collapsible_sesupported_protocol_versions = CollapsibleBox("Supported Versions")
collapsible_sesupported_protocol_versions.toggle_button.setText("Supported Versions")
sesupported_protocol_versions_layout = QVBoxLayout()
sesupported_protocol_versions_layout.addWidget(sesupported_protocol_versions_display)
collapsible_sesupported_protocol_versions.setContentLayout(sesupported_protocol_versions_layout)
left_vbox_layout.addWidget(collapsible_sesupported_protocol_versions)
globals.collapsible_sesupported_protocol_versions = collapsible_sesupported_protocol_versions

# Collapsible panel for "Ratings"
collapsible_ratings = CollapsibleBox("Ratings")
collapsible_ratings.toggle_button.setText("Ratings")
ratings_layout = QVBoxLayout()
ratings_layout.addWidget(ratings_display)
collapsible_ratings.setContentLayout(ratings_layout)
left_vbox_layout.addWidget(collapsible_ratings)
globals.collapsible_ratings = collapsible_ratings

# Collapsible panel for "SeAvailableCurrent"
collapsible_seavailable_current = CollapsibleBox("SeAvailableCurrent")
collapsible_seavailable_current.toggle_button.setText("SeAvailableCurrent")
seavailable_current_layout = QVBoxLayout()
seavailable_current_layout.addWidget(seavailable_current_display)
collapsible_seavailable_current.setContentLayout(seavailable_current_layout)
left_vbox_layout.addWidget(collapsible_seavailable_current)
globals.collapsible_seavailable_current = collapsible_seavailable_current

# Open box on startup
collapsible_seavailable_current.toggle_button.setChecked(True)
collapsible_seavailable_current.on_toggle()

# Collapsible panel for "EvPresentCurrent"
collapsible_evpresent_current = CollapsibleBox("EvPresentCurrent")
collapsible_evpresent_current.toggle_button.setText("EvPresentCurrent")
evpresent_current_layout = QVBoxLayout()
evpresent_current_layout.addWidget(evpresent_current_display)
collapsible_evpresent_current.setContentLayout(evpresent_current_layout)
left_vbox_layout.addWidget(collapsible_evpresent_current)
globals.collapsible_evpresent_current = collapsible_evpresent_current

# Collapsible panel for "EvRequestedCurrent"
collapsible_evrequested_current = CollapsibleBox("EvRequestedCurrent")
collapsible_evrequested_current.toggle_button.setText("EvRequestedCurrent")
evrequested_current_layout = QVBoxLayout()
evrequested_current_layout.addWidget(evrequested_current_display)
collapsible_evrequested_current.setContentLayout(evrequested_current_layout)
left_vbox_layout.addWidget(collapsible_evrequested_current)
globals.collapsible_evrequested_current = collapsible_evrequested_current

# Collapsible panel for "EvInfo"
collapsible_EvInfo = CollapsibleBox("EvInfo")
collapsible_EvInfo.toggle_button.setText("EvInfo")
EvInfo_layout = QVBoxLayout()
EvInfo_layout.addWidget(EvInfo_display)
collapsible_EvInfo.setContentLayout(EvInfo_layout)
left_vbox_layout.addWidget(collapsible_EvInfo)
globals.collapsible_EvInfo = collapsible_EvInfo

# Collapsible panel for "SeInfo"
collapsible_SeInfo = CollapsibleBox("SeInfo")
collapsible_SeInfo.toggle_button.setText("SeInfo")
SeInfo_layout = QVBoxLayout()
SeInfo_layout.addWidget(SeInfo_display)
collapsible_SeInfo.setContentLayout(SeInfo_layout)
left_vbox_layout.addWidget(collapsible_SeInfo)
globals.collapsible_SeInfo = collapsible_SeInfo

# Collapsible panel for "Cable Node"
collapsible_cable_Node = CollapsibleBox("CaProperties")
collapsible_cable_Node.toggle_button.setText("CaProperties")
cable_Node_layout = QVBoxLayout()
cable_Node_layout.addWidget(cable_Node_display)
collapsible_cable_Node.setContentLayout(cable_Node_layout)
left_vbox_layout.addWidget(collapsible_cable_Node)
globals.collapsible_cable_Node = collapsible_cable_Node

# Collapsible panel for "Sleep and Connection"
collapsible_sleep_Connection = CollapsibleBox("Sleep and Connection")
collapsible_sleep_Connection.toggle_button.setText("Sleep and Connection")
sleep_Connection_layout = QVBoxLayout()
sleep_Connection_layout.addWidget(sleep_connection_display)
collapsible_sleep_Connection.setContentLayout(sleep_Connection_layout)
left_vbox_layout.addWidget(collapsible_sleep_Connection)
globals.collapsible_sleep_Connection = collapsible_sleep_Connection

# Collapsible panel OP3 Control Page
collapsible_control_page = CollapsibleBox("OP3 Control Page")
collapsible_control_page.toggle_button.setText("OP3 Control Page")
control_page_layout = QVBoxLayout()
control_page_layout.addWidget(control_page_display)
collapsible_control_page.setContentLayout(control_page_layout)
left_vbox_layout.addWidget(collapsible_control_page)
globals.collapsible_control_page = collapsible_control_page

# Collapsible panel OP252 Control Page
collapsible_OP252_control_page = CollapsibleBox("OP252 Control Page")
collapsible_OP252_control_page.toggle_button.setText("OP252 Control Page")
OP252_control_page_layout = QVBoxLayout()
OP252_control_page_layout.addWidget(OP252_control_page_display)
collapsible_OP252_control_page.setContentLayout(OP252_control_page_layout)
left_vbox_layout.addWidget(collapsible_OP252_control_page)
globals.collapsible_OP252_control_page = collapsible_OP252_control_page

# Collapsible panel EvModeCtrl
collapsible_EvModeCtrl = CollapsibleBox("EvModeCtrl")
collapsible_EvModeCtrl.toggle_button.setText("EvModeCtrl")
EvModeCtrl_layout = QVBoxLayout()
EvModeCtrl_layout.addWidget(EvModeCtrl_display)
collapsible_EvModeCtrl.setContentLayout(EvModeCtrl_layout)
left_vbox_layout.addWidget(collapsible_EvModeCtrl)
globals.collapsible_EvModeCtrl = collapsible_EvModeCtrl

# Collapsible panel SeModeCtrl
collapsible_SeModeCtrl_page = CollapsibleBox("SeModeCtrl")
collapsible_SeModeCtrl_page.toggle_button.setText("SeModeCtrl")
SeModeCtrl_layout = QVBoxLayout()
SeModeCtrl_layout.addWidget(SeModeCtrl_display)
collapsible_SeModeCtrl_page.setContentLayout(SeModeCtrl_layout)
left_vbox_layout.addWidget(collapsible_SeModeCtrl_page)
globals.collapsible_SeModeCtrl_page = collapsible_SeModeCtrl_page

# Collapsible panel SeTargets1
collapsible_SeTargets1_page = CollapsibleBox("SeTargets1")
collapsible_SeTargets1_page.toggle_button.setText("SeTargets1")
SeTargets1_layout = QVBoxLayout()
SeTargets1_layout.addWidget(SeTargets1_display)
collapsible_SeTargets1_page.setContentLayout(SeTargets1_layout)
left_vbox_layout.addWidget(collapsible_SeTargets1_page)
globals.collapsible_SeTargets1_page = collapsible_SeTargets1_page


left_vbox_layout.addStretch()
left_scroll_area.setWidget(left_container)

# --- Right Pane (Tab Widget) ---
right_tab_widget = QTabWidget()
#right_tab_widget.setMinimumWidth(int(450 * dpi_scale))  #uncomment for fixed width commented lets shrink with window
right_tab_widget.setStyleSheet("""
    QTabWidget::pane {
        border: none;
        background-color: transparent;
    }

""")

# Tab 1: se id stage
tab_seid = QWidget()
tab_seid_layout = QVBoxLayout(tab_seid)
tab_seid_layout.setContentsMargins(0, 0, 0, 0)
tab_seid_layout.addWidget(op3_seid_display)
right_tab_widget.addTab(tab_seid, "Se Id Stage")

# Tab 2: ev id stage
tab_evid = QWidget()
tab_evid_layout = QVBoxLayout(tab_evid)
tab_evid_layout.setContentsMargins(0, 0, 0, 0)
tab_evid_layout.addWidget(op3_evid_display)
right_tab_widget.addTab(tab_evid, "Ev Id Stage")

# Tab 3: se data
tab_se_data = QWidget()
tab_se_data_layout = QVBoxLayout(tab_se_data)
tab_se_data_layout.setContentsMargins(0, 0, 0, 0)
tab_se_data_layout.addWidget(se_data_tab_display)
right_tab_widget.addTab(tab_se_data, "Se Data")

# Tab 4: ev data
tab_ev_data = QWidget()
tab_ev_data_layout = QVBoxLayout(tab_ev_data)
tab_ev_data_layout.setContentsMargins(0, 0, 0, 0)
tab_ev_data_layout.addWidget(ev_data_tab_display)
right_tab_widget.addTab(tab_ev_data, "Ev Data")

# Tab 5: SeJ3072
tab_SeJ3072 = QWidget()
tab_SeJ3072_layout = QVBoxLayout(tab_SeJ3072)
tab_SeJ3072_layout.setContentsMargins(0, 0, 0, 0)
tab_SeJ3072_layout.addWidget(SeJ3072_tab_display)
right_tab_widget.addTab(tab_SeJ3072, "Se-J3072")

# Tab 6: EvJ3072
tab_EvJ3072 = QWidget()
tab_EvJ3072_layout = QVBoxLayout(tab_EvJ3072)
tab_EvJ3072_layout.setContentsMargins(0, 0, 0, 0)
tab_EvJ3072_layout.addWidget(EvJ3072_tab_display)
right_tab_widget.addTab(tab_EvJ3072, "Ev-J3072")

# --- Assemble the bottom content area ---  Alter the numbers below to change how big the left to right sizes of blocks
content_hbox.addWidget(left_scroll_area, stretch=2)
content_hbox.addWidget(right_tab_widget, stretch=2)

# --- Add the content area to the top-level layout ---
top_level_layout.addWidget(content_area)

# --- Set the central widget for the main window ---
window.setCentralWidget(central_widget)


# ------------- update Displays ---------------------
def refresh_all_displays(value):
    update_slider_label(value, frame_validity_map, label)
    update_task_display(value, ver_data_timeline, op_data_timeline, task_operation_display, format_frame)
    update_contactor_state_display(value, ver_data_timeline, contactor_state_display, format_frame)
    update_protocol_version_display(value, ver_data_timeline, selected_protocol_version_display, format_frame,
                                    ratings_display, protocol_version_names)
    update_sesupported_protocol_versions_display(value, ver_data_timeline, sesupported_protocol_versions_display,
                                                 format_frame)
    update_ratings_display(value, init_data_timeline, ratings_display)
    update_seavailable_current_display(value, init_data_timeline, seavailable_current_display, format_frame)
    update_evpresent_current_display(value, op_data_timeline, evpresent_current_display, format_frame)
    update_evrequested_current_display(value, op_data_timeline, evrequested_current_display, format_frame)
    update_EvInfo_display(value, init_data_timeline, EvInfo_display, format_frame)
    update_SeInfo_display(value, init_data_timeline, SeInfo_display, format_frame)
    update_CableNode_display(value, format_frame)
    update_sleep_connection_display(value, op_data_timeline, sleep_connection_display, format_frame)
    #   J3068/1 implementation
    update_Op3EvID_display(value, op_data_timeline, op3_evid_display, format_frame)
    update_Op3SeID_display(value, op_data_timeline, op3_seid_display, format_frame)
    update_ev_data_tab(value, init_data_timeline, op_data_timeline, ver_data_timeline, ev_data_tab_display,
                       format_frame)
    update_se_data_tab(value, init_data_timeline, op_data_timeline, ver_data_timeline, se_data_tab_display,
                       format_frame)
    update_control_page_display(value, op_data_timeline, control_page_display, format_frame)
    update_OP252_control_page_display(value, op_data_timeline, OP252_control_page_display, format_frame)
    update_EvModeCtrl_display(value, op_data_timeline, EvModeCtrl_display, format_frame)
    update_SeModeCtrl_display(value, op_data_timeline, SeModeCtrl_display, format_frame)
    update_EvJ3072_display(value, op_data_timeline, EvJ3072_tab_display, format_frame)
    update_SeJ3072_display(value, op_data_timeline, SeJ3072_tab_display, format_frame)
    update_SeTargets1_display(value, op_data_timeline, SeTargets1_display, format_frame)

# Initial call to populate displays
refresh_all_displays(slider.value())

slider.valueChanged.connect(refresh_all_displays)

timer = QTimer()
window.show()
sys.exit(app.exec_())