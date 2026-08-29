#!/usr/bin/env python3
# Interactive discovery of the wheel's vibration output-report format.
#
# The wheel accepts 64-byte vendor output reports (see PROTOCOL.md) and has
# rumble motors (they work on PS4/Windows), but the command format is
# undocumented. This tool writes candidate reports one at a time and asks
# whether the wheel buzzed. Run it in a terminal as root while someone has
# a hand on the wheel:   python3 probe-rumble.py
#
# DO NOT run while a game is being played: unknown commands may reset the
# wheel's wireless link (the PS button does exactly that).
import os, glob, json, time

VID, PID = 0x0F0D, 0x01BC

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
    raise SystemExit("Wheel not found")
f = os.open(path, os.O_WRONLY)

def send(report):
    try:
        os.write(f, bytes(report))
    except OSError as e:
        print("   (write failed: %s)" % e)

def ask(what):
    r = input(">>> %s  - did the wheel buzz/react? [y/N/q] " % what).strip().lower()
    if r == "q":
        raise SystemExit("aborted")
    return r == "y"

def trial(report, what):
    send(report)
    time.sleep(1.2)
    send(bytes(64))          # all-zero report as "stop"
    time.sleep(0.5)
    return ask(what)

def save(template, strong_off, weak_off):
    cfg = {"template": bytes(template).hex(), "strong_off": strong_off, "weak_off": weak_off}
    with open("/etc/hori-rwa-rumble.json", "w") as fh:
        json.dump(cfg, fh, indent=1)
    print("Saved /etc/hori-rwa-rumble.json - restart hori-rwa.service to enable rumble.")

print("Phase 1: likely formats")
candidates = []
ds4 = bytearray(64); ds4[0] = 0x05; ds4[1] = 0xFF; ds4[4] = 0xFF; ds4[5] = 0xFF
candidates.append((ds4, "DS4-style (0x05 header, motors at 4/5)", 5, 4))
for off in (2, 3, 4, 5, 12):
    r = bytearray(64); r[0] = 0xF0; r[1] = 0x01; r[off] = 0xFF; r[off + 1] = 0xFF
    candidates.append((r, "f0 01 header, motors at %d/%d" % (off, off + 1), off, off + 1))
for report, what, s_off, w_off in candidates:
    if trial(report, what):
        t = bytearray(report); t[s_off] = 0; t[w_off] = 0
        save(t, s_off, w_off)
        raise SystemExit(0)

print("Phase 2: single-byte sweep, no header (offsets 0-31)")
for off in range(32):
    r = bytearray(64); r[off] = 0xFF
    if trial(r, "plain report, 0xFF at offset %d" % off):
        save(bytearray(64), off, off)
        raise SystemExit(0)

print("Phase 3: single-byte sweep with f0 01 header (offsets 2-31)")
for off in range(2, 32):
    r = bytearray(64); r[0] = 0xF0; r[1] = 0x01; r[off] = 0xFF
    if trial(r, "f0 01 header, 0xFF at offset %d" % off):
        t = bytearray(64); t[0] = 0xF0; t[1] = 0x01
        save(t, off, off)
        raise SystemExit(0)

print("No luck. Next step: capture the PS4's USB traffic to the wheel, or")
print("HORI's Windows driver with Wireshark/usbmon, and add the format here.")
