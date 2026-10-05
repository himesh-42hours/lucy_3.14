# check_device.py

import sounddevice as sd

print(sd.query_devices())
print()
print(sd.default.device)