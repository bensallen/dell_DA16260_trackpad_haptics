# touchpad-haptics

Control the haptic click strength of the Dell XPS 16 (DA16260) touchpad on Linux.

On this laptop, neither GNOME, libinput, the kernel nor the BIOS offers a setting for
haptic strength. Windows has a slider, but nothing on Linux used the touchpad
interface behind it. This package provides a small CLI that sets it, plus a udev rule
and a systemd-sleep hook to keep the setting applied.

## Hardware

| | |
|---|---|
| Touchpad | Synaptics `06CB:D01A`, part `TM4122-001`, I²C-HID, driven by `hid-multitouch` |
| Haptic driver | Qorvo QPG5072 microcontroller behind the Synaptics controller |
| I²C path | `0000:00:19.0` → `i2c_designware.0` → `i2c-VEN_06CB:00` |

## Findings

### The standard intensity report

The touchpad's HID report descriptor has a feature report `0x37` on the HID Haptics
page (`0x0E`), usage `0x23` (Intensity), with a logical range of 0–100.

- Writing it with `HIDIOCSFEATURE` on the hidraw node works.
- Reading it with `HIDIOCGFEATURE` fails with `EREMOTEIO`, so the current value can't be read back.
- The touchpad generates click feedback on its own. Nothing has to be sent per click.
  The descriptor has no Manual Trigger usage (`0x21`).

### Only five values matter

Values from 1 to 100 first seemed to feel identical, while 0 turned haptics off. To find
out why, the Dell touchpad firmware updater
(`Dell-Touchpad-Firmware-Update-Utility_Y3TT2_WIN64_1739.53274.277_A00.EXE`) was
unpacked. It contains two flashers: `TM-4122-1.exe` for the Synaptics controller and
`qmcu_fw_updater…exe` for the Qorvo haptic chip. The Qorvo firmware is a Cortex-M
image embedded in the second flasher's `.data` section, at load base `0x04014c00`.
Its debug strings are intact.

Disassembling the Qorvo command handler showed this:

- The Windows updater talks to the Qorvo chip through the touchpad's vendor page
  `0xFF81` (feature reports `0x38`/`0x39`/`0x3A`), which pass messages through to the chip.
- Command `0x05` sets the press strength and `0x08` the release strength. Each takes
  one byte, which the firmware maps to one of five levels:

  | Byte | Level |
  |---|---|
  | `0x00` | off |
  | `0x3F` | 1 |
  | `0x7F` | 2 |
  | `0xBF` | 3 |
  | `0xFF` | 4 |
  | anything else | 2 (default) |

These bytes are 0/25/50/75/100 scaled to 0–255. The Synaptics firmware appears to
scale report `0x37` this way and forward it, so **only 0, 25, 50, 75 and 100 are
distinct**. Every other value falls back to level 2, which is why most of the range
felt the same. Testing confirmed that 25 and 100 feel different, but the difference
is subtle.

The difference is small because the built-in gain tables are close together. These
are the press amplitudes for the five touchpad zones:

```
level 1: 48 41 36 46 4f
level 2: 52 4b 3c 50 58
level 3: 54 52 42 52 5b
level 4: 58 5a 46 52 5f
```

Level 4 is only about 15–25% stronger than level 1. The firmware can load a custom
gain table from its flash, and the updater has commands to write one. That protocol
is undocumented, and a mistake could leave the haptics broken until Dell's Windows
updater reflashes the chip. This project doesn't attempt it.

### Haptics lost after suspend

Omarchy ships a daemon that re-sends the intensity report on every button press. Their
own explanation is that a "Manual Trigger" pulse is needed. That doesn't match this
touchpad's descriptor. Their commit history suggests the real problem was the touchpad
losing its haptic state around suspend/resume and boot. Re-sending the setting on every
click hides that problem.

This package reapplies the setting when the device appears and after every resume
instead. Two fallbacks exist if that isn't enough:

- **The level resets while the laptop is awake:** keep the I²C controller powered by
  setting `ATTR{power/control}="on"` on `0000:00:19.0` and `i2c_designware.0` in a
  udev rule. This costs some idle power.
- **Haptics stop entirely:** re-sending the level won't help. Unbind and rebind
  `i2c_hid_acpi` for `i2c-VEN_06CB:00`.

### Upstream status

A kernel interface for haptic touchpad settings is only at the RFC stage on
linux-input as of mid-2026. GNOME and libinput have no haptics setting.

## What's here

| File | Purpose |
|---|---|
| `touchpad-haptics` | CLI (Python, no dependencies) |
| `touchpad-haptics.conf` | Config file, installed as `/etc/touchpad-haptics.conf` |
| `70-touchpad-haptics.rules` | udev rule: gives the logged-in user access to the hidraw node (`uaccess`) and applies the configured level when the device appears |
| `touchpad-haptics.sleep` | systemd-sleep hook that reapplies the level after resume |
| `touchpad-haptics.spec`, `Makefile` | RPM packaging |
| `probe-features` | Diagnostic script, not packaged: tries `GET_FEATURE` on each of the touchpad's feature reports |

## Build and install

```sh
make rpm
sudo dnf install ./rpmbuild/RPMS/noarch/touchpad-haptics-1.1-1.fc44.noarch.rpm
```

`make srpm` builds only the source RPM. `make clean` removes `rpmbuild/`.

## Usage

```sh
touchpad-haptics set off        # or 0: disable haptics
touchpad-haptics set 1          # weakest … 4 strongest
touchpad-haptics set --raw 60   # send a raw 0–100 value unchanged
touchpad-haptics apply          # apply the level from /etc/touchpad-haptics.conf
touchpad-haptics info           # show the detected hidraw node and report
touchpad-haptics -d /dev/hidraw1 set 3
```

The device is found by searching hidraw report descriptors for the Haptics Intensity
usage. Once the udev rule is installed, the logged-in user can run `set` without
root. Without the rule, use `sudo`. `get` is included, but this touchpad rejects reads.

`set` changes the level only until the next reboot or resume, when `apply` restores
the configured level. To make a change permanent, edit `/etc/touchpad-haptics.conf`:

```sh
LEVEL=3
```

Valid values are `off` and `1` to `4`. The default is `2`.
