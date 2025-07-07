import pyvisa as visa
import time
import numpy as np
import matplotlib.pyplot as plt


class Keithley2636B:
    def __init__(self):
        self.rm = visa.ResourceManager()
        self.smu = None
        self.channel = "smua"
        self.voltage_data = []
        self.current_data = []
        self.address = None

    def connect(self, address=None):
        """Connect to the Keithley 2636B."""
        try:
            resources = self.rm.list_resources()
            if not resources:
                raise ValueError("No instruments found!")
            address = address if address else resources[0]
            self.smu = self.rm.open_resource(address)
            self.smu.timeout = 5000
            self.address = address

            self.smu.write(":SYST:COMM:SER:PROT TSP")
            self.smu.write("reset()")
            time.sleep(1)

            # self.address = address
            # print(f"Connected to: {self.smu.query('*IDN?')}")
            idn_response = self.smu.query("*IDN?").strip()
            time.sleep(0.5)
            self.smu.flush(visa.constants.VI_READ_BUF_DISCARD)
            print(f"Connected to: {idn_response}")
            time.sleep(0.5)
            # clear read buffer
            self.smu.flush(visa.constants.VI_READ_BUF_DISCARD)
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def set_channel(self, channel_name):
        if channel_name.lower() in ["smua", "smub"]:
            self.channel = channel_name.lower()
        else:
            raise ValueError("Invalid channel. Choose 'smua' or 'smub'")

    def configure_smu(self, source_type="Voltage", source_value=0, current_limit=0.1, source_delay=0.1, nplc=1):
        """Configure the SMU for voltage or current sourcing."""
        if not self.smu:
            raise RuntimeError("Keithley not connected!")

        try:
            self.smu.write("*RST")
            time.sleep(1)
            self.smu.write(f"{self.channel}.source.delay = {source_delay}")

            if source_type == "Voltage":
                self.smu.write(
                    f"{self.channel}.source.func = {self.channel}.OUTPUT_DCVOLTS")
                self.smu.write(
                    f"{self.channel}.source.levelv = {source_value}")
                self.smu.write(
                    f"{self.channel}.source.limiti = {current_limit}")
                self.smu.write(
                    f"{self.channel}.measure.autorangei = {self.channel}.AUTORANGE_ON")
                self.smu.write(f"{self.channel}.measure.nplc = {nplc}")
            elif source_type == "Current":
                self.smu.write(
                    f"{self.channel}.source.func = {self.channel}.OUTPUT_DCAMPS")
                self.smu.write(
                    f"{self.channel}.source.leveli = {source_value}")
                self.smu.write(
                    f"{self.channel}.source.limitv = {current_limit}")
                self.smu.write(
                    f"{self.channel}.measure.autorangev = {self.channel}.AUTORANGE_ON")
                self.smu.write(f"{self.channel}.measure.nplc = {nplc}")
            else:
                raise ValueError(
                    "Invalid source type. Choose 'Voltage' or 'Current'.")

            print(f"Keithley configured for {source_type} sourcing.")
            return True
        except Exception as e:
            print(f"Configuration error: {e}")
            return False

    # def measure(self, measure_type="Current"):
    #     """Generic measurement method."""
    #     if measure_type == "Current":
    #         return float(self.smu.query(f"print({self.channel}.measure.i())"))
    #     elif measure_type == "Voltage":
    #         return float(self.smu.query(f"print({self.channel}.measure.v())"))
    #     elif measure_type == "Resistance":
    #         return float(self.smu.query(f"print({self.channel}.measure.r())"))
    #     else:
    #         raise ValueError("Invalid measure_type")

    # def measure(self, measure_type="Current"):
    #     if not self.smu:
    #         raise RuntimeError("Keithley not connected!")

    #     try:
    #         if measure_type == "Current":
    #             response = self.smu.query(f"print({self.channel}.measure.i())")
    #         elif measure_type == "Voltage":
    #             response = self.smu.query(f"print({self.channel}.measure.v())")
    #         elif measure_type == "Resistance":
    #             response = self.smu.query(f"print({self.channel}.measure.r())")
    #         else:
    #             raise ValueError("Invalid measure_type")

    #         response = response.strip()
    #         print(f"[DEBUG] Response: {repr(response)}")

    #         value=float(response)
    #         return value
    #         # Check if it's a valid float
    #         # if any(keyword in response.lower() for keyword in ["keithley", "model", "inc", ","]):
    #         #     raise ValueError(f"Invalid measurement (probably leftover IDN response): {response}")

    #         # return float(response)

    #     except Exception as e:
    #         raise RuntimeError(f"fail to parce measurment.raw response:'{response}' \nError: {e}") # Let the GUI catch and display the error
    # def measure(self, measure_type="Current"):
    #         if not self.smu:
    #             raise RuntimeError("Keithley not connected!")

    #         try:
    #             self.smu.flush(visa.constants.VI_READ_BUF_DISCARD)
    #             if measure_type == "Current":
    #                 response = self.smu.query(f"print({self.channel}.measure.i())")
    #             elif measure_type == "Voltage":
    #                 response = self.smu.query(f"print({self.channel}.measure.v())")
    #             elif measure_type == "Resistance":
    #                 response = self.smu.query(f"print({self.channel}.measure.r())")
    #             else:
    #                 raise ValueError("Invalid measure_type")

    #             response = response.strip()

    #         # Add stricter float check
    #             try:
    #                 val = float(response)
    #             except ValueError:
    #                 raise ValueError(f"Non-numeric response from instrument: {response}")

    #             print(f"[DEBUG] {measure_type}: {val}")
    #             return val

    #         except Exception as e:
    #             print(f"[ERROR] Measurement failed: {e}")
    #             raise
    def measure(self, measure_type="Current"):
        if not self.smu:
            raise RuntimeError("Keithley not connected!")

        try:
            self.smu.flush(visa.constants.VI_READ_BUF_DISCARD)
            time.sleep(0.3)  # Give Keithley time to clear any garbage

            if measure_type == "Current":
                query_cmd = f"print({self.channel}.measure.i())"
            elif measure_type == "Voltage":
                query_cmd = f"print({self.channel}.measure.v())"
            elif measure_type == "Resistance":
                query_cmd = f"print({self.channel}.measure.r())"
            else:
                raise ValueError("Invalid measure_type")

            for attempt in range(3):
                response = self.smu.query(query_cmd).strip()
                print(
                    f"[DEBUG attempt {attempt+1}] {measure_type} response: {response}")

                # If it's a valid float, return it
                try:
                    return float(response)
                except ValueError:
                    # If it's not a number, flush again and retry
                    if any(k in response.lower() for k in ["keithley", "model", "inc", ","]):
                        self.smu.flush(visa.constants.VI_READ_BUF_DISCARD)
                        time.sleep(0.2)
                        continue
                    raise ValueError(
                        f"Unexpected non-numeric response: {response}")

            raise RuntimeError(
                f"Failed to get numeric response from instrument after 3 tries")

        except Exception as e:
            print(f"[ERROR] Measurement failed: {e}")
            raise

    def output_on(self):
        self.smu.write(
            f"{self.channel}.source.output = {self.channel}.OUTPUT_ON")

    def output_off(self):
        self.smu.write(
            f"{self.channel}.source.output = {self.channel}.OUTPUT_OFF")

    def measure_current(self, voltage, max_attempts=3):
        """Backward-compatible helper to measure current at a specific voltage."""
        if not self.smu:
            raise RuntimeError("Keithley not connected!")

        for attempt in range(max_attempts):
            try:
                self.smu.write(f"{self.channel}.source.levelv = {voltage}")
                self.smu.write(
                    f"{self.channel}.source.output = {self.channel}.OUTPUT_ON")
                time.sleep(0.1)

                current = self.measure("Current")

                self.smu.write(
                    f"{self.channel}.source.output = {self.channel}.OUTPUT_OFF")
                return current
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(1)

        print(f"Failed after {max_attempts} attempts.")
        return None

    def sweep(self, source_type="Voltage", measure_type="Current", start=0, stop=5, steps=50, delay=0.1):
        """Sweep source values and measure response."""
        if not self.smu:
            raise RuntimeError("Keithley not connected!")

        x_values = np.linspace(start, stop, steps)
        y_values = []

        for val in x_values:
            try:
                if source_type == "Voltage":
                    self.smu.write(f"{self.channel}.source.levelv = {val}")
                elif source_type == "Current":
                    self.smu.write(f"{self.channel}.source.leveli = {val}")
                else:
                    raise ValueError("Invalid source type")

                self.smu.write(
                    f"{self.channel}.source.output = {self.channel}.OUTPUT_ON")
                time.sleep(delay)

                measured = self.measure(measure_type)
                y_values.append(measured)
                print(f"{source_type}: {val:.3f} => {measure_type}: {measured:.4e}")

            except Exception as e:
                print(f"Measurement failed at {val:.3f}: {e}")
                y_values.append(None)
            finally:
                self.smu.write(
                    f"{self.channel}.source.output = {self.channel}.OUTPUT_OFF")

        return x_values, y_values

    def sweep_stream(self, source_type="Voltage", measure_type="Current", start=0, stop=5, steps=50, delay=0.1):
        if not self.smu:
            raise RuntimeError("Keithley not connected!")

        x_values = np.linspace(start, stop, steps)
        for val in x_values:
            try:
                if source_type == "Voltage":
                    self.smu.write(f"{self.channel}.source.levelv = {val}")
                elif source_type == "Current":
                    self.smu.write(f"{self.channel}.source.leveli = {val}")
                else:
                    raise ValueError("Invalid source type")

                self.smu.write(
                    f"{self.channel}.source.output = {self.channel}.OUTPUT_ON")
                time.sleep(delay)

                measured = self.measure(measure_type)
                yield val, measured

            except Exception as e:
                print(f"Error at {val}: {e}")
                yield val, None
            finally:
                self.smu.write(
                    f"{self.channel}.source.output = {self.channel}.OUTPUT_OFF")

    def pulse_iv_sweep(self, source_type="Voltage", measure_type="Current",
                       start=0, stop=1, steps=10, pulse_width=0.01, pulse_delay=0.1, compliance=0.1):
        if not self.smu:
            raise RuntimeError("Keithley not connected!")

        self.smu.write("*RST")
        time.sleep(0.5)

        self.smu.write(f"{self.channel}.source.delay = {pulse_delay}")
        self.smu.write(f"{self.channel}.source.pulsetransient = {pulse_delay}")

        if source_type == "Voltage":
            self.smu.write(
                f"{self.channel}.source.func = {self.channel}.OUTPUT_DCVOLTS")
            self.smu.write(f"{self.channel}.source.limiti = {compliance}")
        elif source_type == "Current":
            self.smu.write(
                f"{self.channel}.source.func = {self.channel}.OUTPUT_DCAMPS")
            self.smu.write(f"{self.channel}.source.limitv = {compliance}")
        else:
            raise ValueError("Invalid source_type")

        self.smu.write(f"{self.channel}.source.pulsetransient = {pulse_delay}")
        self.smu.write(
            f"{self.channel}.source.output = {self.channel}.OUTPUT_ON")

        x_vals = np.linspace(start, stop, steps)
        y_vals = []

        for val in x_vals:
            if source_type == "Voltage":
                self.smu.write(f"{self.channel}.source.levelv = {val}")
            else:
                self.smu.write(f"{self.channel}.source.leveli = {val}")

            self.smu.write(f"{self.channel}.source.pulsewidth = {pulse_width}")
            self.smu.write(f"{self.channel}.source.initiate()")
            time.sleep(pulse_width + pulse_delay)

            y = self.measure(measure_type)
            y_vals.append(y)
            print(f"Pulse {source_type}={val}, Measured {measure_type}={y}")

        self.smu.write(
            f"{self.channel}.source.output = {self.channel}.OUTPUT_OFF")
        return x_vals, y_vals

    def plot_iv_curve(self):
        """Plot I-V curve."""
        if not self.current_data:
            raise RuntimeError("No data to plot!")

        plt.figure(figsize=(10, 6))
        plt.plot(self.voltage_data, self.current_data, 'b-')
        plt.xlabel("Voltage (V)")
        plt.ylabel("Current (A)")
        plt.title("Keithley 2636B I-V Curve")
        plt.grid(True)
        plt.show()

    def disconnect(self):
        """Safely disconnect the instrument."""
        if self.smu:
            self.smu.write(
                f"{self.channel}.source.output = {self.channel}.OUTPUT_OFF")
            self.smu.close()
            print("Keithley disconnected.")
