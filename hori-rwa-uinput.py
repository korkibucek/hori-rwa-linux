#!/usr/bin/env python3
# Userspace driver: HORI Wireless Racing Wheel Apex (0f0d:01bc) -> virtual X360 pad.
# The wheel's PC mode uses a vendor-specific HID protocol (no input node). This
# daemon translates its 64-byte hidraw reports into an emulated Xbox 360
# controller (the layout HORI's own Windows driver presents), so Steam/SDL
# apply their standard mapping: steering = left stick X, pedals = triggers.
import os, time, struct, fcntl, glob, json

VID, PID = 0x0F0D, 0x01BC

UI_SET_EVBIT  = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_SET_ABSBIT = 0x40045567
UI_DEV_CREATE  = 0x5501
UI_DEV_DESTROY = 0x5502
EV_SYN, EV_KEY, EV_ABS = 0x00, 0x01, 0x03
ABS_X, ABS_Y, ABS_Z, ABS_RX, ABS_RY, ABS_RZ = 0, 1, 2, 3, 4, 5
ABS_HAT0X, ABS_HAT0Y = 0x10, 0x11

BTN = {  # (report byte, bitmask) -> X360 button; confirmed with hori-rwa-mapper.py
    (4, 0x40): 0x130,  # A      (cross)
    (4, 0x20): 0x131,  # B      (circle)
    (4, 0x80): 0x133,  # X      (square)
    (4, 0x10): 0x134,  # Y      (triangle)
    (7, 0x01): 0x136,  # LB     (left shifter paddle)
    (7, 0x02): 0x137,  # RB     (right shifter paddle)
    (5, 0x04): 0x13D,  # LS click (L2 button)
    (5, 0x08): 0x13E,  # RS click (R2 button)
    (5, 0x10): 0x13A,  # Back   (share)
    (5, 0x20): 0x13B,  # Start  (options)
    (5, 0x80): 0x2C0,  # extra button (Assign)
}
HAT = {  # (report byte, bitmask) -> (axis, value); confirmed with hori-rwa-mapper.py
    (4, 0x01): (ABS_HAT0Y, -1),  # up
    (4, 0x04): (ABS_HAT0Y, 1),   # down
    (4, 0x08): (ABS_HAT0X, -1),  # left
    (4, 0x02): (ABS_HAT0X, 1),   # right
}

# /etc/hori-rwa-buttons.json (written by hori-rwa-mapper.py) overrides the
# built-in guesses. Format: {"control_name": [report_byte, bitmask], ...}
NAME2BTN = {
    "cross": 0x130, "circle": 0x131, "square": 0x133, "triangle": 0x134,
    "paddle_left": 0x136, "paddle_right": 0x137, "l2": 0x13D, "r2": 0x13E,
    "share": 0x13A, "options": 0x13B, "ps": 0x13C, "extra": 0x2C0,
}
NAME2HAT = {
    "dpad_up": (ABS_HAT0Y, -1), "dpad_down": (ABS_HAT0Y, 1),
    "dpad_left": (ABS_HAT0X, -1), "dpad_right": (ABS_HAT0X, 1),
}
try:
    with open("/etc/hori-rwa-buttons.json") as _fh:
        _cfg = json.load(_fh)
    BTN, HAT = {}, {}
    for _name, (_bi, _mask) in _cfg.items():
        if _name in NAME2HAT:
            HAT[(_bi, _mask)] = NAME2HAT[_name]
        elif _name in NAME2BTN:
            BTN[(_bi, _mask)] = NAME2BTN[_name]
except (OSError, ValueError):
    pass

def find_hidraw():
    for p in glob.glob("/sys/class/hidraw/hidraw*/device/uevent"):
        try:
            txt = open(p).read()
        except OSError:
            continue
        if "HID_ID=0003:0000%04X:0000%04X" % (VID, PID) in txt:
            return "/dev/" + p.split("/")[4]
    return None

def emit(u, etype, code, value):
    os.write(u, struct.pack("qqHHi", 0, 0, etype, code, value))

def create_uinput():
    u = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
    fcntl.ioctl(u, UI_SET_EVBIT, EV_KEY)
    fcntl.ioctl(u, UI_SET_EVBIT, EV_ABS)
    for code in BTN.values():
        fcntl.ioctl(u, UI_SET_KEYBIT, code)
    for code in (ABS_X, ABS_Y, ABS_Z, ABS_RX, ABS_RY, ABS_RZ, ABS_HAT0X, ABS_HAT0Y):
        fcntl.ioctl(u, UI_SET_ABSBIT, code)
    amax = [0]*64; amin = [0]*64; afuzz = [0]*64; aflat = [0]*64
    for code in (ABS_X, ABS_Y, ABS_RX, ABS_RY):
        amin[code], amax[code], afuzz[code], aflat[code] = -32768, 32767, 16, 128
    for code in (ABS_Z, ABS_RZ):
        amax[code] = 255
    for code in (ABS_HAT0X, ABS_HAT0Y):
        amin[code], amax[code] = -1, 1
    dev = struct.pack("80s4HI", b"Microsoft X-Box 360 pad", 0x03, 0x045E, 0x028E, 0x0114, 0)
    dev += struct.pack("64i", *amax) + struct.pack("64i", *amin)
    dev += struct.pack("64i", *afuzz) + struct.pack("64i", *aflat)
    os.write(u, dev)
    fcntl.ioctl(u, UI_DEV_CREATE)
    return u

def parse(d):
    state = {}
    for (bi, mask), code in BTN.items():
        state[(EV_KEY, code)] = 1 if d[bi] & mask else 0
    hx = hy = 0
    for (bi, mask), (axis, val) in HAT.items():
        if d[bi] & mask:
            if axis == ABS_HAT0X: hx = val
            else: hy = val
    state[(EV_ABS, ABS_HAT0X)] = hx
    state[(EV_ABS, ABS_HAT0Y)] = hy
    state[(EV_ABS, ABS_X)] = (d[50] | d[51] << 8) - 32768   # steering
    state[(EV_ABS, ABS_RZ)] = (d[52] | d[53] << 8) >> 8     # right pedal -> RT
    state[(EV_ABS, ABS_Z)] = (d[54] | d[55] << 8) >> 8      # left pedal -> LT
    return state

def run(path, u):
    f = os.open(path, os.O_RDONLY)
    prev_raw = None
    prev = {}
    try:
        while True:
            d = os.read(f, 64)
            if len(d) < 56 or d == prev_raw:
                continue
            prev_raw = d
            state = parse(d)
            dirty = False
            for key, val in state.items():
                if prev.get(key) != val:
                    emit(u, key[0], key[1], val)
                    dirty = True
            if dirty:
                emit(u, EV_SYN, 0, 0)
            prev = state
    finally:
        os.close(f)

def main():
    while True:
        path = find_hidraw()
        if not path:
            time.sleep(3)
            continue
        u = create_uinput()
        try:
            run(path, u)
        except OSError:
            pass
        finally:
            try:
                fcntl.ioctl(u, UI_DEV_DESTROY)
            except OSError:
                pass
            os.close(u)
        time.sleep(1)

main()
