# HORI Wireless Racing Wheel Apex — vendor HID protocol notes

Device: `0f0d:01bc` "HORI WIRELESS RACING WHEEL APEX", USB HID v1.11,
one interface, no serial number. The USB device is the wheel's base/receiver;
the wheel itself talks to it wirelessly.

## Report descriptor

The entire descriptor is vendor-defined — this is why no kernel driver
creates an input device for it:

```
06 00 ff    Usage Page (Vendor 0xFF00)
09 01       Usage (1)
a1 01       Collection (Application)
19 01 29 02 15 00 25 01 75 01 96 00 02   ; 512 x 1-bit
81 02       Input (Data,Var,Abs)          ; 64-byte input report
19 01 29 02
91 02       Output (Data,Var,Abs)         ; 64-byte output report
c0          End Collection
```

Same descriptor in PS mode and PC/Steering mode. Only the input reports
have been reverse-engineered; the output report (force feedback?) is
unexplored.

## Input report (64 bytes, ~250 Hz, continuous)

Idle frame (wheel awake, everything centered/released):

```
f0 01 01 00 00 00 00 00 00 00 00 00 40 01 00 0b
00*32
00 00 00 80 00 00 00 00 00 00 00 00 00 00 00 00
```

| Offset | Size | Meaning |
|-------:|-----:|---------|
| 0-1    | 2 | Constant header `f0 01` |
| 2      | 1 | Wireless link state: `01` = wheel connected/awake, `00` = wheel asleep or off. While 0, all control fields freeze. |
| 4      | 1 | Button bits: `0x08` left paddle, `0x80` right paddle. Other bits unobserved. |
| 5      | 1 | Button bits: `0x01` square, `0x02` triangle, `0x04` L2 click, `0x08` R2 click, `0x40` Share, `0x80` Options. |
| 6      | 1 | Never observed changing. Suspected d-pad bits (up/down/left/right = 0x01/02/04/08) — unverified. |
| 7      | 1 | Button bits: `0x02` cross, `0x04` circle. `0x01` suspected PS/home — unverified. |
| 12-13  | 2 | Constant `40 01` (status? battery?) |
| 14-15  | 2 | Constant `00 0b` |
| 24-25  | 2 | L2 analog travel, u16 LE, 0 → 0xFFFF |
| 26-27  | 2 | R2 analog travel, u16 LE, 0 → 0xFFFF |
| 50-51  | 2 | Steering, u16 LE. 0x0000 full left, 0x8000 center, 0xFFFF full right. Full 16-bit resolution confirmed. |
| 52-53  | 2 | Right pedal (throttle), u16 LE, 0 released → 0xFFFF floored |
| 54-55  | 2 | Left pedal (brake), u16 LE, 0 released → 0xFFFF floored |

All other bytes were `00` in every observed frame.

Button presses set the digital bit for the whole press; L2/R2 additionally
report analog travel. Pedals are pure analog with no digital bit.

## Open questions

- D-pad and PS button locations (assumed byte 6 / byte 7 bit 0).
  Capture with `tools/capture-buttons.py` to confirm.
- Bytes 12-15 meaning (battery level / status flags?).
- Output report format — the wheel accepts 64-byte output reports;
  presumably force feedback and/or LED control. Untouched so far.
- Whether a PS-mode session (byte layouts) differs — PS mode streams the
  same idle frames but was not mapped.

## Method

Captured with the scripts in `tools/` on the raw `hidraw` node while each
control was operated in a known order, then diffed which byte offsets
changed (per-byte min/max over time-bucketed segments). See the scripts
for details; they are generic enough to reuse for other vendor-HID devices.
