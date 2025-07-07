import pyvisa
import logging
import time

logging.basicConfig(filename='instrument_gui.log', level=logging.INFO)


class SR830Controller:
    def __init__(self, address=None):
        try:
            self.rm = pyvisa.ResourceManager()
            self.address = address or self._find_device()
            self.inst = self.rm.open_resource(self.address)
            self.inst.write_termination = '\n'
            self.inst.read_termination = '\n'
            self.inst.timeout = 5000
            idn = self.inst.query("*IDN?").strip()
            logging.info(f"Connected to SR830: {idn}")
        except Exception as e:
            logging.error(f"Failed to connect to SR830: {e}")
            raise

    def _find_device(self):
        for res in self.rm.list_resources():
            try:
                inst = self.rm.open_resource(res)
                inst.write_termination = '\n'
                inst.read_termination = '\n'
                idn = inst.query("*IDN?").strip()
                if "SR830" in idn.upper():
                    logging.info(f"SR830 found at {res}: {idn}")
                    return res
            except Exception:
                continue
        raise Exception(
            "SR830 Lock-in Amplifier not found. Check connections.")

    def configure(self, frequency, amplitude, time_constant_index, sensitivity_index):
        """
        Configure the SR830 Lock-in Amplifier with reference frequency, amplitude, time constant, and sensitivity.

        Parameters:
        - frequency (float): Reference frequency in Hz
        - amplitude (float): Reference amplitude in Volts
        - time_constant_index (int): Time constant setting index (SR830 supports 0-18)
        - sensitivity_index (int): Sensitivity level index (SR830 supports 0-26)
        """
        try:
            self.set_reference(frequency, amplitude)
            self.set_time_constant(time_constant_index)
            self.set_sensitivity(sensitivity_index)
            logging.info(
                f"SR830 configured with freq={frequency}Hz, amp={amplitude}V, TC index={time_constant_index}, Sens index={sensitivity_index}")
        except Exception as e:
            logging.error(f"Failed to configure SR830: {e}")
            raise

    def set_reference(self, frequency, amplitude):
        try:
            self.inst.write(f'FREQ {frequency}')
            self.inst.write(f'SLVL {amplitude}')
            logging.info(
                f"Set ref freq to {frequency} Hz, amplitude to {amplitude} V")
        except Exception as e:
            logging.warning(f"Failed to set reference: {e}")

    def set_time_constant(self, value_index):
        try:
            self.inst.write(f'OFLT {value_index}')
            logging.info(f"Set time constant index to {value_index}")
        except Exception as e:
            logging.warning(f"Failed to set time constant: {e}")

    def set_sensitivity(self, level_index):
        try:
            self.inst.write(f'SENS {level_index}')
            logging.info(f"Set sensitivity level index to {level_index}")
        except Exception as e:
            logging.warning(f"Failed to set sensitivity: {e}")

    def read_xy(self):
        try:
            response = self.inst.query('OUTP? 1,2')
            x, y = map(float, response.split(','))
            return x, y
        except Exception as e:
            logging.warning(f"Failed to read X/Y: {e}")
            return 0.0, 0.0

    def read_rtheta(self):
        try:
            r = float(self.inst.query('OUTP? 3'))
            theta = float(self.inst.query('OUTP? 4'))
            return r, theta
        except Exception as e:
            logging.warning(f"Failed to read R/θ: {e}")
            return 0.0, 0.0

    def disconnect(self):
        self.close()

    def close(self):
        try:
            self.inst.close()
            self.rm.close()
            logging.info("SR830 connection closed.")
        except Exception as e:
            logging.warning(f"SR830 close error: {e}")
