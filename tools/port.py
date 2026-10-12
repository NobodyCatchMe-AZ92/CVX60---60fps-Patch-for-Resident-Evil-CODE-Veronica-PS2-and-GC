"""port.py TARGET_DOL: translate every PAL address in mod/regions.json to another CVX build by masked code-pattern
alignment over the whole target text (vectorised, no position guess). Self-checks by translating to USA first
and comparing with regions.json. Prints a table and writes port_<id>.json."""
import json, struct, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")
from dol import Dol
import xlate as X   # PAL loader, mask(), sda_base(), ref_sites()

def masked_text(d):
    addrs, words = [], []
    for _, base, sz, data in d.text:
        w = np.frombuffer(data, dtype=">u4").astype(np.uint32)
        addrs.append(base + 4 * np.arange(len(w), dtype=np.uint32)); words.append(w)
    a = np.concatenate(addrs); w = np.concatenate(words)
    op = w >> 26
    m = w.copy()
    m = np.where(op == 18, w & 0xFC000003, m)
    m = np.where(op == 16, w & 0xFFFF0003, m)
    m = np.where(np.isin(op, [14, 15, 24, 25]), w & 0xFFFF0000, m)
    m = np.where((op >= 32) & (op <= 55), w & 0xFFFF0000, m)
    return a, w, m

class Target:
    def __init__(self, path):
        self.d = Dol(path); self.a, self.w, self.m = masked_text(self.d)
        self.idx = {int(x): i for i, x in enumerate(self.a)}
        self.r2, self.r13 = X.sda_base(self.d)
    def align(self, pal_addr):
        for before, after in ((6, 10), (12, 20), (24, 40)):
            pat = [X.mask(X.PAL.u32(pal_addr + 4 * k)) for k in range(-before, after)]
            cand = np.nonzero(self.m == pat[0])[0]
            ok = [c for c in cand if c + len(pat) <= len(self.m) and np.array_equal(self.m[c:c + len(pat)], pat)]
            if len(ok) == 1: return int(self.a[ok[0] + before])
        return None
    def u32(self, a): return int(self.w[self.idx[a]])

def resolve(T, name, pal):
    if name == "A_R13": return T.r13
    if name.startswith("O_"):
        vals = set()
        for s, _ in X.ref_sites(-pal, "r13")[:8]:
            t = T.align(s)
            if t is None: continue
            imm = T.u32(t) & 0xFFFF; vals.add(-(imm - 0x10000 if imm & 0x8000 else imm))
        return vals.pop() if len(vals) == 1 else None
    if name == "A_COUNTDOWN_POS":   # r2-relative constant, loaded in bhSysCallScreenSaver's timer block (PAL site)
        t = T.align(0x8016D450)
        if t is None: return None
        imm = T.u32(t) & 0xFFFF; return T.r2 + (imm - 0x10000 if imm & 0x8000 else imm)
    if name in ("A_CAM_BASE", "A_DOOR_WRK", "A_TASK_TABLE"):
        vals = set()
        for s, ls in X.ref_sites(pal, "abs")[:8]:
            t = T.align(s)
            if t is None: continue
            w = T.u32(t); op, imm = w >> 26, w & 0xFFFF
            simm = imm - 0x10000 if imm & 0x8000 else imm
            hi = T.u32(t + (ls - s)) & 0xFFFF
            vals.add(((hi << 16) | imm) if op == 24 else ((hi << 16) + simm) & 0xFFFFFFFF)
        return vals.pop() if len(vals) == 1 else None
    return T.align(pal)

if __name__ == "__main__":
    reg = json.load(open("mod/regions.json"))
    usa = Target("usa1/sys/main.dol"); tgt = Target(sys.argv[1])
    gid = open(os.path.join(os.path.dirname(os.path.dirname(sys.argv[1])), "boot.bin") if False else sys.argv[1].replace("main.dol", "boot.bin"), "rb").read(6).decode()
    out, bad, mism = {}, [], []
    for name, (pal_s, usa_s) in reg.items():
        pal = int(pal_s, 16)
        u = resolve(usa, name, pal); t = resolve(tgt, name, pal)
        if u != int(usa_s, 16): mism.append(name)
        if t is None: bad.append(name)
        out[name] = t
        print(f"{name:36} PAL {pal:#010x}  USA {usa_s:>10} (check {'ok' if u == int(usa_s,16) else 'MISMATCH ' + (hex(u) if u is not None else 'None')})  {gid} {hex(t) if t is not None else '???'}")
    print(f"\n{gid}: r2={tgt.r2:#x} r13={tgt.r13:#x}   unresolved: {bad}   USA self-check mismatches: {mism}")
    json.dump({k: (hex(v) if v is not None else None) for k, v in out.items()}, open(f"port_{gid}.json", "w"), indent=1)
