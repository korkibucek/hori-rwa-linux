# HORI Wireless Racing Wheel Apex — Linux driver

Userspace driver that makes the **HORI Wireless Racing Wheel Apex**
(USB ID `0f0d:01bc`) work as a game controller on Linux.

Out of the box the wheel does not appear under game controllers on any Linux
distribution. Even with its platform switch set to **PC/Steering** mode, the
wheel speaks a fully vendor-specific HID protocol: its report descriptor
contains only vendor usages (usage page `0xFF00`), so the kernel binds
`hid-generic`, creates raw `hidraw`/`hiddev` nodes, and no input device is
ever created. On Windows this is papered over by HORI's proprietary driver.

This project replaces that driver: a small, dependency-free Python daemon
reads the wheel's raw 64-byte HID reports and feeds a virtual **Xbox 360
controller** through `uinput` — the same layout HORI's Windows driver
presents. Steam, SDL, and Proton games recognise it automatically.

| Wheel control          | Presented as            |
|------------------------|-------------------------|
| Steering               | Left stick X (16-bit)   |
| Right pedal            | Right trigger (RT)      |
| Left pedal             | Left trigger (LT)       |
| Cross / Circle         | A / B                   |
| Square / Triangle      | X / Y                   |
| Left / Right paddle    | LB / RB                 |
| L2 / R2 buttons        | Left / Right stick click|
| Share / Options        | Back / Start            |
| PS button              | Guide                   |
| D-pad                  | D-pad (hat)             |

## Requirements

- Any modern Linux with `python3` and the `uinput` kernel module
  (present by default on Bazzite, SteamOS, Fedora, Ubuntu, Arch, …).
- No third-party packages: the daemon talks to `uinput` with raw ioctls.
- Root (the daemon runs as a systemd system service).

Tested on Bazzite (Fedora Atomic). Because it is pure userspace, it
survives kernel updates — no DKMS/akmods needed, which matters on
immutable/atomic distributions.

## Install

```bash
sudo cp hori-rwa-uinput.py /usr/local/bin/hori-rwa-uinput.py
sudo chmod 755 /usr/local/bin/hori-rwa-uinput.py
sudo cp systemd/hori-rwa.service /etc/systemd/system/hori-rwa.service
sudo systemctl daemon-reload
sudo systemctl enable --now hori-rwa.service
```

Set the wheel's platform toggle to **PC/Steering** mode and connect it via
USB. Verify:

```bash
systemctl status hori-rwa.service
cat /proc/bus/input/devices | grep -A4 "X-Box 360"
```

A `js0`/`eventN` device named "Microsoft X-Box 360 pad" appears whenever the
wheel is plugged in; it is removed when the wheel is unplugged. The daemon
polls for the wheel every 3 seconds, so plug order doesn't matter.

## Usage notes

- **The wheel sleeps aggressively.** A few seconds after you stop touching
  it, the wheel drops its wireless link to the USB base and the controller
  goes quiet (it does not disappear). Nudge the wheel or press a button to
  wake it.
- **Remapping.** If a button doesn't do what you expect, remap it in
  Steam's controller layout screen, or edit the `BTN` table at the top of
  `hori-rwa-uinput.py` (see `PROTOCOL.md` for the bit layout) and
  `sudo systemctl restart hori-rwa.service`.
- **Force feedback is not implemented.** Steering, pedals, and buttons work;
  rumble/FFB would require reverse-engineering the wheel's output reports.
  Contributions welcome.

## How it was reverse-engineered

The wheel streams 64-byte input reports at ~250 Hz on `hidraw` regardless of
mode. The scripts in `tools/` were used to capture reports while each
control was operated and to diff which bytes changed; the resulting map is
documented in [PROTOCOL.md](PROTOCOL.md). The capture tools are kept in the
repo so unknown fields (d-pad bits, PS button, force feedback) can be
confirmed or corrected later.

## Repository layout

```
hori-rwa-uinput.py       the driver daemon
systemd/hori-rwa.service systemd unit
tools/                   hidraw capture/analysis scripts used for the RE work
PROTOCOL.md              reverse-engineered report format
```

## Status / caveats

- D-pad and PS/Guide button bit positions are **unverified guesses**
  (byte 6 bits 0-3 and byte 7 bit 0); they were never observed in a capture.
  If they don't work, capture a press with `tools/capture-buttons.py` and
  fix the tables.
- Force feedback: not implemented.
- Only the wireless model (`0f0d:01bc`) is handled. The wired Racing Wheel
  Apex (`0f0d:00a4`) reportedly works out of the box via `xpad`/generic HID
  and does not need this driver.

## License

GPL-2.0-or-later.
