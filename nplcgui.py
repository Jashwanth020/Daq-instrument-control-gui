import sys
import time
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFileDialog, QComboBox, QCheckBox, QScrollArea, QSizePolicy, QGridLayout
)
from PyQt5.QtCore import QTimer, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import mplcursors

from keithley_2636B import Keithley2636B
from lakeshore import LakeShoreController335
from lakeshore325 import LakeShoreController325
from keithley2450 import Keithley2450
from sr830_controller1 import SR830Controller
# from mock_instruments import MockKeithley2636B as Keithley2636B
# from mock_instruments import MockLakeShoreController as LakeShoreController
# from mock2450 import Keithley2450

from PyQt5.QtCore import QThread, pyqtSignal


class InstrumentControlGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instrument Control - DAQ GUI")
        self.keithley = Keithley2636B()
        self.lakeshore = LakeShoreController335()
        self.keithley2450 = Keithley2450()
        self.keithley2450_address = "Not connected"
        self.keithley_address = "Not connected"
        self.lakeshore_address = "Not connected"
        self.lakeshore325_address = "Not connected"
        self.init_ui()

        self.temp_timer = QTimer()
        self.temp_timer.timeout.connect(self.update_temperature_display)
        self.temp_timer.start(1000)
        self.stop_requested = False

    def update_source_labels(self):
        unit = "V" if self.source_select.currentText() == "Voltage" else "A"
        self.start_label.setText(f"Start Source ({unit}):")
        self.stop_label.setText(f"Stop Source ({unit}):")
        self.fixed_label.setText(f"Fixed Source Value ({unit}):")

    def init_ui(self):
        # main_layout = QHBoxLayout()
        # control_panel = QVBoxLayout()

        main_layout = QHBoxLayout()

        # Scrollable control panel
        # scroll_area = QScrollArea()
        # scroll_area.setWidgetResizable(True)

        # control_widget = QWidget()
        # control_panel = QVBoxLayout(control_widget)

        # scroll_area.setWidget(control_widget)
        # Create scroll area for control panel
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff)  # ⛔ no horizontal scroll

        # Container widget for scroll area
        control_widget = QWidget()
        control_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred)

        control_panel = QVBoxLayout(control_widget)

        # Apply proper width to avoid horizontal overflow
        control_widget.setMinimumWidth(380)
        control_widget.setMaximumWidth(400)

        scroll_area.setWidget(control_widget)

        # Instrument selection checkboxes
        self.instrument_checkboxes = {
            "Keithley": QCheckBox("Keithley 2636B"),
            "LakeShore": QCheckBox("Lake Shore Controller"),
            "LakeShore325": QCheckBox("Lake Shore 325"),
            "Keithley2450": QCheckBox("Keithley 2450"), "LockIn": QCheckBox("SR830 Lock-in Amplifier"),

        }
        instrument_layout = QVBoxLayout()
        instrument_layout.addWidget(QLabel("Select Instruments:"))
        for checkbox in self.instrument_checkboxes.values():
            checkbox.stateChanged.connect(self.update_experiment_types)
            instrument_layout.addWidget(checkbox)
        control_panel.addLayout(instrument_layout)

        # # Container widgets for Keithley and Lake Shore controls
        # self.keithley_controls = QWidget()
        # self.lakeshore_controls = QWidget()
        # self.keithley_controls_layout = QVBoxLayout()
        # self.lakeshore_controls_layout = QVBoxLayout()
        # self.keithley_controls.setLayout(self.keithley_controls_layout)
        # self.lakeshore_controls.setLayout(self.lakeshore_controls_layout)

        # Dynamic experiment type dropdown
        self.experiment_select = QComboBox()
        self.experiment_select.setEditable(False)
        control_panel.addLayout(self.labeled_input(
            "Experiment Type:", self.experiment_select))

        # Instrument address label
        self.instrument_address_label = QLabel(
            "Keithley: Not connected | Lake Shore: Not connected")
        control_panel.addWidget(self.instrument_address_label)

        # Container widgets for Keithley and Lake Shore controls
        self.keithley_controls = QWidget()
        self.lakeshore_controls = QWidget()
        self.keithley_controls_layout = QVBoxLayout()
        self.lakeshore_controls_layout = QVBoxLayout()
        self.keithley_controls.setLayout(self.keithley_controls_layout)
        self.lakeshore_controls.setLayout(self.lakeshore_controls_layout)

        # Keithley connect button
        self.connect_keithley_btn = QPushButton("Connect Keithley")
        self.connect_keithley_btn.clicked.connect(self.connect_keithley)
        self.keithley_controls_layout.addWidget(self.connect_keithley_btn)

        self.disconnect_keithley_btn = QPushButton("Disconnect Keithley")
        self.disconnect_keithley_btn.clicked.connect(self.disconnect_keithley)
        self.disconnect_keithley_btn.setVisible(False)
        self.keithley_controls_layout.addWidget(self.disconnect_keithley_btn)

        # Lake Shore connect button
        self.connect_lakeshore_btn = QPushButton("Connect Lake Shore")
        self.connect_lakeshore_btn.clicked.connect(self.connect_lakeshore)
        self.lakeshore_controls_layout.addWidget(self.connect_lakeshore_btn)

        self.disconnect_lakeshore_btn = QPushButton("Disconnect Lake Shore")
        self.disconnect_lakeshore_btn.clicked.connect(
            self.disconnect_lakeshore)
        self.disconnect_lakeshore_btn.setVisible(False)
        self.lakeshore_controls_layout.addWidget(self.disconnect_lakeshore_btn)

        # Keithley controls
        self.k_address_input = QLineEdit()
        self.k_address_input.setPlaceholderText(
            "Optional: Keithley VISA Address")
        self.keithley_controls_layout.addLayout(
            self.labeled_input("Keithley Address:", self.k_address_input))

        self.channel_select = QComboBox()
        self.channel_select.addItems(["A", "B"])
        self.keithley_controls_layout.addLayout(
            self.labeled_input("Keithley Channel:", self.channel_select))

        self.source_select = QComboBox()
        self.source_select.addItems(["Voltage", "Current"])
        self.measure_select = QComboBox()
        self.measure_select.addItems(["Current", "Voltage", "Resistance"])
        self.keithley_controls_layout.addLayout(
            self.labeled_input("Source Type:", self.source_select))
        self.keithley_controls_layout.addLayout(
            self.labeled_input("Measure Type:", self.measure_select))

        self.compliance_input = QLineEdit("0.1")
        self.keithley_controls_layout.addLayout(self.labeled_input(
            "Compliance (A or V):", self.compliance_input))

        self.delay_input = QLineEdit("0.1")
        self.nplc_input = QLineEdit("1")
        self.keithley_controls_layout.addLayout(
            self.labeled_input("NPLC:", self.nplc_input))

        self.keithley_controls_layout.addLayout(
            self.labeled_input("Source Delay (s):", self.delay_input))

        self.pulse_width_input = QLineEdit("0.01")
        self.pulse_delay_input = QLineEdit("0.1")
        self.keithley_controls_layout.addLayout(
            self.labeled_input("Pulse Width (s):", self.pulse_width_input))
        self.keithley_controls_layout.addLayout(
            self.labeled_input("Pulse Delay (s):", self.pulse_delay_input))

        self.start_v_input = QLineEdit("0")
        self.stop_v_input = QLineEdit("5")
        self.steps_input = QLineEdit("50")
        self.cycles_input = QLineEdit("1")
        self.fixed_source_input = QLineEdit("0")

        self.start_label = QLabel("Start Source (A):")
        self.stop_label = QLabel("Stop Source (A):")
        self.fixed_label = QLabel("Fixed Source Value (A):")

        self.keithley_controls_layout.addLayout(
            self.labeled_input_widget(self.start_label, self.start_v_input))
        self.keithley_controls_layout.addLayout(
            self.labeled_input_widget(self.stop_label, self.stop_v_input))
        self.keithley_controls_layout.addLayout(
            self.labeled_input("Steps:", self.steps_input))
        self.keithley_controls_layout.addLayout(
            self.labeled_input("Number of Cycles:", self.cycles_input))
        self.keithley_controls_layout.addLayout(
            self.labeled_input_widget(self.fixed_label, self.fixed_source_input))

        self.probe_mode_select = QComboBox()
        self.probe_mode_select.addItems(["2-Probe", "4-Probe"])
        self.keithley_controls_layout.addLayout(
            self.labeled_input("Measurement Mode:", self.probe_mode_select))

        # Time Logging - Common block
        self.interval_input = QLineEdit("1000")
        self.total_time_input = QLineEdit("60000")
        control_panel.addLayout(self.labeled_input(
            "Interval (ms):", self.interval_input))
        control_panel.addLayout(self.labeled_input(
            "Total Time (ms):", self.total_time_input))

        # Lake Shore controls
        self.l_address_input = QLineEdit()
        self.l_address_input.setPlaceholderText(
            "Optional: Lake Shore VISA Address")
        self.lakeshore_controls_layout.addLayout(
            self.labeled_input("Lake Shore Address:", self.l_address_input))

        # self.use_temp_checkbox = QCheckBox("Use Temperature Control")
        # self.use_temp_checkbox.setChecked(True)
        # self.lakeshore_controls_layout.addWidget(self.use_temp_checkbox)

        self.temp_input = QLineEdit("25")
        self.lakeshore_controls_layout.addLayout(
            self.labeled_input("Set Temperature (°C):", self.temp_input))

        self.output_channel_select = QComboBox()
        self.output_channel_select.addItems(["1", "2", "3", "4"])
        self.lakeshore_controls_layout.addLayout(
            self.labeled_input("Output Channel:", self.output_channel_select))

        self.input_channel_select = QComboBox()
        self.input_channel_select.addItems(["A", "B", "C", "D"])
        self.lakeshore_controls_layout.addLayout(
            self.labeled_input("Sensor Channel:", self.input_channel_select))

        self.live_temp_label = QLabel("Current Temperature: -- °C")
        self.lakeshore_controls_layout.addWidget(self.live_temp_label)

        self.keithley2450_controls = QWidget()
        self.keithley2450_controls_layout = QVBoxLayout()
        self.keithley2450_controls.setLayout(self.keithley2450_controls_layout)
        control_panel.addWidget(self.keithley2450_controls)
        self.lakeshore325_controls = QWidget()
        self.lakeshore325_controls_layout = QVBoxLayout()
        self.lakeshore325_controls.setLayout(self.lakeshore325_controls_layout)

        self.connect_lakeshore325_btn = QPushButton("Connect Lake Shore 325")
        self.connect_lakeshore325_btn.clicked.connect(
            self.connect_lakeshore325)
        self.lakeshore325_controls_layout.addWidget(
            self.connect_lakeshore325_btn)

        self.disconnect_lakeshore325_btn = QPushButton(
            "Disconnect Lake Shore 325")
        self.disconnect_lakeshore325_btn.clicked.connect(
            self.disconnect_lakeshore325)
        self.disconnect_lakeshore325_btn.setVisible(False)
        self.lakeshore325_controls_layout.addWidget(
            self.disconnect_lakeshore325_btn)

        self.l325_address_input = QLineEdit()
        self.l325_address_input.setPlaceholderText(
            "Optional: Lake Shore 325 VISA Address")
        self.lakeshore325_controls_layout.addLayout(
            self.labeled_input("Lake Shore 325 Address:",
                               self.l325_address_input)
        )

        self.l325_temp_input = QLineEdit("25")
        self.lakeshore325_controls_layout.addLayout(
            self.labeled_input("Set Temperature (°C):", self.l325_temp_input)
        )

        self.l325_input_channel_select = QComboBox()
        self.l325_input_channel_select.addItems(["1", "2"])
        self.lakeshore325_controls_layout.addLayout(
            self.labeled_input("Sensor Channel:",
                               self.l325_input_channel_select)
        )

        self.l325_live_temp_label = QLabel("Current Temperature: -- °C")
        self.lakeshore325_controls_layout.addWidget(self.l325_live_temp_label)

        # --- Lock-in Controls ---
        self.lockin_controls = QWidget()
        self.lockin_controls_layout = QVBoxLayout()
        self.lockin_controls.setLayout(self.lockin_controls_layout)

        # Connect Button
        self.connect_lockin_btn = QPushButton("Connect Lock-in Amplifier")
        self.connect_lockin_btn.clicked.connect(self.connect_lockin)
        self.lockin_controls_layout.addWidget(self.connect_lockin_btn)

        self.disconnect_lockin_btn = QPushButton(
            "Disconnect Lock-in Amplifier")
        self.disconnect_lockin_btn.clicked.connect(self.disconnect_lockin)
        self.disconnect_lockin_btn.setVisible(False)
        self.lockin_controls_layout.addWidget(self.disconnect_lockin_btn)

        # --- AC I-V Sweep Input Fields ---
        self.ac_iv_inputs_widget = QWidget()
        ac_iv_layout = QVBoxLayout(self.ac_iv_inputs_widget)

        self.ac_start_input = QLineEdit("0")
        self.ac_stop_input = QLineEdit("1")
        self.ac_steps_input = QLineEdit("10")

        ac_iv_layout.addLayout(self.labeled_input(
            "Start Voltage (V):", self.ac_start_input))
        ac_iv_layout.addLayout(self.labeled_input(
            "Stop Voltage (V):", self.ac_stop_input))
        ac_iv_layout.addLayout(self.labeled_input(
            "Steps:", self.ac_steps_input))

        self.lockin_controls_layout.addWidget(self.ac_iv_inputs_widget)
        self.ac_iv_inputs_widget.hide()

        # --- Impedance vs Time Input Fields ---
        self.impedance_inputs_widget = QWidget()
        imp_layout = QVBoxLayout(self.impedance_inputs_widget)

        self.imp_duration_input = QLineEdit("10")
        self.imp_interval_input = QLineEdit("0.5")

        imp_layout.addLayout(self.labeled_input(
            "Measurement Duration (s):", self.imp_duration_input))
        imp_layout.addLayout(self.labeled_input(
            "Interval (s):", self.imp_interval_input))

        self.lockin_controls_layout.addWidget(self.impedance_inputs_widget)
        self.impedance_inputs_widget.hide()

        # Frequency and Amplitude
        self.lockin_freq_input = QLineEdit("1000")
        self.lockin_amp_input = QLineEdit("1.0")
        self.lockin_controls_layout.addLayout(self.labeled_input(
            "Reference Frequency (Hz):", self.lockin_freq_input))
        self.lockin_controls_layout.addLayout(self.labeled_input(
            "Reference Amplitude (V):", self.lockin_amp_input))

        # Frequency Sweep Controls
        self.lockin_freq_start_input = QLineEdit("100")
        self.lockin_freq_stop_input = QLineEdit("10000")
        # self.lockin_freq_steps_input = QLineEdit("50")

        self.freq_start_layout = self.labeled_input(
            "Start Frequency (Hz):", self.lockin_freq_start_input)
        self.freq_stop_layout = self.labeled_input(
            "Stop Frequency (Hz):", self.lockin_freq_stop_input)
        # self.freq_steps_layout = self.labeled_input("Steps:", self.lockin_freq_steps_input)

        self.lockin_controls_layout.addLayout(self.freq_start_layout)
        self.lockin_controls_layout.addLayout(self.freq_stop_layout)
        # self.lockin_controls_layout.addLayout(self.freq_steps_layout)

        self.freq_start_layout.setEnabled(False)
        self.freq_stop_layout.setEnabled(False)
        # self.freq_steps_layout.setEnabled(False)
        self.lockin_freq_interval_input = QLineEdit(
            "100")  # Default 100 Hz step
        self.freq_interval_layout = self.labeled_input(
            "Frequency Interval (Hz):", self.lockin_freq_interval_input)
        self.lockin_controls_layout.addLayout(self.freq_interval_layout)
        self.freq_interval_layout.setEnabled(False)

        # Time Constant
        self.lockin_tc_select = QComboBox()
        self.lockin_tc_select.addItems(
            [str(i) for i in range(19)])  # SR830 values
        self.lockin_controls_layout.addLayout(self.labeled_input(
            "Time Constant Index:", self.lockin_tc_select))

        # Sensitivity
        self.lockin_sens_select = QComboBox()
        self.lockin_sens_select.addItems(
            [str(i) for i in range(27)])  # SR830 levels
        self.lockin_controls_layout.addLayout(self.labeled_input(
            "Sensitivity Index:", self.lockin_sens_select))

        # Output Mode
        self.lockin_output_mode = QComboBox()
        self.lockin_output_mode.addItems(["X/Y", "R/θ"])
        self.lockin_controls_layout.addLayout(
            self.labeled_input("Output Mode:", self.lockin_output_mode))

        # Dual sweep checkbox
        self.dual_sweep_checkbox = QCheckBox("Enable Dual Sweep")
        self.keithley_controls_layout.addWidget(self.dual_sweep_checkbox)
        self.keithley2450_controls_layout.addWidget(
            QCheckBox("Enable Dual Sweep"))
        self.dual_sweep_checkbox_2450 = self.keithley2450_controls_layout.itemAt(
            self.keithley2450_controls_layout.count() - 1).widget()


