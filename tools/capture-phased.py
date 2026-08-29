import os, time
PHASES = [("WHEEL: turn full LEFT then full RIGHT, back to center", 12),
          ("PEDALS: press RIGHT pedal fully, release; then LEFT pedal fully, release", 12),
          ("BUTTONS: press each button one at a time incl dpad and paddles", 16)]
f = os.open("/dev/hidraw5", os.O_RDONLY)
for name, dur in PHASES:
    print("\n>>> NOW %s (%ds)" % (name, dur), flush=True)
    end = time.time() + dur
    mins = [255]*64; maxs = [0]*64; n = 0
    samples = []
    while time.time() < end:
        d = os.read(f, 64)
        n += 1
        if n % 100 == 0: samples.append(d.hex())
        for i, b in enumerate(d):
            if b < mins[i]: mins[i] = b
            if b > maxs[i]: maxs[i] = b
    print("reports %d changed: %s" % (n, " ".join("%d:%02x-%02x" % (i, mins[i], maxs[i]) for i in range(64) if mins[i] != maxs[i])), flush=True)
    for s in samples[::4][:6]: print("  s:", s, flush=True)
print("\nDONE", flush=True)
