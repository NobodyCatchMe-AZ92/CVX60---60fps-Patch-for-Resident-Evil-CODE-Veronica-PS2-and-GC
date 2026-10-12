"""ps2dis.py ADDR [N] : disassemble SLUS_201.84 (EE, little-endian) with symbol names from the decomp's symbol_addrs."""
import sys, struct, re, capstone, os, json
REG = os.environ.get("REG") or ("eu" if os.environ.get("PAL") == "1" else "us")   # REG=eu|jp (or PAL=1): symbols via ps2<reg>_map.json
PAL = REG != "us"
ELF = open({"us": "ps2us/SLUS_201.84", "eu": "ps2eu/SLES_503.06", "jp": "ps2jp/SLPM_650.22"}[REG], "rb").read()
def rd(a, n): o = a - 0x100000 + 0x80; return ELF[o:o + n]
def u32(a): return struct.unpack("<I", rd(a, 4))[0]
SYM = {}
for l in open("ps2-decomp/config/symbol_addrs.txt"):
    m = re.match(r"(\w+)\s*=\s*0x([0-9A-Fa-f]+);", l)
    if m: SYM[int(m.group(2), 16)] = m.group(1)
if PAL: SYM = {int(v[1], 16): k for k, v in json.load(open(f"ps2{REG}_map.json")).items()}
ADDR = {v: k for k, v in SYM.items()}
md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS64 + capstone.CS_MODE_LITTLE_ENDIAN)
def dis(a, n=40):
    out = []
    for k in range(n):
        x = a + 4 * k; w = u32(x); ins = list(md.disasm(rd(x, 4), x))
        if not ins: out.append(f"{x:08x}: .word {w:08x}"); continue
        i = ins[0]; s = f"{x:08x}: {i.mnemonic} {i.op_str}"
        if w >> 26 in (2, 3):
            t = ((x + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2); s = f"{x:08x}: {'jal' if w >> 26 == 3 else 'j'} {t:#x}   <{SYM.get(t, '?')}>"
        out.append(s)
    return out
if __name__ == "__main__":
    a = sys.argv[1]; a = ADDR[a] if a in ADDR else int(a, 16)
    print("\n".join(dis(a, int(sys.argv[2]) if len(sys.argv) > 2 else 40)))
