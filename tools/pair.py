"""pair.py PAL_FN JP_FN [n]: line up the ordered calls (bl), r13 and r2 references of a PAL function and its JP
counterpart (difflib on reference kinds) to read off JP addresses for callees and SDA offsets."""
import sys, os, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ".")
from dol import Dol
P = Dol("disc1/sys/main.dol"); J = Dol("jpn1/sys/main.dol")
SYMS = {}
for l in open("pal_symbols.txt"):
    p = l.split()
    try: SYMS[int(p[1], 16)] = p[0]
    except (ValueError, IndexError): pass

def refs(d, a, end=None, maxn=4000):
    out = []
    for i in range(maxn):
        x = a + 4 * i
        w = d.u32(x); op, rt, ra, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm
        if op == 18 and w & 1:
            off = w & 0x3FFFFFC
            if off & 0x2000000: off -= 0x4000000
            out.append(("bl", x, x + off))
        elif ra in (2, 13) and (op == 14 or 32 <= op <= 55):
            out.append((f"r{ra}", x, simm))
        if i > 2 and (w == 0x4E800020) and (end is None or x >= end):   # blr
            break
    return out

def pair(pa, ja, show=True):
    A, B = refs(P, pa), refs(J, ja)
    sa = [k if k != "bl" else "bl" for k, _, _ in A]; sb = [k for k, _, _ in B]
    res = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, sa, sb, autojunk=False).get_opcodes():
        if tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                res.append((A[i], B[j]))
        elif show:
            res.append((("--" + tag, 0, [hex(v if k == "bl" else v) for k, _, v in A[i1:i2]]), ("", 0, [hex(v) for k, _, v in B[j1:j2]])))
    if show:
        for (k, xa, va), (_, xb, vb) in res:
            if k.startswith("--"): print(f"   {k}: PAL {va}  JP {vb}"); continue
            name = SYMS.get(va, "") if k == "bl" else ""
            print(f"{k:3} PAL {va:#010x} {name:30} JP {vb:#010x}" if k == "bl" else f"{k:3} PAL {va:#x} -> JP {vb:#x}")
    return res

if __name__ == "__main__":
    pair(int(sys.argv[1], 16), int(sys.argv[2], 16))
