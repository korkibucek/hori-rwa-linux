#!/usr/bin/env python3
# Interactive button mapper for the HORI Wireless Racing Wheel Apex driver.
# Prompts for each control, detects the press on the raw HID stream, writes
# /etc/hori-rwa-buttons.json and restarts the driver. Run as root.
import os, glob, json, time, subprocess

VID, PID = 0x0F0D, 0x01BC
CONTROLS = [
    ("cross",        "CROSS (X)"),
    ("circle",       "CIRCLE (O)"),
    ("square",       "SQUARE"),
    ("triangle",     "TRIANGLE"),
    ("paddle_left",  "LEFT shifter paddle (back)"),
    ("paddle_right", "RIGHT shifter paddle (back)"),
    ("l2",           "L2"),
    ("r2",           "R2"),
    ("share",        "SHARE"),
    ("options",      "OPTIONS"),
    ("dpad_up",      "D-PAD UP"),
    ("dpad_down",    "D-PAD DOWN"),
    ("dpad_left",    "D-PAD LEFT"),
    ("dpad_right",   "D-PAD RIGHT"),
    ("extra",        "any other button - but NOT the PS button"),
]

def find_hidraw():
    for p in glob.glob("/sys/class/hidraw/hidraw*/device/uevent"):
        try:
            txt = open(p).read()
        except OSError:
            continue
        if "HID_ID=0003:0000%04X:0000%04X" % (VID, PID) in txt:
            return "/dev/" + p.split("/")[4]
    return None

path = find_hidraw()
if not path:
    raise SystemExit("Wheel not found - is it plugged in?")
f = os.open(path, os.O_RDONLY)

def wait_idle():
    warned = False
    while True:
        d = os.read(f, 64)
        if d[2] != 1:
            if not warned:
                print("   (wheel is asleep - give the steering wheel a nudge)", flush=True)
                warned = True
            continue
        if not (d[4] or d[5] or d[6] or d[7]):
            return

mapping = {}
used = set()
print("")
print("=== HORI wheel button mapper ===")
print("Press each button when asked. If your wheel doesn't have that")
print("button, just wait ~20 seconds and it will be skipped.")
print("", flush=True)
for name, label in CONTROLS:
    wait_idle()
    print(">>> Press %s now" % label, flush=True)
    t0 = time.time()
    got = None
    prev = os.read(f, 64)
    while time.time() - t0 < 20 and not got:
        d = os.read(f, 64)
        for bi in (4, 5, 6, 7):
            new = d[bi] & ~prev[bi]
            if new:
                bit = new & -new
                if (bi, bit) in used:
                    print("   that button is already mapped - press the right one", flush=True)
                else:
                    got = (bi, bit)
                break
        prev = d
    if got:
        mapping[name] = [got[0], got[1]]
        used.add(got)
        print("   OK  (byte %d, bit 0x%02x)" % got, flush=True)
    else:
        print("   skipped - no press seen", flush=True)
with open("/etc/hori-rwa-buttons.json", "w") as fh:
    json.dump(mapping, fh, indent=1)
print("")
print("Saved /etc/hori-rwa-buttons.json:")
for k, v in mapping.items():
    print("  %-13s byte%d bit0x%02x" % (k, v[0], v[1]))
subprocess.run(["systemctl", "restart", "hori-rwa.service"])
print("")
print("Driver restarted - MAPPING COMPLETE", flush=True)
