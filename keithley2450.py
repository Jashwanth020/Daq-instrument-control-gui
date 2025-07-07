import pyvisa
import time
import numpy as np
import matplotlib.pyplot as plt


class Keithley2450:
    def __init__(self):
        self.rm = pyvisa.ResourceManager()
        self.smu = None
        self.voltage_data = []
        self.current_data = []
        self.address = None

    def connect(self, address=None):
        try:
            resources = self.rm.list_resources()
            if not resources:
                raise ValueError("No instruments found!")
            address = address if address else resources[0]
            self.smu = self.rm.open_resource(address)
            self.smu.timeout = 5000
            self.address = address
            print(f"Connected to: {self.smu.query('*IDN?')}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def configure_smu(self, source_type="Voltage", source_value=0.0, current_limit=0.01, nplc=1):
        try:
            self.smu.write("*RST")
            time.sleep(1)
            if source_type == "Voltage":
                self.smu.write("SOUR:FUNC VOLT")
                self.smu.write(f"SOUR:VOLT {source_value}")
                self.smu.write(f"SENS:CURR:PROT {current_limit}")
                self.smu.write("SENS:FUNC \"CURR\"")
                self.smu.write(f"SENS:CURR:NPLC {nplc}")
            elif source_type == "Current":
                self.smu.write("SOUR:FUNC CURR")
                self.smu.write(f"SOUR:CURR {source_value}")
                self.smu.write(f"SENS:VOLT:PROT {current_limit}")
                self.smu.write("SENS:FUNC \"VOLT\"")
                self.smu.write(f"SENS:VOLT:NPLC {nplc}")
            else:
                raise ValueError(
                    "Invalid source type. Choose 'Voltage' or 'Current'.")
            print(f"Keithley 2450 configured for {source_type} sourcing.")
            return True
        except Exception as e:
            print(f"Configuration error: {e}")
            return False

    def measure(self, measure_type="Current"):
        try:
            if measure_type == "Current":
                return float(self.smu.query("MEAS:CURR?"))
            elif measure_type == "Voltage":
                return float(self.smu.query("MEAS:VOLT?"))
            elif measure_type == "Resistance":
                return float(self.smu.query("MEAS:RES?"))
            else:
                raise ValueError("Invalid measure_type")
        except Exception as e:
            print(f"Measurement error: {e}")
            return None

    def sweep(self, source_type="Voltage", measure_type="Current", start=0, stop=1, steps=20, delay=0.1):
        x_values = np.linspace(start, stop, steps)
        y_values = []
        try:
            self.smu.write(":OUTP ON")
            for val in x_values:
                if source_type == "Voltage":
                    self.smu.write(f"SOUR:VOLT {val}")
                elif source_type == "Current":
                    self.smu.write(f"SOUR:CURR {val}")
                time.sleep(delay)
                y = self.measure(measure_type)
                y_values.append(y)
                print(f"{source_type}: {val:.3f} -> {measure_type}: {y:.4e}")
            self.smu.write(":OUTP OFF")
        except Exception as e:
            print(f"Sweep error: {e}")
        return x_values, y_values

    def disconnect(self):
        if self.smu:
            self.smu.write(":OUTP OFF")
            self.smu.close()
            print("Keithley 2450 disconnected.")


if __name__ == "__main__":
    keithley = Keithley2450()
    if keithley.connect():
        keithley.configure_smu(source_type="Voltage",
                               source_value=0.0, current_limit=0.01)
        x, y = keithley.sweep(source_type="Voltage",
                              measure_type="Current", start=0, stop=1, steps=20)
        plt.plot(x, y, 'o-')
        plt.xlabel("Voltage (V)")
        plt.ylabel("Current (A)")
        plt.title("I-V Curve: Keithley 2450")
        plt.grid(True)
        plt.show()
        keithley.disconnect()
