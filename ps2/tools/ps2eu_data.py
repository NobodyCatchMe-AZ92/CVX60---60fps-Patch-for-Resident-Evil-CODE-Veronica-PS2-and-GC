"""ps2eu_data.py: USA -> PAL data addresses, from hi/lo address pairs in aligned (mapped) functions. -> ps2eu_data.json
Also checks big SYS_WORK offsets (lui 1..3 + ori/addiu on a sys-derived register) are unchanged."""
import json, collections
exec(open("ps2eu_map.py").read().split("SYM = {}")[0])
mp = json.load(open(MAPJ))
votes = collections.defaultdict(collections.Counter)
for name, (ua, ea, sz) in mp.items():
    ua, ea = int(ua, 16), int(ea, 16)
    if ua >= 0x300000: continue
    iu, ie = (ua - UB) // 4, (ea - EB) // 4; hu, he = {}, {}
    for k in range(sz // 4):
        u, e = int(UW[iu + k]), int(EW[ie + k])
        if (u >> 26) != (e >> 26) or UM[iu + k] != EM[ie + k]: break
        op, rs, rt = u >> 26, (u >> 21) & 31, (u >> 16) & 31
        if op == 15: hu[rt] = (u & 0xFFFF) << 16; he[rt] = (e & 0xFFFF) << 16; continue
        if op in (9, 13) or 32 <= op <= 63:
            if rs in hu and rs in he:
                su = u & 0xFFFF; se = e & 0xFFFF
                if op != 13: su = su - 0x10000 if su & 0x8000 else su; se = se - 0x10000 if se & 0x8000 else se
                A, B = (hu[rs] + su) & 0xFFFFFFFF, (he[rs] + se) & 0xFFFFFFFF
                if 0x100000 <= A < 0x2000000: votes[A][B] += 1
            if op in (9, 13) and rt in hu: del hu[rt]; he.pop(rt, None)
        if op not in (15,) and rt in hu and 32 <= op <= 39: hu.pop(rt, None); he.pop(rt, None)   # loads overwrite rt
out = {hex(a): hex(c.most_common(1)[0][0]) for a, c in votes.items()}
json.dump(out, open(DATAJ, "w"), indent=0)
print(len(out), "data addresses")
import sys
for q in sys.argv[1:]:
    q = int(q, 16); near = sorted(votes, key=lambda a: abs(a - q))[:3]
    for a in near: print(f"  {q:#x}: ref {a:#x} -> {votes[a].most_common(2)}  => {q - a + votes[a].most_common(1)[0][0]:#x}")
