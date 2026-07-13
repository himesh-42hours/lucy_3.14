import sounddevice as sd

for i, dev in enumerate(sd.query_devices()):
    if dev["max_input_channels"] > 0:
        print(i, dev)