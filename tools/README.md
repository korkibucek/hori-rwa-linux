# Capture / reverse-engineering tools

Small scripts used to map the wheel's vendor HID reports. They read the raw
hidraw node directly and print which byte offsets change while you operate
the controls. **They hardcode `/dev/hidraw5`** — check
`ls /sys/class/hidraw/*/device/uevent | xargs grep -l 0F0D` and adjust the
path before use. Run as root.

- `hidraw-monitor.py [seconds]` — per-byte min/max over a window; quick
  "which bytes move" check.
- `capture-phased.py` — three timed phases (wheel / pedals / buttons) with
  on-screen prompts; prints changed bytes and sample frames per phase.
- `capture-timeline.py` — 150 s free-play capture; prints a timestamped,
  segment-merged timeline of every change (best for ordered sequences).
- `capture-buttons.py` — 75 s capture that ignores the steering bytes
  (2, 50, 51) so button/pedal events stand out. Use this to confirm the
  unverified d-pad / PS button bits.