# 🔚 Finally, add to GUI panel
        control_panel.addWidget(self.lockin_controls)

        # Log scale checkboxes - keep always visible
        self.log_x_checkbox = QCheckBox("Log X")
        self.log_y_checkbox = QCheckBox("Log Y")
        control_panel.addWidget(self.log_x_checkbox)
        control_panel.addWidget(self.log_y_checkbox)

        # Buttons - always visible
        # btn_layout = QHBoxLayout()
        btn_layout = QGridLayout()

        self.start_btn = QPushButton("Start Sweep")
        self.start_log_btn = QPushButton("Start Time Logging")
        self.clear_btn = QPushButton("Clear Plot")
        self.save_btn = QPushButton("Save Plot")
        self.save_csv_btn = QPushButton("Save CSV")
        self.stop_btn = QPushButton("Stop")
        for btn in [self.start_btn, self.start_log_btn, self.stop_btn, self.clear_btn, self.save_btn, self.save_csv_btn]:
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.stop_btn.clicked.connect(self.request_stop)
        btn_layout.addWidget(self.stop_btn, 0, 2)

        self.start_btn.clicked.connect(self.start_sweep)
        self.start_log_btn.clicked.connect(self.start_time_logging)
        self.clear_btn.clicked.connect(self.clear_plot)
        self.save_btn.clicked.connect(self.save_plot)
        self.save_csv_btn.clicked.connect(self.save_csv)

        btn_layout.addWidget(self.start_btn, 0, 0)
        btn_layout.addWidget(self.start_log_btn, 0, 1)
        btn_layout.addWidget(self.clear_btn, 1, 0)
        btn_layout.addWidget(self.save_btn, 1, 1)
        btn_layout.addWidget(self.save_csv_btn, 1, 2)
        control_panel.addLayout(btn_layout)

        # Add instrument control widgets
        control_panel.addWidget(self.keithley_controls)
        control_panel.addWidget(self.lakeshore_controls)
        control_panel.addWidget(self.lakeshore325_controls)
        self.lakeshore325_controls.setVisible(False)

        # Plot
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.grid(True)
        self.canvas.draw()
        # main_layout.addLayout(control_panel, 1)
        main_layout.addWidget(scroll_area, 1)
        main_layout.addWidget(self.canvas, 4)

        # Status
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)

        # Final setup
        self.setLayout(main_layout)
        self.source_select.currentTextChanged.connect(
            self.update_source_labels)
        self.update_source_labels()
        self.keithley_controls.setVisible(False)
        self.lakeshore_controls.setVisible(False)

        # Connect button
        self.connect_2450_btn = QPushButton("Connect Keithley 2450")
        self.connect_2450_btn.clicked.connect(self.connect_keithley_2450)
        self.keithley2450_controls_layout.addWidget(self.connect_2450_btn)

        self.disconnect_2450_btn = QPushButton("Disconnect Keithley 2450")
        self.disconnect_2450_btn.clicked.connect(self.disconnect_keithley_2450)
        self.disconnect_2450_btn.setVisible(False)
        self.keithley2450_controls_layout.addWidget(self.disconnect_2450_btn)


