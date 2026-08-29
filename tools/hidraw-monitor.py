import sys, os, time
dur = float(sys.argv[1]) if len(sys.argv) > 1 else 8
f = os.open("/dev/hidraw5", os.O_RDONLY)
end = time.time() + dur
mins = [255]*64; maxs = [0]*64; first = None; last = None
n = 0
while time.time() < end:
    d = os.read(f, 64)
    if first is None: first = d
    last = d
    n += 1
    for i, b in enumerate(d):
        if b < mins[i]: mins[i] = b
        if b > maxs[i]: maxs[i] = b
print("reports", n)
print("changed:", " ".join("%d:%02x-%02x" % (i, mins[i], maxs[i]) for i in range(64) if mins[i] != maxs[i]))
print("first:", first.hex())
print("last: ", last.hex())
