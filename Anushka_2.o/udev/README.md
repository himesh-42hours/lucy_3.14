# Udev setup

This folder contains the template for permanent serial names.

## Install

1. Copy `99-anushka-arduinos.rules.example` to `/etc/udev/rules.d/99-anushka-arduinos.rules`
2. Replace `LEFT_ARM_SERIAL`, `RIGHT_ARM_SERIAL`, `HEAD_SERIAL`, and `BASE_SERIAL` with the real board serials
3. Reload rules:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Use in `.env`

```env
ANUSHKA_LEFT_ARM_MEGA_PORT=/dev/anushka_left_arm
ANUSHKA_RIGHT_ARM_MEGA_PORT=/dev/anushka_right_arm
ANUSHKA_HEAD_MEGA_PORT=/dev/anushka_head
ANUSHKA_BASE_MEGA_PORT=/dev/anushka_base
```

## Why this works

`ttyACM0`, `ttyACM1`, etc. can change after reboot or reconnect. Udev creates fixed symlinks based on each Arduino's serial number, so the runtime always opens the same board.