# VISA Address
        self.k2450_address_input = QLineEdit()
        self.k2450_address_input.setPlaceholderText(
            "Optional: Keithley 2450 VISA Address")
        self.keithley2450_controls_layout.addLayout(
            self.labeled_input("2450 Address:", self.k2450_address_input))

# Source & measure types
        self.k2450_source_select = QComboBox()
        self.k2450_source_select.addItems(["Voltage", "Current"])
        self.k2450_measure_select = QComboBox()
        self.k2450_measure_select.addItems(
            ["Current", "Voltage", "Resistance"])
        self.keithley2450_controls_layout.addLayout(
            self.labeled_input("Source Type:", self.k2450_source_select))
        self.keithley2450_controls_layout.addLayout(
            self.labeled_input("Measure Type:", self.k2450_measure_select))

# Sweep inputs
        self.k2450_start_input = QLineEdit("0")
        self.k2450_stop_input = QLineEdit("5")
        self.k2450_steps_input = QLineEdit("50")
        self.k2450_compliance_input = QLineEdit("0.1")

        self.keithley2450_controls_layout.addLayout(
            self.labeled_input("Start Value:", self.k2450_start_input))
        self.keithley2450_controls_layout.addLayout(
            self.labeled_input("Stop Value:", self.k2450_stop_input))
        self.keithley2450_controls_layout.addLayout(
            self.labeled_input("Steps:", self.k2450_steps_input))
        self.keithley2450_controls_layout.addLayout(
            self.labeled_input("Compliance:", self.k2450_compliance_input))
        self.k2450_cycles_input = QLineEdit("1")
        self.keithley2450_controls_layout.addLayout(
            self.labeled_input("Number of Cycles:", self.k2450_cycles_input))
        self.k2450_fixed_input = QLineEdit("0")
        self.keithley2450_controls_layout.addLayout(
            self.labeled_input("Fixed Source Value:", self.k2450_fixed_input)
        )

        self.k2450_nplc_input = QLineEdit("1")
        self.keithley2450_controls_layout.addLayout(
            self.labeled_input("NPLC:", self.k2450_nplc_input))

    def update_experiment_types(self):
        selected = [name for name,
                    cb in self.instrument_checkboxes.items() if cb.isChecked()]
        self.experiment_select.clear()
        experiments = set()

        self.keithley_controls.setVisible("Keithley" in selected)
        self.lakeshore_controls.setVisible("LakeShore" in selected)
        self.keithley2450_controls.setVisible("Keithley2450" in selected)
        self.lakeshore325_controls.setVisible("LakeShore325" in selected)
        if "Keithley" in selected:
            experiments.update(["IV Sweep",  "Time Logging", "Pulse IV Sweep"])

        if "LakeShore" in selected:
            experiments.update(["Temperature Stabilization"])
        if "LakeShore325" in selected:
            experiments.update(["Temperature Stabilization 325"])
        if ("Keithley" in selected and "LakeShore" in selected) or \
           ("Keithley2450" in selected and "LakeShore" in selected):
            experiments.add("Temperature Dependent IV")

        if "Keithley2450" in selected:
            experiments.update(["IV Sweep 2450", "Time Logging 2450"])
        if "LockIn" in selected:
            experiments.update(["AC Signal Measurement", "Impedance vs Time", "Frequency Sweep",
                               "Harmonic Detection", "AC I-V Measurement (Lock-in Only)"])

        if "Keithley" in selected and "LockIn" in selected:
            experiments.add("AC I-V Measurement (2636B)")

        if "Keithley2450" in selected and "LockIn" in selected:
            experiments.add("AC I-V Measurement (2450)")

        if "LockIn" in selected and "LakeShore" in selected:
            if "Keithley" in selected:
                experiments.add("Temp Dependent AC I-V (2636B)")
            if "Keithley2450" in selected:
                experiments.add("Temp Dependent AC I-V (2450)")

        if not experiments:
            self.experiment_select.addItem("Select instrument(s) first")
        else:
            self.experiment_select.addItems(sorted(experiments))

        self.lockin_controls.setVisible("LockIn" in selected)
        self.experiment_select.currentIndexChanged.connect(
            self.update_lockin_inputs_visibility)

    def labeled_input(self, label_text, input_widget):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setMinimumWidth(140)
        input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(label)
        layout.addWidget(input_widget, 1)
        return layout

    def labeled_input_widget(self, label_widget, input_widget):
        layout = QHBoxLayout()
        label_widget.setMinimumWidth(140)
        input_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(label_widget)
        layout.addWidget(input_widget, 1)
        return layout

    # ... other methods (connect_keithley, connect_lakeshore, start_sweep, start_time_logging, etc.) remain unchanged ...
    def connect_keithley(self):
        k_address = self.k_address_input.text().strip()
        k_ok = self.keithley.connect(address=k_address if k_address else None)
        if k_ok:
            self.keithley_address = self.keithley.address
            self.k_address_input.setPlaceholderText(
                f"Connected: {self.keithley_address}")
            self.disconnect_keithley_btn.setVisible(True)

            QMessageBox.information(
                self, "Success", "Keithley connected successfully!")
            self.refresh_address_label()
        else:
            QMessageBox.critical(
                self, "Error", "Failed to connect to Keithley.")

    def connect_lakeshore(self):
        l_address = self.l_address_input.text().strip()
        l_ok = self.lakeshore.connect(address=l_address if l_address else None)
        if l_ok:
            self.lakeshore_address = self.lakeshore.address
            self.l_address_input.setPlaceholderText(
                f"Connected: {self.lakeshore_address}")
            self.disconnect_lakeshore_btn.setVisible(True)
            self.refresh_address_label()
            QMessageBox.information(
                self, "Success", "Lake Shore connected successfully!")
        else:
            QMessageBox.critical(
                self, "Error", "Failed to connect to Lake Shore.")

    def connect_lakeshore325(self):
        l325_address = self.l325_address_input.text().strip()
        l325_ok = self.lakeshore325.connect(
            address=l325_address if l325_address else None)
        if l325_ok:
            self.lakeshore325_address = self.lakeshore325.address
            self.l325_address_input.setPlaceholderText(
                f"Connected: {self.lakeshore325_address}")
            self.disconnect_lakeshore325_btn.setVisible(True)
            self.refresh_address_label()
            QMessageBox.information(
                self, "Success", "Lake Shore 325 connected successfully!")
        else:
            QMessageBox.critical(
                self, "Error", "Failed to connect to Lake Shore 325.")

    def disconnect_lakeshore325(self):
        self.lakeshore325.close()
        self.disconnect_lakeshore325_btn.setVisible(False)
        self.l325_address_input.setPlaceholderText("Disconnected")
        self.lakeshore325_address = "Not connected"
        self.refresh_address_label()

    def connect_keithley_2450(self):
        address = self.k2450_address_input.text().strip()
        ok = self.keithley2450.connect(address if address else None)
        if ok:
            self.keithley2450_address = self.keithley2450.address
            self.k2450_address_input.setPlaceholderText(
                f"Connected: {self.keithley2450_address}")
            self.disconnect_2450_btn.setVisible(True)
            self.refresh_address_label()
            QMessageBox.information(
                self, "Success", "Keithley 2450 connected successfully!")
        else:
            QMessageBox.critical(
                self, "Error", "Failed to connect to Keithley 2450.")

    def connect_lockin(self):
        try:
            self.lockin = SR830Controller()
            self.disconnect_lockin_btn.setVisible(True)
            QMessageBox.information(
                self, "Success", "SR830 Lock-in connected.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def configure_lockin(self):
        if not hasattr(self, 'lockin'):
            raise Exception("Lock-in not connected.")

        freq = float(self.lockin_freq_input.text())
        amp = float(self.lockin_amp_input.text())
        tc_index = int(self.lockin_tc_select.currentText())
        sens_index = int(self.lockin_sens_select.currentText())

        self.lockin.set_reference(freq, amp)
        self.lockin.set_time_constant(tc_index)
        self.lockin.set_sensitivity(sens_index)

    def request_stop(self):
        self.stop_requested = True
        self.status_label.setText("Stopping requested...")

    def disconnect_keithley(self):
        self.keithley.disconnect()
        self.disconnect_keithley_btn.setVisible(False)
        self.k_address_input.setPlaceholderText("Disconnected")
        self.keithley_address = "Not connected"
        self.refresh_address_label()

    def disconnect_lakeshore(self):
        self.lakeshore.disconnect()
        self.disconnect_lakeshore_btn.setVisible(False)
        self.l_address_input.setPlaceholderText("Disconnected")
        self.lakeshore_address = "Not connected"
        self.refresh_address_label()

    def disconnect_keithley_2450(self):
        self.keithley2450.disconnect()
        self.disconnect_2450_btn.setVisible(False)
        self.k2450_address_input.setPlaceholderText("Disconnected")
        self.keithley2450_address = "Not connected"
        self.refresh_address_label()

    def disconnect_lockin(self):
        if hasattr(self, 'lockin'):
            self.lockin.disconnect()
            del self.lockin
        self.disconnect_lockin_btn.setVisible(False)
        QMessageBox.information(self, "Info", "Lock-in disconnected.")

    # def refresh_address_label(self):
    #     self.instrument_address_label.setText(
    #         f"Keithley: {self.keithley_address} | "
    #         f"Lake Shore: {self.lakeshore_address} | "
    #         f"Keithley 2450: {self.keithley2450_address}"
    #     )

    def refresh_address_label(self):
        self.instrument_address_label.setText(
            f"Keithley: {self.keithley_address} | "
            f"Lake Shore: {self.lakeshore_address} | "
            f"Keithley 2450: {self.keithley2450_address} | "
            f"Lake Shore 325: {self.lakeshore325_address}"
        )
    # ... rest of the methods unchanged ...
    # def start_sweep(self):
    #     channel = self.channel_select.currentText().lower()  # 'a' or 'b'
    #     selected = [name for name, cb in self.instrument_checkboxes.items() if cb.isChecked()]

    #     try:
    #         target_temp = float(self.temp_input.text())
    #         output_channel = int(self.output_channel_select.currentText())
    #         input_channel = self.input_channel_select.currentText()
    #         probe_mode = self.probe_mode_select.currentText()

    #         if self.use_temp_checkbox.isChecked():
    #            self.lakeshore.set_temperature(target_temp, channel=output_channel)
    #            if not self.lakeshore.stabilize_temperature(target_temp, channel=input_channel):
    #               QMessageBox.warning(self, "Warning", "Temperature not stabilized.")
    #               return

    #         source_type = self.source_select.currentText()
    #         measure_type = self.measure_select.currentText()

    #         delay = float(self.delay_input.text())
    #         self.keithley.configure_smu(source_type=source_type, source_value=0, current_limit=0.1, source_delay=delay)

    #         if probe_mode == "4-Probe":
    #            self.keithley.smu.write(f"smu{channel}.sense = smu{channel}.SENSE_REMOTE")
    #         else:
    #             self.keithley.smu.write(f"smu{channel}.sense = smu{channel}.SENSE_LOCAL")

    #         start_v = float(self.start_v_input.text())
    #         stop_v = float(self.stop_v_input.text())
    #         steps = int(self.steps_input.text())
    #         cycles = int(self.cycles_input.text())

    #         x_vals, y_vals = [], []

    #         for cycle in range(cycles):
    #             for val in np.linspace(start_v, stop_v, steps):
    #                 if source_type == "Voltage":
    #                     self.keithley.smu.write(f"smu{channel}.source.levelv = {val}")
    #                 elif source_type == "Current":
    #                     self.keithley.smu.write(f"smu{channel}.source.leveli = {val}")

    #                 self.keithley.smu.write(f"smu{channel}.source.output = smu{channel}.OUTPUT_ON")

    #                 time.sleep(0.05)
    #                 measured = self.keithley.measure(measure_type)
    #                 x_vals.append(val)
    #                 y_vals.append(measured)
    #                 self.plot_data(x_vals, y_vals, x_label=source_type, y_label=measure_type,
    #                                title=f"{measure_type} vs {source_type} (Cycle {cycle + 1})")
    #                 QApplication.processEvents()
    #         self.keithley.smu.write(f"smu{channel}.source.output = smu{channel}.OUTPUT_OFF")

    #     except Exception as e:
    #         QMessageBox.critical(self, "Error", str(e))

    #     if "Keithley2450" in selected:
    #         try:
    #                source_type = self.k2450_source_select.currentText()
    #                measure_type = self.k2450_measure_select.currentText()
    #                start_val = float(self.k2450_start_input.text())
    #                stop_val = float(self.k2450_stop_input.text())
    #                steps = int(self.k2450_steps_input.text())
    #                compliance = float(self.k2450_compliance_input.text())

    #                self.keithley2450.configure_smu(
    #                source_type=source_type,
    #                source_value=start_val,
    #                current_limit=compliance
    #     )

    #                x_vals, y_vals = self.keithley2450.sweep(
    #                source_type=source_type,
    #                measure_type=measure_type,
    #                start=start_val,
    #                stop=stop_val,
    #                steps=steps,
    #                delay=0.1
    #     )

    #                self.plot_data(
    #                x_vals, y_vals,
    #                x_label=source_type,
    #                y_label=measure_type,
    #                title="Keithley 2450 Sweep"
    #     )

    #         except Exception as e:
    #                QMessageBox.critical(self, "Error", f"2450 Sweep Failed:\n{e}")

    # def start_sweep(self):
    #     experiment = self.experiment_select.currentText()
    #     selected = [name for name, cb in self.instrument_checkboxes.items() if cb.isChecked()]
    #     channel = self.channel_select.currentText().lower()

    #     try:
    #     # If LakeShore selected, stabilize temperature first
    #        if "LakeShore" in selected:
    #            target_temp = float(self.temp_input.text())
    #            output_channel = int(self.output_channel_select.currentText())
    #            input_channel = self.input_channel_select.currentText()

    #            self.lakeshore.set_temperature(target_temp, channel=output_channel)
    #            if not self.lakeshore.stabilize_temperature(target_temp, channel=input_channel):
    #                 QMessageBox.warning(self, "Warning", "Temperature not stabilized.")
    #                 return

    #     # --- Keithley 2636B Sweep ---
    #        if "Keithley" in selected:
    #             probe_mode = self.probe_mode_select.currentText()
    #             source_type = self.source_select.currentText()
    #             measure_type = self.measure_select.currentText()
    #             delay = float(self.delay_input.text())

    #             self.keithley.configure_smu(
    #                 source_type=source_type,
    #                 source_value=0,
    #                 current_limit=0.1,
    #                 source_delay=delay
    #             )

    #             if probe_mode == "4-Probe":
    #                 self.keithley.smu.write(f"smu{channel}.sense = smu{channel}.SENSE_REMOTE")
    #             else:
    #                 self.keithley.smu.write(f"smu{channel}.sense = smu{channel}.SENSE_LOCAL")

    #             start_v = float(self.start_v_input.text())
    #             stop_v = float(self.stop_v_input.text())
    #             steps = int(self.steps_input.text())
    #             cycles = int(self.cycles_input.text())

    #             x_vals, y_vals = [], []

    #             for cycle in range(cycles):
    #                 for val in np.linspace(start_v, stop_v, steps):
    #                     if source_type == "Voltage":
    #                         self.keithley.smu.write(f"smu{channel}.source.levelv = {val}")
    #                     elif source_type == "Current":
    #                         self.keithley.smu.write(f"smu{channel}.source.leveli = {val}")

    #                     self.keithley.smu.write(f"smu{channel}.source.output = smu{channel}.OUTPUT_ON")
    #                     time.sleep(0.05)
    #                     measured = self.keithley.measure(measure_type)
    #                     x_vals.append(val)
    #                     y_vals.append(measured)

    #                     self.plot_data(
    #                         x_vals, y_vals,
    #                         x_label=source_type,
    #                         y_label=measure_type,
    #                         title=f"Keithley 2636B: {measure_type} vs {source_type} (Cycle {cycle + 1})"
    #                     )
    #                     QApplication.processEvents()

    #             self.keithley.smu.write(f"smu{channel}.source.output = smu{channel}.OUTPUT_OFF")

    #     # --- Keithley 2450 Sweep ---
    #        if "Keithley2450" in selected:
    #         # Optionally re-check temperature for 2450 as well
    #             if "LakeShore" in selected:
    #                 target_temp = float(self.temp_input.text())
    #                 output_channel = int(self.output_channel_select.currentText())
    #                 input_channel = self.input_channel_select.currentText()

    #                 self.lakeshore.set_temperature(target_temp, channel=output_channel)
    #                 if not self.lakeshore.stabilize_temperature(target_temp, channel=input_channel):
    #                     QMessageBox.warning(self, "Warning", "Temperature not stabilized.")
    #                     return

    #             source_type = self.k2450_source_select.currentText()
    #             measure_type = self.k2450_measure_select.currentText()
    #             start_val = float(self.k2450_start_input.text())
    #             stop_val = float(self.k2450_stop_input.text())
    #             steps = int(self.k2450_steps_input.text())
    #             compliance = float(self.k2450_compliance_input.text())
    #             cycles = int(self.cycles_input.text())

    #             self.keithley2450.configure_smu(
    #                 source_type=source_type,
    #                 source_value=start_val,
    #                 current_limit=compliance
    #             )

    #             x_vals, y_vals = [], []

    #             for cycle in range(cycles):
    #                 x_cycle, y_cycle = self.keithley2450.sweep(
    #                     source_type=source_type,
    #                     measure_type=measure_type,
    #                     start=start_val,
    #                     stop=stop_val,
    #                     steps=steps,
    #                     delay=0.1
    #                 )
    #                 x_vals.extend(x_cycle)
    #                 y_vals.extend(y_cycle)

    #                 self.plot_data(
    #                     x_vals, y_vals,
    #                     x_label=source_type,
    #                     y_label=measure_type,
    #                     title=f"Keithley 2450 Sweep (Cycle {cycle + 1})"
    #                 )
    #                 QApplication.processEvents()

    #     except Exception as e:
    #         QMessageBox.critical(self, "Error", f"Sweep Failed:\n{e}")

    def start_sweep(self):
        experiment = self.experiment_select.currentText()
        selected = [name for name,
                    cb in self.instrument_checkboxes.items() if cb.isChecked()]
        self.stop_requested = False

        try:
            if experiment == "IV Sweep":
                self.run_iv_sweep(selected)

            elif experiment == "IV Sweep 2450":
                self.run_iv_sweep(selected)

            elif experiment == "Pulse IV Sweep":
                self.run_pulse_iv_2636b()

            elif experiment == "AC Signal Measurement":
                self.start_ac_signal_measurement()  # Lock-in only

            elif experiment == "AC I-V Measurement (2636B)":
                self.run_ac_iv_2636b()

            elif experiment == "AC I-V Measurement (2450)":
                self.run_ac_iv_2450()

            elif experiment == "Temperature Dependent AC I-V (2636B)":
                self.run_temp_ac_iv_2636b()

            elif experiment == "Temperature Dependent AC I-V (2450)":
                self.run_temp_ac_iv_2450()
            elif experiment == "Frequency Sweep":
                self.run_lockin_frequency_sweep()
            elif experiment == "Impedance vs Time":
                self.run_impedance_vs_time()
            elif experiment == "Time Logging":
                self.start_time_logging()
            elif experiment == "AC I-V Measurement (Lock-in Only)":
                self.run_ac_iv_lockin_only()

            else:
                QMessageBox.information(
                    self, "Experiment", "Please select a valid experiment.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Experiment failed:\n{e}")

    def run_iv_sweep(self, selected):
        # --- Temperature stabilization if LakeShore is selected ---
        if "LakeShore" in selected:
            try:
                target_temp = float(self.temp_input.text())
                output_channel = int(self.output_channel_select.currentText())
                input_channel = self.input_channel_select.currentText()

                self.lakeshore.set_temperature(
                    target_temp, channel=output_channel)
                if not self.lakeshore.stabilize_temperature(target_temp, channel=input_channel):
                    QMessageBox.warning(
                        self, "Warning", "Temperature not stabilized.")
                    return
            except Exception as e:
                QMessageBox.critical(self, "LakeShore Error", str(e))
                return

        # --- Keithley 2636B Sweep ---
        if "Keithley" in selected:
            channel = self.channel_select.currentText().lower()
            probe_mode = self.probe_mode_select.currentText()
            source_type = self.source_select.currentText()
            measure_type = self.measure_select.currentText()
            delay = float(self.delay_input.text())

            self.keithley.configure_smu(
                source_type=source_type,
                source_value=0,
                current_limit=0.1,
                source_delay=delay
            )

            if probe_mode == "4-Probe":
                self.keithley.smu.write(
                    f"smu{channel}.sense = smu{channel}.SENSE_REMOTE")
            else:
                self.keithley.smu.write(
                    f"smu{channel}.sense = smu{channel}.SENSE_LOCAL")

            start_v = float(self.start_v_input.text())
            stop_v = float(self.stop_v_input.text())
            steps = int(self.steps_input.text())
            cycles = int(self.cycles_input.text())

            x_vals, y_vals = [], []

            for cycle in range(cycles):
                for val in np.linspace(start_v, stop_v, steps):
                    if self.stop_requested:
                        self.status_label.setText("Sweep stopped.")
                        return

                    if source_type == "Voltage":
                        self.keithley.smu.write(
                            f"smu{channel}.source.levelv = {val}")
                    elif source_type == "Current":
                        self.keithley.smu.write(
                            f"smu{channel}.source.leveli = {val}")

                    self.keithley.smu.write(
                        f"smu{channel}.source.output = smu{channel}.OUTPUT_ON")
                    time.sleep(0.05)
                    measured = self.keithley.measure(measure_type)
                    x_vals.append(val)
                    y_vals.append(measured)

                    self.plot_data(
                        x_vals, y_vals,
                        x_label=source_type,
                        y_label=measure_type,
                        title=f"Keithley 2636B: {measure_type} vs {source_type} (Cycle {cycle + 1})"
                    )
                    QApplication.processEvents()

            self.keithley.smu.write(
                f"smu{channel}.source.output = smu{channel}.OUTPUT_OFF")
            self.stream_data = (x_vals, y_vals)
        # --- Keithley 2450 Sweep ---
        if "Keithley2450" in selected:
            source_type = self.k2450_source_select.currentText()
            measure_type = self.k2450_measure_select.currentText()
            start_val = float(self.k2450_start_input.text())
            stop_val = float(self.k2450_stop_input.text())
            steps = int(self.k2450_steps_input.text())
            compliance = float(self.k2450_compliance_input.text())
            # cycles = int(self.cycles_input.text())
            cycles = int(self.k2450_cycles_input.text())

            self.keithley2450.configure_smu(
                source_type=source_type,
                source_value=start_val,
                current_limit=compliance
            )

            x_vals, y_vals = [], []

            for cycle in range(cycles):
                if self.stop_requested:
                    self.status_label.setText("Sweep stopped.")
                    return

                x_cycle, y_cycle = self.keithley2450.sweep(
                    source_type=source_type,
                    measure_type=measure_type,
                    start=start_val,
                    stop=stop_val,
                    steps=steps,
                    delay=0.1
                )
                # x_vals.extend(x_cycle)
                # y_vals.extend(y_cycle)

                x_vals.extend(x_cycle)
                y_vals.extend(y_cycle)

                if self.dual_sweep_checkbox_2450.isChecked():
                    x_rev, y_rev = self.keithley2450.sweep(
                        source_type=source_type,
                        measure_type=measure_type,
                        start=stop_val,
                        stop=start_val,
                        steps=steps,
                        delay=0.1
                    )
                    x_vals.extend(x_rev)
                    y_vals.extend(y_rev)
                self.plot_data(
                    x_vals, y_vals,
                    x_label=source_type,
                    y_label=measure_type,
                    title=f"Keithley 2450 Sweep (Cycle {cycle + 1})"
                )
                QApplication.processEvents()
                self.stream_data = (x_vals, y_vals)

    def run_ac_iv_lockin_only(self):
        try:
            self.configure_lockin()

            start = float(self.ac_start_input.text())
            stop = float(self.ac_stop_input.text())
            steps = int(self.ac_steps_input.text())
            output_mode = self.lockin_output_mode.currentText()

            voltages = np.linspace(start, stop, steps)
            x_vals, y1_vals, y2_vals = [], [], []

            for v in voltages:
                if self.stop_requested:
                    self.status_label.setText("AC IV sweep stopped.")
                    return

                # ✅ You'll need to implement this in SR830Controller
                self.lockin.set_offset_voltage(v)
                time.sleep(0.3)

                if output_mode == "X/Y":
                    x, y = self.lockin.read_xy()
                    y1_vals.append(x)
                    y2_vals.append(y)
                else:
                    r, theta = self.lockin.read_rtheta()
                    y1_vals.append(r)
                    y2_vals.append(theta)
                x_vals.append(v)

            if output_mode == "X/Y":
                self.plot_dual_data(
                    x_vals, y1_vals, y2_vals, "V (Lock-in Offset)", "X (V)", "Y (V)", "AC I-V (Lock-in Only)")
            else:
                self.plot_dual_data(
                    x_vals, y1_vals, y2_vals, "V (Lock-in Offset)", "R (V)", "θ (°)", "AC I-V (Lock-in Only)")

            self.status_label.setText("AC IV with Lock-in completed.")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"AC IV Lock-in only failed:\n{e}")

    def run_ac_iv_2636b(self):
        try:
            self.configure_lockin()
            self.configure_keithley_2636b()
            start = float(self.ac_start_input.text())
            stop = float(self.ac_stop_input.text())
            steps = int(self.ac_steps_input.text())
            source_type = self.ac_source_type.currentText()
            output_mode = self.lockin_output_mode.currentText()

            voltages = np.linspace(start, stop, steps)
            x_vals, y1_vals, y2_vals = [], [], []

            for v in voltages:
                if self.stop_requested:
                    self.status_label.setText("AC IV sweep stopped.")
                    return
                self.keithley2636b.set_source_value(source_type, v)
                time.sleep(0.3)
                if output_mode == "X/Y":
                    x, y = self.lockin.read_xy()
                    y1_vals.append(x)
                    y2_vals.append(y)
                else:
                    r, theta = self.lockin.read_rtheta()
                    y1_vals.append(r)
                    y2_vals.append(theta)
                x_vals.append(v)

            if output_mode == "X/Y":
                self.plot_dual_data(
                    x_vals, y1_vals, y2_vals, "Voltage (V)", "X (V)", "Y (V)", "AC I-V Sweep (X/Y)")
            else:
                self.plot_dual_data(
                    x_vals, y1_vals, y2_vals, "Voltage (V)", "R (V)", "θ (°)", "AC I-V Sweep (R/θ)")

            self.status_label.setText("AC I-V measurement complete.")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"AC IV measurement failed:\n{e}")

    def run_ac_iv_2450(self):
        try:
            self.configure_lockin()
            self.configure_keithley_2450()
            start = float(self.ac_start_input.text())
            stop = float(self.ac_stop_input.text())
            steps = int(self.ac_steps_input.text())
            source_type = self.ac_source_type.currentText()
            output_mode = self.lockin_output_mode.currentText()

            voltages = np.linspace(start, stop, steps)
            x_vals, y1_vals, y2_vals = [], [], []

            for v in voltages:
                if self.stop_requested:
                    self.status_label.setText("AC IV sweep stopped.")
                    return
                self.keithley2450.set_source_value(source_type, v)
                time.sleep(0.3)
                if output_mode == "X/Y":
                    x, y = self.lockin.read_xy()
                    y1_vals.append(x)
                    y2_vals.append(y)
                else:
                    r, theta = self.lockin.read_rtheta()
                    y1_vals.append(r)
                    y2_vals.append(theta)
                x_vals.append(v)

            if output_mode == "X/Y":
                self.plot_dual_data(
                    x_vals, y1_vals, y2_vals, "Voltage (V)", "X (V)", "Y (V)", "AC I-V Sweep (X/Y)")
            else:
                self.plot_dual_data(
                    x_vals, y1_vals, y2_vals, "Voltage (V)", "R (V)", "θ (°)", "AC I-V Sweep (R/θ)")

            self.status_label.setText("AC I-V measurement complete.")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"AC IV measurement failed:\n{e}")

    def run_temp_ac_iv_2636b(self):
        try:
            # Stabilize temperature
            target_temp = float(self.temp_input.text())
            output_channel = int(self.output_channel_select.currentText())
            input_channel = self.input_channel_select.currentText()

            self.lakeshore.set_temperature(target_temp, channel=output_channel)
            if not self.lakeshore.stabilize_temperature(target_temp, channel=input_channel):
                QMessageBox.warning(
                    self, "Warning", "Temperature not stabilized.")
                return

            # Then perform AC IV
            self.run_ac_iv_2636b()

            self.status_label.setText(f"AC I-V completed at {target_temp} °C")

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Temp Dependent AC I-V Failed:\n{e}")

    def run_pulse_iv_2636b(self):
        channel = self.channel_select.currentText().lower()
        source_type = self.source_select.currentText()
        measure_type = self.measure_select.currentText()
        start = float(self.start_v_input.text())
        stop = float(self.stop_v_input.text())
        steps = int(self.steps_input.text())
        compliance = float(self.compliance_input.text())
        pulse_width = 0.01  # seconds
        pulse_delay = 0.1   # seconds

        self.keithley.set_channel(f"smu{channel}")
        x, y = self.keithley.pulse_iv_sweep(
            source_type=source_type,
            measure_type=measure_type,
            start=start,
            stop=stop,
            steps=steps,
            pulse_width=pulse_width,
            pulse_delay=pulse_delay,
            compliance=compliance
        )

        self.plot_data(
            x, y,
            x_label=f"{source_type} Pulse",
            y_label=measure_type,
            title="Pulse IV Sweep"
        )
        self.stream_data = (x, y)

    def run_impedance_vs_time(self):
        try:
            self.configure_lockin()

            source_amplitude = float(self.lockin_amp_input.text())  # V_ac
            output_mode = self.lockin_output_mode.currentText()

            duration = float(self.imp_duration_input.text())  # seconds
            interval = float(self.imp_interval_input.text())  # seconds

            steps = int(duration / interval)

            x_vals, z_vals = [], []

            for i in range(steps):
                if self.stop_requested:
                    self.status_label.setText("Sweep stopped.")
                    return

                t = i * interval
                if output_mode == "X/Y":
                    _, i_measured = self.lockin.read_xy()  # Y = current-like
                else:
                    r, _ = self.lockin.read_rtheta()       # R = magnitude
                    i_measured = r

                # Avoid division by zero
                if abs(i_measured) < 1e-12:
                    impedance = float('inf')
                else:
                    impedance = source_amplitude / i_measured  # Ohm

                x_vals.append(t)
                z_vals.append(impedance)

                time.sleep(interval)

            self.plot_data(
                x_vals, z_vals,
                x_label="Time (s)",
                y_label="Impedance (Ohms)",
                title="Impedance vs Time"
            )
            self.stream_data = (x_vals, z_vals)
            self.status_label.setText(
                "Impedance vs Time measurement complete.")

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Impedance vs Time Failed:\n{e}")

    def run_lockin_frequency_sweep(self):
        try:
            self.configure_lockin()

            start_freq = float(self.lockin_freq_start_input.text())
            stop_freq = float(self.lockin_freq_stop_input.text())
            interval = float(self.lockin_freq_interval_input.text())
            freqs = np.arange(start_freq, stop_freq + interval, interval)
            output_mode = self.lockin_output_mode.currentText()

            x_vals = []
            y1_vals = []  # R or X
            y2_vals = []  # θ or Y (optional)

            for freq in freqs:
                if self.stop_requested:
                    self.status_label.setText("Sweep stopped.")
                    return

                self.lockin.set_reference(
                    freq, float(self.lockin_amp_input.text()))
                time.sleep(0.3)  # allow settling

                if output_mode == "X/Y":
                    x, y = self.lockin.read_xy()
                    y1_vals.append(x)
                    y2_vals.append(y)
                else:  # R/θ
                    r, theta = self.lockin.read_rtheta()
                    y1_vals.append(r)
                    y2_vals.append(theta)

                x_vals.append(freq)

            # Plotting based on mode
            if output_mode == "X/Y":
                self.plot_dual_data(
                    x_vals, y1_vals, y2_vals,
                    x_label="Frequency (Hz)",
                    y1_label="X (V)",
                    y2_label="Y (V)",
                    title="Lock-in Frequency Sweep (X/Y)"
                )
            else:  # R/θ
                self.plot_dual_data(
                    x_vals, y1_vals, y2_vals,
                    x_label="Frequency (Hz)",
                    y1_label="R (V)",
                    y2_label="θ (deg)",
                    title="Lock-in Frequency Sweep (R/θ)"
                )

            self.status_label.setText("Lock-in frequency sweep complete.")
            self.stream_data = (x_vals, y1_vals)

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Frequency sweep failed:\n{e}")

    def plot_dual_data(self, x, y1, y2, x_label, y1_label, y2_label, title):
        self.figure.clear()
        ax1 = self.figure.add_subplot(111)
        ax2 = ax1.twinx()

        ax1.plot(x, y1, 'b-', label=y1_label)
        ax2.plot(x, y2, 'r--', label=y2_label)

        ax1.set_xlabel(x_label)
        ax1.set_ylabel(y1_label, color='b')
        ax2.set_ylabel(y2_label, color='r')
        self.figure.tight_layout()
        self.canvas.draw()

    def run_lockin_harmonic_detection(self):
        try:
            self.configure_lockin()
            base_freq = float(self.lockin_freq_input.text())
            max_harmonic = int(self.lockin_harmonics_input.text())
            harmonics = list(range(1, max_harmonic + 1))

            output_mode = self.lockin_output_mode.currentText()

            x_vals, y_vals = [], []

            for n in harmonics:
                if self.stop_requested:
                    self.status_label.setText("Sweep stopped.")
                    return

                freq = base_freq * n
                self.lockin.set_reference(
                    freq, float(self.lockin_amp_input.text()))
                time.sleep(0.3)
                if output_mode == "X/Y":
                    _, y = self.lockin.read_xy()
                else:
                    r, _ = self.lockin.read_rtheta()
                    y = r
                x_vals.append(n)
                y_vals.append(y)

            self.plot_data(
                x_vals, y_vals,
                x_label="Harmonic Number",
                y_label=f"Lock-in {output_mode.split('/')[1]}",
                title="Harmonic Detection"
            )
            self.stream_data = (x_vals, y_vals)
            self.status_label.setText("Harmonic detection complete.")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Harmonic detection failed:\n{e}")

    # def update_lockin_inputs_visibility(self):
    #     experiment = self.experiment_select.currentText()

    #     is_freq = experiment == "Frequency Sweep"
    #     is_harmonic = experiment == "Harmonic Detection"

    #     self.lockin_freq_start_input.setVisible(is_freq)
    #     self.lockin_freq_stop_input.setVisible(is_freq)
    #     self.lockin_freq_steps_input.setVisible(is_freq)

    #     self.lockin_harmonics_input.setVisible(is_harmonic)
    # def update_lockin_inputs_visibility(self):
    #     is_freq = self.experiment_select.currentText() == "Frequency Sweep"

    #     self.freq_start_layout.setEnabled(is_freq)
    #     self.freq_stop_layout.setEnabled(is_freq)
    #     #self.freq_steps_layout.setEnabled(is_freq)
    #     self.freq_interval_layout.setEnabled(is_freq)
    def update_lockin_inputs_visibility(self):
        experiment = self.experiment_select.currentText()

        is_freq = experiment == "Frequency Sweep"
        is_ac_iv = "AC I-V Measurement" in experiment
        is_impedance = "Impedance vs Time" in experiment

        # Frequency Sweep Inputs
        self.freq_start_layout.setEnabled(is_freq)
        self.freq_stop_layout.setEnabled(is_freq)
        self.freq_interval_layout.setEnabled(is_freq)

        # AC I-V Inputs (Show/Hide container)
        if hasattr(self, 'ac_iv_inputs_widget'):
            self.ac_iv_inputs_widget.setVisible(is_ac_iv)

        # Impedance Inputs (Show/Hide container)
        if hasattr(self, 'impedance_inputs_widget'):
            self.impedance_inputs_widget.setVisible(is_impedance)


