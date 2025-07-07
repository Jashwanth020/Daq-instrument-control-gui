import pyvisa


class LakeShoreController325:
    def __init__(self):
        self.rm = pyvisa.ResourceManager()
        self.instrument = None
        self.address = None

    def connect(self, address=None):
        try:
            if address:
                # Use provided address
                self.instrument = self.rm.open_resource(address)
                idn = self.instrument.query("*IDN?")
                if "LSCI" in idn or "MODEL 325" in idn.upper():
                    self.address = self.instrument.resource_name
                    return True
                else:
                    self.instrument.close()
                    return False
            else:
                # Auto-detect Lake Shore 325
                for res in self.rm.list_resources():
                    try:
                        inst = self.rm.open_resource(res)
                        inst.timeout = 2000
                        idn = inst.query("*IDN?")
                        if "LSCI" in idn or "MODEL 325" in idn.upper():
                            self.instrument = inst
                            self.address = inst.resource_name
                            return True
                        else:
                            inst.close()
                    except Exception:
                        continue
                return False
        except Exception as e:
            print(f"LakeShore connection error: {e}")
            return False

    def set_temperature(self, temp, loop=1):
        if self.instrument:
            self.instrument.write(f"SETP {loop},{temp}")

    def get_temperature(self, input_channel=1):
        if self.instrument:
            return float(self.instrument.query(f"KRDG? {input_channel}"))
        return None

    def get_setpoint(self, loop=1):
        if self.instrument:
            return float(self.instrument.query(f"SETP? {loop}"))
        return None

    def set_heater_range(self, range_code=1, loop=1):
        if self.instrument:
            self.instrument.write(f"RANGE {loop},{range_code}")

    def get_heater_range(self, loop=1):
        if self.instrument:
            return int(self.instrument.query(f"RANGE? {loop}"))
        return None

    def set_heater_on(self):
        self.write("OUTMODE 1,1,0")  # Example SCPI/TSP command

    def set_heater_off(self):
        self.write("OUTMODE 1,0,0")

    def set_manual_heater_output(self, percent):
        self.write(f"MOUT {percent}")

    def set_pid(self, p, i, d):
        self.write(f"PID 1,{p},{i},{d}")

    def enable_excitation_reversal(self, enable=True):
        self.write(f"EXREV 1,{1 if enable else 0}")

    def set_alarm_threshold(self, threshold):
        self.write(f"ALARM 1,1,{threshold},0")

    def close(self):
        if self.instrument:
            self.instrument.close()
            self.instrument = None
            self.address = None
