import pyvisa as visa
import time

# or use PySide2.QtWidgets if you use PySide2
from PyQt5.QtWidgets import QMessageBox


class LakeShoreController335:
    def __init__(self):
        """Initialize the LakeShore Temperature Controller."""
        self.rm = visa.ResourceManager(
        )  # resourcemanager identifies which instrument is to be connected and how self.lakeshore = None #gpib-general purpose interface bus
        self.lakeshore = None
        self.address = None

    def connect(self, address=None):
        """Connect to the LakeShore controller."""

        try:
            resources = self.rm.list_resources()
            print(f"Available instruments: {resources}")

            if not resources:
                print("No VISA instruments found.")
                return False

            if address is None:  # checks if user havent given address, if not will pick the first insturment
                self.lakeshore = self.rm.open_resource(resources[0])
            else:
                self.lakeshore = self.rm.open_resource(
                    address)  # if mentioned, will pick that

            self.address = self.lakeshore.resource_name
            # query is giving command for writing and reading, IDN it is a std command for programmable instruments, thus it gives the details of the instrument like its model no. etc.
            idn = self.lakeshore.query("*IDN?")
            # IDN asks lakeshore who it is and store in idn
            print(f"Connected to: {idn.strip()}")
            return True
        except Exception as e:
            # if not connected, it wil show connection error as no insturment found
            print(f"Connection error: {e}")
            return False

    # channel 1,2 are control loop o/p channels-o/p channels control temperature like heater, used to set temperature
    def set_temperature(self, temp_celsius, channel=1):
        """Set the target temperature (°C) on a control loop channel."""
        if not self.lakeshore:
            print("LakeShore not connected!")
            return False

        try:
            temp_kelvin = temp_celsius + 273.15
            # set channel 1 to this temperature-the format is SET <channel>,<value>
            self.lakeshore.write(f"SETP {channel},{temp_kelvin:.3f}")
            print(f"Temperature set to {temp_celsius}°C on channel {channel}")
            return True
        except Exception as e:
            print(f"Set temperature error: {e}")
            return False

    # channel A,B is the i/p sensor channel, it reads the temperauture from sensor
    def get_temperature(self, channel='A'):
        """Read the current temperature from sensor channel."""
        if not self.lakeshore:
            print("LakeShore not connected!")
            return None

        try:
            # KRDG it asks whats the reading temperature in channel 1
            temp_kelvin = float(self.lakeshore.query(f"KRDG? {channel}"))
            return temp_kelvin - 273.15
        except Exception as e:
            print(f"Read temperature error: {e}")
            return None

    def stabilize_temperature(self, target_temp, tolerance=0.1, timeout=300, channel='A'):
        """Wait until the temperature stabilizes around the target value."""
        start_time = time.time()
        while True:
            current_temp = self.get_temperature(channel)
            if current_temp is None:
                return False

            if abs(current_temp - target_temp) <= tolerance:
                print(f"Stabilized at {current_temp:.2f}°C")
                return True

            if time.time() - start_time > timeout:
                print(f"Timeout: Could not stabilize at {target_temp}°C")
                return False

            time.sleep(1)

    def set_l335_heater_range(self):
        try:
            range_code = self.l335_heater_range_select.currentIndex()
            self.lakeshore335.set_heater_range(range_code=range_code)
            QMessageBox.information(
                self, "Heater Range", f"Heater range set to {range_code}")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to set heater range: {e}")

    def set_heater_on(self):
        if self.lakeshore:
            # Example command, adjust if needed
            self.lakeshore.write("OUTMODE 1,1,0")

    def set_heater_off(self):
        if self.lakeshore:
            # Example command, adjust if needed
            self.lakeshore.write("OUTMODE 1,0,0")

    def set_l335_pid(self):
        try:
            p = float(self.l335_pid_p.text())
            i = float(self.l335_pid_i.text())
            d = float(self.l335_pid_d.text())
            self.lakeshore335.set_pid(p, i, d)
            QMessageBox.information(
                self, "PID", f"PID set to P={p}, I={i}, D={d}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to set PID: {e}")

    def set_l335_manual_heater(self):
        try:
            percent = float(self.l335_manual_heater_input.text())
            self.lakeshore335.set_manual_heater_output(percent)
            QMessageBox.information(
                self, "Manual Heater", f"Manual heater output set to {percent}%")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to set manual heater output: {e}")

    def set_l335_excitation(self):
        try:
            enable = self.l335_excitation_checkbox.isChecked()
            self.lakeshore335.enable_excitation_reversal(enable)
            QMessageBox.information(
                self, "Excitation Reversal", f"Excitation reversal {'enabled' if enable else 'disabled'}")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to set excitation reversal: {e}")

    def set_l335_alarm(self):
        try:
            threshold = float(self.l335_alarm_input.text())
            self.lakeshore335.set_alarm_threshold(threshold)
            QMessageBox.information(
                self, "Alarm", f"Alarm threshold set to {threshold}")
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to set alarm threshold: {e}")

    def disconnect(self):
        """Disconnect the LakeShore controller."""
        if self.lakeshore:
            self.lakeshore.close()
            print("LakeShore controller disconnected.")