# Replace existing time logging method logic with this fixed version:
    # def start_time_logging(self):
    #     selected = [name for name, cb in self.instrument_checkboxes.items() if cb.isChecked()]
    #     self.stream_data = ([], [])  # Reset

    #     try:
    #         # Parse timing inputs
    #         interval_ms = float(self.interval_input.text())
    #         total_time_ms = float(self.total_time_input.text())
    #         interval_sec = interval_ms / 1000.0
    #         total_time_sec = total_time_ms / 1000.0

    #         x_vals, y_vals = [], []
    #         start_time = time.time()
    #         next_time = start_time

    #         # Determine which Keithley to use
    #         if "Keithley" in selected:
    #             channel = self.channel_select.currentText().lower()
    #             self.keithley.set_channel(f"smu{channel}")
    #             source_type = self.source_select.currentText()
    #             measure_type = self.measure_select.currentText()
    #             fixed_value = float(self.fixed_source_input.text())

    #             self.keithley.configure_smu(source_type=source_type, source_value=fixed_value, current_limit=0.1)
    #             self.keithley.output_on()

    #             while True:
    #                 now = time.time()
    #                 if now - start_time >= total_time_sec:
    #                     break

    #                 if now >= next_time:
    #                     elapsed_ms = (now - start_time) * 1000
    #                     value = self.keithley.measure(measure_type)
    #                     x_vals.append(round(elapsed_ms, 1))
    #                     y_vals.append(value)
    #                     next_time += interval_sec

    #                 time.sleep(0.001)

    #             self.keithley.output_off()
    #             title = "Keithley 2636B Time Logging"

    #         elif "Keithley2450" in selected:
    #             source_type = self.k2450_source_select.currentText()
    #             measure_type = self.k2450_measure_select.currentText()
    #             fixed_value = float(self.k2450_start_input.text())

    #             self.keithley2450.configure_smu(source_type=source_type, source_value=fixed_value, current_limit=0.1)
    #             self.keithley2450.smu.write("OUTP ON")

    #             while True:
    #                 now = time.time()
    #                 if now - start_time >= total_time_sec:
    #                     break

    #                 if now >= next_time:
    #                     elapsed_ms = (now - start_time) * 1000
    #                     value = self.keithley2450.measure(measure_type)
    #                     x_vals.append(round(elapsed_ms, 1))
    #                     y_vals.append(value)
    #                     next_time += interval_sec

    #                 time.sleep(0.001)

    #             self.keithley2450.smu.write("OUTP OFF")
    #             title = "Keithley 2450 Time Logging"

    #         # Plot and store results
    #         self.plot_data(
    #             x_vals, y_vals,
    #             x_label="Time (ms)",
    #             y_label=measure_type,
    #             title=title
    #         )
    #         self.status_label.setText(f"{title} complete.")
    #         self.stream_data = (x_vals, y_vals)

    #     except Exception as e:
    #         QMessageBox.critical(self, "Error", f"Time Logging Failed:\n{e}")

    def start_time_logging(self):
        selected = [name for name,
                    cb in self.instrument_checkboxes.items() if cb.isChecked()]
        self.stream_data = ([], [])  # Reset

        try:
            # # Parse total time input only (no interval now)
            # total_time_ms = float(self.total_time_input.text())
            # total_time_sec = total_time_ms / 1000.0

            # x_vals, y_vals = [], []
            # start_time = time.time()
            interval_ms = float(self.interval_input.text())
            total_time_ms = float(self.total_time_input.text())
            interval_sec = interval_ms / 1000.0
            total_time_sec = total_time_ms / 1000.0

            num_points = int(total_time_ms // interval_ms)
            x_vals, y_vals = [], []

            start_time = time.time()
            if "Keithley" in selected:
                channel = self.channel_select.currentText().lower()
                self.keithley.set_channel(f"smu{channel}")
                source_type = self.source_select.currentText()
                measure_type = self.measure_select.currentText()
                fixed_value = float(self.fixed_source_input.text())
                nplc = float(self.nplc_input.text())

                self.keithley.configure_smu(
                    source_type=source_type, source_value=fixed_value, current_limit=0.1, source_delay=0.1, nplc=nplc)
                self.keithley.output_on()

                # while True:
                #     now = time.time()
                #     if now - start_time >= total_time_sec:
                #         break

                #     elapsed_ms = (now - start_time) * 1000
                #     value = self.keithley.measure(measure_type)
                #     x_vals.append(round(elapsed_ms, 1))
                #     y_vals.append(value)

                #     # Optional: prevent CPU overuse
                #     time.sleep(0.001)

                # self.keithley.output_off()
                # title = "Keithley 2636B Time Logging"
                for i in range(num_points):
                    if self.stop_requested:
                        self.status_label.setText("Sweep stopped.")
                        return

                    scheduled_time = start_time + i * interval_sec
                    while time.time() < scheduled_time:
                        time.sleep(0.0005)

                    value = self.keithley.measure(measure_type)
                    x_vals.append(round(i * interval_ms, 1))
                    y_vals.append(value)

                self.keithley.output_off()
                title = "Keithley 2636B Timed Logging"
            elif "Keithley2450" in selected:
                source_type = self.k2450_source_select.currentText()
                measure_type = self.k2450_measure_select.currentText()
                # fixed_value = float(self.k2450_start_input.text())
                # ✅ Correct: uses fixed source
                fixed_value = float(self.k2450_fixed_input.text())
                nplc = float(self.k2450_nplc_input.text())
                self.keithley2450.configure_smu(
                    source_type=source_type, source_value=fixed_value, current_limit=0.1, nplc=nplc)
                self.keithley2450.smu.write("OUTP ON")

                # while True:
                #     now = time.time()
                #     if now - start_time >= total_time_sec:
                #         break

                #     elapsed_ms = (now - start_time) * 1000
                #     value = self.keithley2450.measure(measure_type)
                #     x_vals.append(round(elapsed_ms, 1))
                #     y_vals.append(value)

                #     time.sleep(0.001)

                # self.keithley2450.smu.write("OUTP OFF")
                # title = "Keithley 2450 Time Logging"
                for i in range(num_points):
                    if self.stop_requested:
                        self.status_label.setText("Sweep stopped.")
                        return

                    scheduled_time = start_time + i * interval_sec
                    while time.time() < scheduled_time:
                        time.sleep(0.0005)

                    value = self.keithley2450.measure(measure_type)
                    x_vals.append(round(i * interval_ms, 1))
                    y_vals.append(value)

                self.keithley2450.smu.write("OUTP OFF")
                title = "Keithley 2450 Timed Logging"
            # Plot and store results
            self.plot_data(
                x_vals, y_vals,
                x_label="Time (ms)",
                y_label=measure_type,
                title=title
            )
            self.status_label.setText(f"{title} complete.")
            self.stream_data = (x_vals, y_vals)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Time Logging Failed:\n{e}")
    # def start_time_logging(self):
    #     selected = [name for name, cb in self.instrument_checkboxes.items() if cb.isChecked()]
    #     self.stream_data = ([], [])

    #     try:
    #         interval_ms = float(self.interval_input.text())
    #         total_time_ms = float(self.total_time_input.text())
    #         interval_sec = interval_ms / 1000.0
    #         total_time_sec = total_time_ms / 1000.0

    #         x_vals, y_vals = [], []
    #         start_time = time.time()
    #         next_time = start_time

    #         if "Keithley" in selected:
    #             channel = self.channel_select.currentText().lower()
    #             self.keithley.set_channel(f"smu{channel}")
    #             source_type = self.source_select.currentText()
    #             measure_type = self.measure_select.currentText()
    #             fixed_value = float(self.fixed_source_input.text())

    #             self.keithley.configure_smu(source_type=source_type, source_value=fixed_value, current_limit=0.1)
    #             self.keithley.output_on()

    #             while True:
    #                 now = time.time()
    #                 elapsed = now - start_time
    #                 if elapsed >= total_time_sec:
    #                     break

    #                 if now >= next_time:
    #                     value = self.keithley.measure(measure_type)
    #                     elapsed_ms = round((now - start_time) * 1000, 1)
    #                     x_vals.append(elapsed_ms)
    #                     y_vals.append(value)
    #                     next_time += interval_sec

    #                 time.sleep(0.0005)

    #             self.keithley.output_off()
    #             title = "Keithley 2636B Logging"

    #         elif "Keithley2450" in selected:
    #             source_type = self.k2450_source_select.currentText()
    #             measure_type = self.k2450_measure_select.currentText()
    #             fixed_value = float(self.k2450_start_input.text())

    #             self.keithley2450.configure_smu(source_type=source_type, source_value=fixed_value, current_limit=0.1)
    #             self.keithley2450.smu.write("OUTP ON")

    #             while True:
    #                 now = time.time()
    #                 elapsed = now - start_time
    #                 if elapsed >= total_time_sec:
    #                     break

    #                 if now >= next_time:
    #                     value = self.keithley2450.measure(measure_type)
    #                     elapsed_ms = round((now - start_time) * 1000, 1)
    #                     x_vals.append(elapsed_ms)
    #                     y_vals.append(value)
    #                     next_time += interval_sec

    #                 time.sleep(0.0005)

    #             self.keithley2450.smu.write("OUTP OFF")
    #             title = "Keithley 2450 Logging"

    #         # Plot and store results
    #         self.plot_data(
    #             x_vals, y_vals,
    #             x_label="Time (ms)",
    #             y_label=measure_type,
    #             title=title
    #         )
    #         self.status_label.setText(f"{title} complete.")
    #         self.stream_data = (x_vals, y_vals)

    #     except Exception as e:
    #         QMessageBox.critical(self, "Error", f"Time Logging Failed:\n{e}")
    # def start_time_logging(self):
    #     selected = [name for name, cb in self.instrument_checkboxes.items() if cb.isChecked()]
    #     self.stream_data = ([], [])

    #     try:
    #         interval_ms = float(self.interval_input.text())
    #         total_time_ms = float(self.total_time_input.text())
    #         interval_sec = interval_ms / 1000.0
    #         total_time_sec = total_time_ms / 1000.0

    #         x_vals, y_vals = [], []
    #         start_time = time.time()
    #         next_time = start_time

    #         if "Keithley" in selected:
    #             channel = self.channel_select.currentText().lower()
    #             self.keithley.set_channel(f"smu{channel}")
    #             source_type = self.source_select.currentText()
    #             measure_type = self.measure_select.currentText()
    #             fixed_value = float(self.fixed_source_input.text())

    #             self.keithley.configure_smu(source_type=source_type, source_value=fixed_value, current_limit=0.1)
    #             self.keithley.output_on()

    #             while True:
    #                 now = time.time()
    #                 elapsed = now - start_time
    #                 if elapsed >= total_time_sec:
    #                     break

    #                 if now >= next_time:
    #                     value = self.keithley.measure(measure_type)
    #                     elapsed_ms = round((now - start_time) * 1000, 1)
    #                     x_vals.append(elapsed_ms)
    #                     y_vals.append(value)
    #                     next_time += interval_sec

    #                 time.sleep(0.0005)

    #             self.keithley.output_off()
    #             title = "Keithley 2636B Logging"

    #         elif "Keithley2450" in selected:
    #             source_type = self.k2450_source_select.currentText()
    #             measure_type = self.k2450_measure_select.currentText()
    #             fixed_value = float(self.k2450_start_input.text())

    #             self.keithley2450.configure_smu(source_type=source_type, source_value=fixed_value, current_limit=0.1)
    #             self.keithley2450.smu.write("OUTP ON")

    #             while True:
    #                 now = time.time()
    #                 elapsed = now - start_time
    #                 if elapsed >= total_time_sec:
    #                     break

    #                 if now >= next_time:
    #                     value = self.keithley2450.measure(measure_type)
    #                     elapsed_ms = round((now - start_time) * 1000, 1)
    #                     x_vals.append(elapsed_ms)
    #                     y_vals.append(value)
    #                     next_time += interval_sec

    #                 time.sleep(0.0005)

    #             self.keithley2450.smu.write("OUTP OFF")
    #             title = "Keithley 2450 Logging"

    #         # Plot and store results
    #         self.plot_data(
    #             x_vals, y_vals,
    #             x_label="Time (ms)",
    #             y_label=measure_type,
    #             title=title
    #         )
    #         self.status_label.setText(f"{title} complete.")
    #         self.stream_data = (x_vals, y_vals)

    #     except Exception as e:
    #         QMessageBox.critical(self, "Error", f"Time Logging Failed:\n{e}")
    def update_temperature_display(self):
        try:
            if self.use_temp_checkbox.isChecked():
                input_channel = self.input_channel_select.currentText()
                current_temp = self.lakeshore.get_temperature(
                    channel=input_channel)
                self.live_temp_label.setText(
                    f"Current Temperature: {current_temp:.2f} °C")
            else:
                self.live_temp_label.setText("Temperature Control Disabled")
        except Exception:
            self.live_temp_label.setText("Current Temperature: -- °C")

    def update_temperature_display(self):
        try:
            if hasattr(self, "use_temp_checkbox") and self.use_temp_checkbox.isChecked():
                input_channel = self.input_channel_select.currentText()
                current_temp = self.lakeshore.get_temperature(
                    channel=input_channel)
                self.live_temp_label.setText(
                    f"Current Temperature: {current_temp:.2f} °C")
            elif self.lakeshore325_controls.isVisible():
                input_channel = int(
                    self.l325_input_channel_select.currentText())
                current_temp = self.lakeshore325.get_temperature(
                    input_channel=input_channel)
                self.l325_live_temp_label.setText(
                    f"Current Temperature: {current_temp:.2f} °C")
            else:
                self.live_temp_label.setText("Temperature Control Disabled")
                self.l325_live_temp_label.setText(
                    "Temperature Control Disabled")
        except Exception:
            self.live_temp_label.setText("Current Temperature: -- °C")
            self.l325_live_temp_label.setText("Current Temperature: -- °C")

    def plot_data(self, x_data, y_data, x_label="X", y_label="Y", title="Measurement Plot"):
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        line, = self.ax.plot(x_data, y_data, 'b-')

        cursor = mplcursors.cursor(line, hover=True)
        cursor.connect("add", lambda sel: sel.annotation.set_text(
            f"x: {sel.target[0]:.3f}\ny: {sel.target[1]:.3e}"))

        self.ax.set_xlabel(x_label)
        self.ax.set_ylabel(y_label)
        self.ax.set_title(title)
        self.ax.grid(True)

        if self.log_x_checkbox.isChecked():
            self.ax.set_xscale('log')
        if self.log_y_checkbox.isChecked():
            self.ax.set_yscale('log')

        self.canvas.draw()

    def start_ac_signal_measurement(self):
        try:
            self.configure_lockin()
            duration = float(self.lockin_duration_input.text())
            interval = float(self.lockin_interval_input.text())
            output_mode = self.lockin_output_mode.currentText()

            timestamps = []
            y1_vals, y2_vals = [], []
            start_time = time.time()

            while time.time() - start_time < duration:
                if self.stop_requested:
                    self.status_label.setText("AC signal measurement stopped.")
                    return
                t = time.time() - start_time
                if output_mode == "X/Y":
                    x, y = self.lockin.read_xy()
                    y1_vals.append(x)
                    y2_vals.append(y)
                else:
                    r, theta = self.lockin.read_rtheta()
                    y1_vals.append(r)
                    y2_vals.append(theta)
                timestamps.append(t)
                time.sleep(interval)

            if output_mode == "X/Y":
                self.plot_dual_data(timestamps, y1_vals, y2_vals, "Time (s)",
                                    "X (V)", "Y (V)", "Lock-in AC Signal (X/Y)")
            else:
                self.plot_dual_data(timestamps, y1_vals, y2_vals, "Time (s)",
                                    "R (V)", "θ (°)", "Lock-in AC Signal (R/θ)")

            self.status_label.setText("AC signal measurement complete.")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"AC signal measurement failed:\n{e}")

    def run_lockin_harmonic_detection(self):
        try:
            self.configure_lockin()
            base_freq = float(self.lockin_freq_input.text())
            harmonics = [1, 2, 3, 4, 5]  # 1st to 5th harmonic
            output_mode = self.lockin_output_mode.currentText()

            x_vals, y_vals = [], []

            for n in harmonics:
                freq = base_freq * n
                self.lockin.set_reference(
                    freq, float(self.lockin_amp_input.text()))
                time.sleep(0.3)
                if output_mode == "X/Y":
                    _, y = self.lockin.read_xy()
                else:
                    r, _ = self.lockin.read_rtheta()
                    y = r
                x_vals.append(n)
                y_vals.append(y)

            self.plot_data(
                x_vals, y_vals,
                x_label="Harmonic Number",
                y_label=f"Lock-in {output_mode.split('/')[1]}",
                title="Harmonic Detection"
            )
            self.stream_data = (x_vals, y_vals)
            self.status_label.setText("Harmonic detection complete.")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Harmonic detection failed:\n{e}")

    def get_unit_scale(self):
        unit = self.y_unit_select.currentText()
        scale_dict = {
            "A": 1,
            "µA": 1e6,
            "nA": 1e9,
            "pA": 1e12,
            "fA": 1e15
        }
        return scale_dict.get(unit, 1), f"Current ({unit})"

    def clear_plot(self):
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.grid(True)
        self.canvas.draw()

    def save_plot(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", "", "PNG Files (*.png);;All Files (*)", options=options
        )
        if file_name:
            self.figure.savefig(file_name)
            QMessageBox.information(
                self, "Saved", f"Plot saved to:\n{file_name}")

    def save_csv(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Data", "", "CSV Files (*.csv);;All Files (*)", options=options
        )
        if file_name:
            try:
                with open(file_name, 'w') as f:
                    f.write("X,Y\n")
                    for x, y in zip(self.stream_data[0], self.stream_data[1]):
                        f.write(f"{x},{y}\n")
                QMessageBox.information(
                    self, "Saved", f"Data saved to:\n{file_name}")
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to save CSV:\n{e}")

    def closeEvent(self, event):
        self.keithley.disconnect()
        self.lakeshore.disconnect()
        self.keithley2450.disconnect()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = InstrumentControlGUI()
    gui.resize(1000, 700)
    gui.show()
    sys.exit(app.exec_())
