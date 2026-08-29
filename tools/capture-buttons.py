import os, time
DUR = 75
IGN = {2, 50, 51}
f = os.open("/dev/hidraw5", os.O_RDONLY)
t0 = time.time()
prev = None
segs = []
while time.time() - t0 < DUR:
    d = os.read(f, 64)
    t = time.time() - t0
    if prev is not None:
        ch = frozenset(i for i in range(64) if d[i] != prev[i] and i not in IGN)
        if ch:
            if segs and segs[-1][2] == ch and t - segs[-1][1] < 0.6:
                s = segs[-1]; s[1] = t; s[3].append(d)
            else:
                segs.append([t, t, ch, [d]])
    prev = d
print("SEGMENTS %d" % len(segs))
for t_a, t_b, ch, ds in segs:
    parts = []
    for i in sorted(ch):
        vals = [d[i] for d in ds]
        parts.append("%d:%02x-%02x(end %02x)" % (i, min(vals), max(vals), ds[-1][i]))
    print("%6.1f-%6.1f n=%-4d %s" % (t_a, t_b, len(ds), " ".join(parts)))
print("FINAL2:", prev.hex())
