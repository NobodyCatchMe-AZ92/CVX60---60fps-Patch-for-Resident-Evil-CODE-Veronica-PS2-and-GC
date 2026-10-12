"""ps2eu_map.py: map USA (SLUS_201.84, decomp symbols) functions to PAL SLES-50306 (REG=eu, default) or JP SLPM-65022 (REG=jp) by masked code patterns."""
import struct, re, json, numpy as np
from ps2reg import ELF as TGT_ELF, MAPJ, DATAJ
def load(p):
    d = open(p, "rb").read(); ph = struct.unpack("<I", d[28:32])[0]
    p0 = struct.unpack("<8I", d[ph:ph + 32]); off, vaddr, fsz = p0[1], p0[2], p0[4]
    w = np.frombuffer(d[off:off + fsz][: fsz // 4 * 4], dtype="<u4").astype(np.uint32)
    return vaddr, w
def mask(w):
    op = w >> 26
    m = w.copy()
    m = np.where((op == 2) | (op == 3), w & 0xFC000000, m)                       # j / jal target
    m = np.where(np.isin(op, [8, 9, 10, 11, 12, 13, 14, 15, 24, 25]), w & 0xFFFF0000, m)   # imm ALU ops (incl. lui)
    m = np.where((op >= 32) & (op <= 63), w & 0xFFFF0000, m)                     # loads/stores (offsets)
    fn = w & 0x3F                                                                 # shift amounts (magic-number divides)
    m = np.where((op == 0) & np.isin(fn, [0, 2, 3, 0x38, 0x3A, 0x3B, 0x3C, 0x3E, 0x3F]), w & 0xFFFFF83F, m)
    return m
UB, UW = load("ps2us/SLUS_201.84"); EB, EW = load(TGT_ELF)
UM, EM = mask(UW), mask(EW)
SYM = {}
for l in open("ps2-decomp/config/symbol_addrs.txt"):
    m = re.match(r"(\w+)\s*=\s*0x([0-9A-Fa-f]+);.*size:0x([0-9A-Fa-f]+)", l)
    if m and UB <= int(m.group(2), 16) < UB + 4 * len(UW): SYM[m.group(1)] = (int(m.group(2), 16), int(m.group(3), 16))
index = {}
for i in range(len(EM) - 1): index.setdefault((int(EM[i]), int(EM[i + 1])), []).append(i)
out = {}
for name, (a, sz) in SYM.items():
    i0 = (a - UB) // 4; n = min(max(sz // 4, 4), 24)
    pat = UM[i0:i0 + n]
    cands = index.get((int(pat[0]), int(pat[1])), [])
    hits = [c for c in cands if c + n <= len(EM) and np.array_equal(EM[c:c + n], pat)]
    if len(hits) == 1: out[name] = (a, EB + 4 * hits[0], sz)
json.dump({k: [hex(v[0]), hex(v[1]), v[2]] for k, v in out.items()}, open(MAPJ, "w"), indent=0)
print(f"mapped {len(out)} of {len(SYM)} USA functions uniquely")
for k in ("Ps2SwapDBuff", "PS2_jikken", "njUserMain", "bhMainSequence", "bhAllDrawModel", "bhPutModel", "bhControlLight", "vsync_func", "bhSysCallScreenSaver", "bhControlDoor"):
    print(k, [hex(x) for x in out[k][:2]] if k in out else "-")
# call-graph propagation: walk each mapped pair in parallel; matching jal sites map callee USA -> PAL
inv = {v[0]: k for k, v in SYM.items()}
for it in range(6):
    votes = {}
    for name, (ua, ea, sz) in list(out.items()):
        iu, ie = (ua - UB) // 4, (ea - EB) // 4
        for k in range(sz // 4):
            u, e = int(UW[iu + k]), int(EW[ie + k])
            if (u >> 26) != (e >> 26) and (UM[iu + k] != EM[ie + k]): break   # streams diverged
            if u >> 26 == 3 and e >> 26 == 3:
                tu, te = (u & 0x3FFFFFF) << 2, (e & 0x3FFFFFF) << 2
                if tu in inv and inv[tu] not in out: votes.setdefault(inv[tu], {}).setdefault(te, 0); votes[inv[tu]][te] += 1
    new = 0
    for nm, d in votes.items():
        if len(d) == 1: out[nm] = (SYM[nm][0], next(iter(d)), SYM[nm][1]); new += 1
    if not new: break
    print(f"propagation pass {it}: +{new}")
json.dump({k: [hex(v[0]), hex(v[1]), v[2]] for k, v in out.items()}, open(MAPJ, "w"), indent=0)
print("total mapped", len(out))
for k in ("bhDispTime", "bhSysCallScreenSaver", "RankingCalc"):
    print(k, [hex(x) for x in out[k][:2]] if k in out else "-")
# positional pass: unmapped functions between two mapped neighbours whose gap is the same size in both -> same offsets
SYM2 = {}
for l in open("ps2-decomp/config/symbol_addrs.txt"):
    m = re.match(r"(\w+)\s*=\s*0x([0-9A-Fa-f]+);.*size:0x([0-9A-Fa-f]+)", l)
    if m and 0x100000 <= int(m.group(2), 16) < 0x380000: SYM2[m.group(1)] = (int(m.group(2), 16), int(m.group(3), 16))
mp = {k: [hex(v[0]), hex(v[1]), v[2]] for k, v in out.items()}
fa = sorted((a, n, s) for n, (a, s) in SYM2.items()); i = 0; same = 0; DIFF = []
while i < len(fa):
    if fa[i][1] in mp: i += 1; continue
    j = i
    while j < len(fa) and fa[j][1] not in mp: j += 1
    if i == 0 or j >= len(fa): i = j; continue
    pa, pn, ps = fa[i - 1]; na, nn, ns = fa[j]
    ugap = na - (pa + ps); egap = int(mp[nn][1], 16) - (int(mp[pn][1], 16) + ps)
    if ugap == egap:
        d = int(mp[pn][1], 16) - pa
        for a, n, s in fa[i:j]: mp[n] = [hex(a), hex(a + d), s]; same += 1
    else: DIFF.append((egap - ugap, [n for a, n, s in fa[i:j]], hex(int(mp[pn][1], 16) + ps)))
    i = j
json.dump(mp, open(MAPJ, "w"), indent=0)
print("positional", same, "total", len(mp))
for d in DIFF: print(f"  size-changed gap {d[0]:+#x} at {d[2]}:", ",".join(d[1])[:150])
