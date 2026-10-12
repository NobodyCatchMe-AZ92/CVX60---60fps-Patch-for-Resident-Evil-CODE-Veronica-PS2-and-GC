"""propagate.py: map PAL -> JP functions/SDA offsets/absolute data by walking the call graph from anchors.
Each mapped (PAL, JP) function pair is lined up by pair.refs (ordered bl / r13 / r2 / abs refs); equal-kind runs
give callee and offset correspondences, counted as votes. Writes jp_map.json."""
import sys, os, json, difflib, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ".")
from pair import P, J, SYMS

def refs(d, a, maxn=6000):
    out = []; lis = {}
    for i in range(maxn):
        x = a + 4 * i
        try: w = d.u32(x)
        except Exception: break
        op, rt, ra, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm
        if op == 15 and ra == 0: lis[rt] = imm
        elif op == 18 and w & 1:
            off = w & 0x3FFFFFC
            if off & 0x2000000: off -= 0x4000000
            out.append(("bl", x + off))
        elif ra in (2, 13) and (op == 14 or 32 <= op <= 55):
            out.append((f"r{ra}", simm))
        elif ra in lis and (op in (14, 24) or 32 <= op <= 55):
            hi = lis[ra]
            out.append(("abs", ((hi << 16) | imm) if op == 24 else ((hi << 16) + simm) & 0xFFFFFFFF))
        if w == 0x4E800020 and i > 2:
            # stop at the first blr unless a branch inside the function jumps past it (simple heuristic: peek next)
            nxt = d.u32(x + 4)
            if (nxt & 0xFFFF0000) == 0x94210000 or nxt == 0: break
    return out

def run(anchors, limit=3000):
    fmap = dict(anchors); votes = collections.defaultdict(collections.Counter)
    q = list(anchors.items()); seen = set()
    while q and len(seen) < limit:
        pa, ja = q.pop(0)
        if pa in seen: continue
        seen.add(pa)
        A, B = refs(P, pa), refs(J, ja)
        sm = difflib.SequenceMatcher(None, [k for k, _ in A], [k for k, _ in B], autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != "equal": continue
            for (k, va), (_, vb) in zip(A[i1:i2], B[j1:j2]):
                votes[k][(va, vb)] += 1
                if k == "bl" and va not in fmap:
                    fmap[va] = vb; q.append((va, vb))
    return fmap, votes

if __name__ == "__main__":
    anchors = {int(k, 16): int(v, 16) for k, v in json.loads(sys.argv[1]).items()}
    fmap, votes = run(anchors)
    # consistency: a PAL item mapped to several JP values
    best = {}
    for k, c in votes.items():
        per = collections.defaultdict(collections.Counter)
        for (va, vb), n in c.items(): per[va][vb] += n
        best[k] = {va: cc.most_common(2) for va, cc in per.items()}
    json.dump({k: {hex(va) if k != "r13" and k != "r2" else str(va): [[hex(v) if k not in ("r13", "r2") else v, n] for v, n in lst] for va, lst in d.items()} for k, d in best.items()},
              open("jp_map.json", "w"), indent=0)
    print("functions mapped:", len(fmap), " r13 offsets:", len(best.get("r13", {})), " r2:", len(best.get("r2", {})), " abs:", len(best.get("abs", {})))
