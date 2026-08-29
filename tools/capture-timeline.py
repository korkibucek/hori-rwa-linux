import os, time
DUR = 150
f = os.open("/dev/hidraw5", os.O_RDONLY)
t0 = time.time()
prev = None
events = []
while time.time() - t0 < DUR:
    d = os.read(f, 64)
    t = time.time() - t0
    if prev is not None and d != prev:
        ch = frozenset(i for i in range(64) if d[i] != prev[i])
        events.append((t, ch, bytes(d)))
    prev = d
segs = []
for t, ch, d in events:
    if segs and segs[-1][2] == ch and t - segs[-1][1] < 0.6:
        s = segs[-1]; s[1] = t; s[3].append(d)
    else:
        segs.append([t, t, ch, [d]])
print("EVENTS %d SEGMENTS %d" % (len(events), len(segs)))
for s in segs[:120]:
    t_a, t_b, ch, ds = s
    parts = []
    for i in sorted(ch):
        vals = [d[i] for d in ds]
        lo, hi = min(vals), max(vals)
        parts.append("%d:%02x-%02x(end %02x)" % (i, lo, hi, ds[-1][i]))
    print("%6.1f-%6.1f n=%-4d %s" % (t_a, t_b, len(ds), " ".join(parts)))
print("FINAL:", prev.hex())
