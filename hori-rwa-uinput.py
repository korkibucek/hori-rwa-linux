#!/usr/bin/env python3
# Userspace driver: HORI Wireless Racing Wheel Apex (0f0d:01bc) -> virtual X360 pad.
# The wheel's PC mode uses a vendor-specific HID protocol (no input node). This
# daemon translates its 64-byte hidraw reports into an emulated Xbox 360
# controller (the layout HORI's own Windows driver presents), so Steam/SDL
# apply their standard mapping: steering = left stick X, pedals = triggers.
import os, time, struct, fcntl, glob, json, select

VID, PID = 0x0F0D, 0x01BC

UI_SET_EVBIT  = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_SET_ABSBIT = 0x40045567
UI_SET_FFBIT  = 0x4004556B
UI_DEV_CREATE  = 0x5501
UI_DEV_DESTROY = 0x5502
EV_SYN, EV_KEY, EV_ABS = 0x00, 0x01, 0x03
EV_FF, EV_UINPUT = 0x15, 0x0101
FF_RUMBLE = 0x50
UI_FF_UPLOAD, UI_FF_ERASE = 1, 2
# struct ff_effect is 48 bytes on x86_64: type u16, id s16, direction u16,
# trigger (2x u16), replay (2x u16), 2 pad, union (32, 8-aligned; for
# FF_RUMBLE: strong u16, weak u16). uinput_ff_upload prepends request_id
# u32 + retval s32 and appends a second ff_effect ("old"): 8+48+48 = 104.
FF_EFFECT_SIZE = 48
UI_BEGIN_FF_UPLOAD = 0xC06855C8   # _IOWR('U', 200, uinput_ff_upload[104])
UI_END_FF_UPLOAD   = 0x406855C9   # _IOW ('U', 201, uinput_ff_upload[104])
UI_BEGIN_FF_ERASE  = 0xC00C55CA   # _IOWR('U', 202, uinput_ff_erase[12])
UI_END_FF_ERASE    = 0x400C55CB   # _IOW ('U', 203, uinput_ff_erase[12])

# Rumble is OFF until /etc/hori-rwa-rumble.json describes the wheel's
# vendor output-report format (discovered with tools/probe-rumble.py):
#   {"template": "<128 hex chars>", "strong_off": N, "weak_off": M}
# template = 64-byte output report; strong/weak motor magnitudes (0-255)
# are written at the given byte offsets. Without the file the driver
# behaves exactly like v3 (no FF capability advertised).
RUMBLE = None
try:
    with open("/etc/hori-rwa-rumble.json") as _fh:
        _r = json.load(_fh)
    RUMBLE = (bytes.fromhex(_r["template"]), int(_r["strong_off"]), int(_r["weak_off"]))
    assert len(RUMBLE[0]) == 64
except (OSError, ValueError, KeyError, AssertionError):
    RUMBLE = None
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
    u = os.open("/dev/uinput", os.O_RDWR | os.O_NONBLOCK)
    fcntl.ioctl(u, UI_SET_EVBIT, EV_KEY)
    fcntl.ioctl(u, UI_SET_EVBIT, EV_ABS)
    if RUMBLE:
        fcntl.ioctl(u, UI_SET_EVBIT, EV_FF)
        fcntl.ioctl(u, UI_SET_FFBIT, FF_RUMBLE)
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
    dev = struct.pack("80s4HI", b"Microsoft X-Box 360 pad", 0x03, 0x045E, 0x028E, 0x0114,
                      16 if RUMBLE else 0)
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

class Rumbler:
    """Translates uinput force-feedback requests into wheel output reports."""

    def __init__(self, u, hid):
        self.u, self.hid = u, hid
        self.effects = {}   # effect id -> (strong, weak) magnitudes 0-65535
        self.playing = set()
        self.level = None

    def handle_uinput_event(self, etype, code, value):
        if etype == EV_UINPUT and code == UI_FF_UPLOAD:
            buf = bytearray(struct.pack("Ii", value, 0)) + bytes(2 * FF_EFFECT_SIZE)
            fcntl.ioctl(self.u, UI_BEGIN_FF_UPLOAD, buf)
            efftype, effid = struct.unpack_from("Hh", buf, 8)
            if efftype == FF_RUMBLE:
                strong, weak = struct.unpack_from("HH", buf, 8 + 16)
                self.effects[effid] = (strong, weak)
            struct.pack_into("i", buf, 4, 0)  # retval = 0
            fcntl.ioctl(self.u, UI_END_FF_UPLOAD, buf)
        elif etype == EV_UINPUT and code == UI_FF_ERASE:
            buf = bytearray(struct.pack("IiI", value, 0, 0))
            fcntl.ioctl(self.u, UI_BEGIN_FF_ERASE, buf)
            effid = struct.unpack_from("I", buf, 8)[0]
            self.effects.pop(effid, None)
            self.playing.discard(effid)
            fcntl.ioctl(self.u, UI_END_FF_ERASE, buf)
        elif etype == EV_FF:
            if value:
                self.playing.add(code)
            else:
                self.playing.discard(code)
            self.update()

    def update(self):
        strong = min(65535, sum(self.effects.get(e, (0, 0))[0] for e in self.playing))
        weak = min(65535, sum(self.effects.get(e, (0, 0))[1] for e in self.playing))
        level = (strong >> 8, weak >> 8)
        if level == self.level:
            return
        self.level = level
        report = bytearray(RUMBLE[0])
        report[RUMBLE[1]] = level[0]
        report[RUMBLE[2]] = level[1]
        try:
            os.write(self.hid, bytes(report))
        except OSError:
            pass


def run(path, u):
    f = os.open(path, os.O_RDONLY)
    hid_out = os.open(path, os.O_WRONLY) if RUMBLE else None
    rumbler = Rumbler(u, hid_out) if RUMBLE else None
    prev_raw = None
    prev = {}
    try:
        while True:
            rlist = [f, u] if rumbler else [f]
            ready, _, _ = select.select(rlist, [], [])
            if rumbler and u in ready:
                try:
                    ev = os.read(u, 24)
                    if len(ev) == 24:
                        etype, code, value = struct.unpack_from("HHi", ev, 16)
                        rumbler.handle_uinput_event(etype, code, value)
                except OSError:
                    pass
            if f not in ready:
                continue
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
        if hid_out is not None:
            os.close(hid_out)

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
