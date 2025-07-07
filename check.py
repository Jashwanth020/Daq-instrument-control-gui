import pyvisa

rm = pyvisa.ResourceManager()
print(rm.list_resources())
# ('GPIB0::12::INSTR', 'GPIB0::8::INSTR', 'USB0::0x05E6::0x2450::04411193::0::INSTR')
('GPIB0::12::INSTR', 'GPIB0::8::INSTR', 'USB0::0x05E6::0x2450::04411193::0::INSTR',
 'USB0::0x05E6::0x2636::4481069::0::INSTR')
