"""ps2stats.py [secs]: CVX60 PS2 diagnostics (cvx_D via symbols) + game tick / buffer-swap rates."""
import json, struct, sys, time
from pmem import PMem
import os
REG = os.environ.get("REG") or ("eu" if os.environ.get("PAL") == "1" else "us")   # REG=eu|jp (or PAL=1); pmem picks the same region
PAL = REG == "eu"
stem = "ps2mod/cvx60_ps2" + {"eu": "_pal", "jp": "_jpn", "us": ""}[REG] + ("_lab" if os.environ.get("LAB") else "")
sym = json.load(open(stem + ".syms.json")); D = sym["cvx_D"]
TICKS = {"eu": 0x1144380, "jp": 0x113A280, "us": 0x112C780}[REG]
F = ["off", "frames", "extra", "late", "vanilla", "camok", "camcut", "camfar", "poserej", "why_last", "why_or", "fake_on", "fake_ps", "bskip", "ptcl", "blood", "snow", "door"]
m = PMem(write=True)
if len(sys.argv) > 2 and sys.argv[1] == "pad":
    m.write(D + 4 * F.index("fake_on"), struct.pack("<I", int(sys.argv[2], 16))); print("pad", sys.argv[2]); sys.exit()
if len(sys.argv) > 2 and sys.argv[1] == "press":
    m.write(D + 4 * F.index("fake_ps"), struct.pack("<I", int(sys.argv[2], 16))); print("press", sys.argv[2]); sys.exit()
secs = float(sys.argv[1]) if len(sys.argv) > 1 else 3
def snap(): return dict(zip(F, m.u32s(D, len(F))), ticks=m.u32(TICKS))
a = snap(); t0 = time.time(); time.sleep(secs); b = snap(); dt = time.time() - t0
for k in ("ticks", "frames", "extra", "late", "vanilla", "camok", "camcut", "camfar", "poserej", "bskip", "ptcl", "blood", "snow", "door"):
    print(f"{k:8} {(b[k] - a[k]) / dt:6.2f}/s")
print("blocked-by last/ever:", hex(b["why_last"]), hex(b["why_or"]), " off", b["off"])
