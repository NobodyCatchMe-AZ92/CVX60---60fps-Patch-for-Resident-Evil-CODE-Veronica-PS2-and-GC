"""jpresolve.py: read the PAL->JP addresses the mod needs out of jp_map.json (from propagate.py)."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ".")
from pair import P, J
reg = json.load(open("mod/regions.json")); jm = json.load(open("jp_map.json"))
def fn_start(d, a):
    while (d.u32(a) & 0xFFFF0000) != 0x94210000: a -= 4
    return a
def bl_target(d, a):
    w = d.u32(a); off = w & 0x3FFFFFC
    if off & 0x2000000: off -= 0x4000000
    return a + off
def vote(kind, key): return jm.get(kind, {}).get(key)
out, unres = {}, []
for name, (pal_s, usa_s) in reg.items():
    pal = int(pal_s, 16); res = None
    if name.startswith("O_"):
        v = vote("r13", str(-pal)); res = (-v[0][0]) if v else None
    elif name in ("A_CAM_BASE", "A_DOOR_WRK", "A_TASK_TABLE"):
        v = vote("abs", hex(pal)); res = int(v[0][0], 16) if v else None
    elif name in ("A_R13", "A_COUNTDOWN_POS"):
        continue
    elif name.startswith("A_SITE"):
        callee = bl_target(P, pal); fs = fn_start(P, pal)
        jc = vote("bl", hex(callee)); jf = vote("bl", hex(fs))
        if jc and jf:
            jcal = int(jc[0][0], 16); jfs = int(jf[0][0], 16)
            hits = [jfs + 4 * i for i in range(3000) if J.u32(jfs + 4 * i) >> 26 == 18 and J.u32(jfs + 4 * i) & 1 and bl_target(J, jfs + 4 * i) == jcal]
            # same ordinal among calls to that callee as in PAL
            pal_hits = [fs + 4 * i for i in range(3000) if P.u32(fs + 4 * i) >> 26 == 18 and P.u32(fs + 4 * i) & 1 and bl_target(P, fs + 4 * i) == callee]
            if len(hits) == len(pal_hits) and pal in pal_hits: res = hits[pal_hits.index(pal)]
        v = (jc, jf)
    else:
        v = vote("bl", hex(pal)); res = int(v[0][0], 16) if v else None
    if res is None: unres.append(name)
    out[name] = res
    print(f"{name:36} PAL {pal:#010x} -> JP {hex(res) if res is not None else '???':>10}   votes {v if not name.startswith('A_SITE') else ''}")
print("unresolved:", unres)
json.dump({k: hex(v) if v is not None else None for k, v in out.items()}, open("jp_resolved.json", "w"), indent=1)
