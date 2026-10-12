"""ps2build.py SRC.c [BASE] : ee-gcc -> ld.lld -> blob at BASE (default 0x1EC0000) -> pnach lines (+ hook)."""
import subprocess, sys, os, struct
from elftools.elf.elffile import ELFFile
HERE = os.path.dirname(os.path.abspath(__file__))
# ee-gcc 2.9 can't handle spaces or "!" in paths, so the folder two levels up is reached through a subst drive W:
SUBST_ROOT = os.path.dirname(os.path.dirname(HERE))
W = "W:" + os.sep + os.path.relpath(os.path.dirname(HERE), SUBST_ROOT)       # project folder as seen through W:
W_HERE = "W:" + os.sep + os.path.relpath(HERE, SUBST_ROOT)                  # this folder as seen through W:
# EE GCC 2.9 toolchain (from the recvx-decomp checkout); EE_GCC overrides (must be a path without spaces)
EE = os.environ.get("EE_GCC") or W + r"\ps2-decomp\compiler\windows\ee\gcc"
PCSX2_DIR = os.environ.get("PCSX2_DIR", r"C:\PCSX2")
LAB = "--lab" in sys.argv; PAL = "--pal" in sys.argv; JPN = "--jpn" in sys.argv; args = [a for a in sys.argv[1:] if a not in ("--lab", "--pal", "--jpn")]
REG = "pal" if PAL else "jpn" if JPN else "usa"
# --pal: SLES-50306 build (-DCVX_PAL). Its free RAM starts above the 60Hz patch cave at 0x1E46000 (pal60.py).
# --jpn: SLPM-65022 build (-DCVX_JPN). bss ends 0x1E3A780; free to 0x1FF9000 (stack above).
PNACH = os.path.join(PCSX2_DIR, "patches", {"pal": "SLES-50306_6EA9DDA9.pnach", "jpn": "SLPM-65022_D0CF2395.pnach", "usa": "SLUS-20184_24036809.pnach"}[REG])
BASES = {"pal": "deployed_bases_pal.txt", "jpn": "deployed_bases_jpn.txt", "usa": "deployed_bases.txt"}[REG]
src = args[0]
# Base address. A savestate holds the mod's code too, and is often taken while the CPU is inside it; if a new build
# were written over the same addresses, that state would resume in the middle of different code and hang. So each
# build goes to a base that doesn't overlap the build currently installed in PCSX2 (0x20000 per build, rotating
# through the free area 0x1E30000-0x1F00000): states saved with the previous build finish their frame in the old
# code, which stays intact, and continue on the new hooks.
SPAN, LO, HI = {"pal": (0x28000, 0x1E50000, 0x1F20000), "jpn": (0x28000, 0x1E40000, 0x1F10000), "usa": (0x28000, 0x1E30000, 0x1F00000)}[REG]
def installed_base():
    import re
    try:
        t = open(PNACH).read()
        sec = t.split("[CVX60" + chr(92) + "60 FPS (interpolated)]", 1)[1]
        return int(re.search(r"patch=1,EE,([0-9A-F]{8}),word", sec).group(1), 16)
    except Exception:
        return 0x1EC0000 if REG == "usa" else LO
# also avoid the last two RELEASE builds installed (the user's savestates are made with those): deployed_bases.txt
# is appended by patch_deploy.py ("rel 0x..." / "lab 0x...")
def recent_release_bases(n=2):
    try: return [int(l.split()[1], 16) for l in open(os.path.join(HERE, BASES)) if l.startswith("rel")][-n:]
    except Exception: return []
if len(args) > 1: base = int(args[1], 16)
else:
    avoid = [installed_base()] + recent_release_bases()
    base = None
    for k in range(LO, HI - SPAN + 1, 0x8000):
        cand = (avoid[0] + SPAN - LO + (k - LO)) % (HI - SPAN - LO + 0x8000) + LO   # start after the installed one
        if all(abs(cand - a) >= SPAN for a in avoid): base = cand; break
    if base is None: sys.exit(f"no free base avoiding {[hex(a) for a in avoid]}")
stem = os.path.splitext(src)[0] + {"pal": "_pal", "jpn": "_jpn", "usa": ""}[REG] + ("_lab" if LAB else "")
env = dict(os.environ, PATH=";".join([EE + r"\bin", EE + r"\ee\bin", EE + r"\lib\gcc-lib\ee\2.9-ee-991111", os.environ["PATH"]]))
def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode or r.stderr.strip(): print(r.stdout, r.stderr)
    if r.returncode: sys.exit(1)
if not os.path.exists(W_HERE):   # old gcc can't handle spaces or "!" in paths: reach the workspace through W:
    subprocess.run(["subst", "W:", SUBST_ROOT], capture_output=True)
import zlib, json
BUILD_ID = zlib.crc32(open(os.path.join(HERE, src), "rb").read()) | 1
run([EE + r"\bin\ee-gcc.exe", "-c", "-O2", "-G0", "-fno-common", "-mno-abicalls", "-fno-pic", "-Wall",
     "-DCVX_LAB" if LAB else "-DCVX_REL", {"pal": "-DCVX_PAL", "jpn": "-DCVX_JPN", "usa": "-DCVX_USA"}[REG], f"-DCVX_BUILD_ID={(BUILD_ID ^ (2 if LAB else 0)):#x}u", src, "-o", stem + ".o"], cwd=W_HERE, env=env)
# mini linker: one object, sections laid out in order at base; MIPS REL relocations (32, 26, HI16/LO16)
e = ELFFile(open(os.path.join(HERE, stem + ".o"), "rb"))
order = [n for n in (".text", ".rodata", ".data", ".sdata", ".sbss", ".bss") if e.get_section_by_name(n) and e.get_section_by_name(n)["sh_size"]]
addr, cur = {}, base
for n in order:
    sec = e.get_section_by_name(n); al = max(sec["sh_addralign"], 4); cur = (cur + al - 1) & ~(al - 1)
    addr[n] = cur; cur += sec["sh_size"]
bss_end = cur
if bss_end - base > SPAN: sys.exit(f"build too big for its {SPAN:#x} slot ({bss_end - base:#x})")
img = bytearray(cur - base)
for n in order:
    sec = e.get_section_by_name(n)
    if sec["sh_type"] == "SHT_PROGBITS": img[addr[n] - base:addr[n] - base + sec["sh_size"]] = sec.data()
symtab = e.get_section_by_name(".symtab"); syms = list(symtab.iter_symbols())
secname = {i: s.name for i, s in enumerate(e.iter_sections())}
bss_lo = min([addr[n] for n in (".sbss", ".bss") if n in addr] or [bss_end])
LINKER = {"__bss_start": bss_lo, "__bss_end": (bss_end + 3) & ~3}
def symval(si):
    s = syms[si]; shn = s["st_shndx"]
    if s.name in LINKER: return LINKER[s.name]
    if shn == "SHN_ABS": return s["st_value"]
    if isinstance(shn, int) and secname[shn] in addr: return addr[secname[shn]] + s["st_value"]
    raise SystemExit(f"unresolved symbol {s.name} ({shn})")
def rw(o): return struct.unpack_from("<I", img, o)[0]
def ww(o, v): struct.pack_into("<I", img, o, v & 0xFFFFFFFF)
for rs in e.iter_sections():
    if rs["sh_type"] != "SHT_REL": continue
    tgt = secname[rs["sh_info"]]
    if tgt not in addr: continue
    rels = list(rs.iter_relocations()); pending = []
    for r in rels:
        t = r["r_info_type"]; o = addr[tgt] - base + r["r_offset"]; S = symval(r["r_info_sym"]); P = addr[tgt] + r["r_offset"]
        if t == 2: ww(o, rw(o) + S)                                            # R_MIPS_32
        elif t == 4:                                                          # R_MIPS_26
            A = (rw(o) & 0x3FFFFFF) << 2; ww(o, (rw(o) & 0xFC000000) | (((A | (P & 0xF0000000)) + S) >> 2 & 0x3FFFFFF))
        elif t == 5: pending.append((o, S))                                   # R_MIPS_HI16 (paired with next LO16)
        elif t == 6:                                                          # R_MIPS_LO16
            lo = rw(o) & 0xFFFF; slo = lo - 0x10000 if lo & 0x8000 else lo
            for ho, hs in pending:
                ahl = ((rw(ho) & 0xFFFF) << 16) + slo; v = ahl + hs
                ww(ho, (rw(ho) & 0xFFFF0000) | (((v + 0x8000) >> 16) & 0xFFFF))
            pending = []
            ww(o, (rw(o) & 0xFFFF0000) | ((S + slo) & 0xFFFF))
        elif t == 0: pass
        else: raise SystemExit(f"unsupported reloc type {t}")
sym = {}
for i, s in enumerate(syms):
    if s.name and s["st_info"]["type"] in ("STT_FUNC", "STT_OBJECT", "STT_NOTYPE") and s["st_shndx"] not in ("SHN_UNDEF",):
        try: sym[s.name] = symval(i)
        except SystemExit: pass
blob = img[:max((addr[n] - base + e.get_section_by_name(n)["sh_size"]) for n in order if e.get_section_by_name(n)["sh_type"] == "SHT_PROGBITS")]
words = [struct.unpack("<I", bytes(blob[i:i + 4]).ljust(4, b"\0"))[0] for i in range(0, len(blob), 4)]
lines = [f"patch=1,EE,{base + 4 * i:08X},word,{w:08X}" for i, w in enumerate(words)]
def jal(target): return 0x0C000000 | ((target >> 2) & 0x3FFFFFF)
if "w_frame" in sym:   # cvx60_ps2: entry wrappers
    H = {"pal": dict(frame=0x12B430, light=0x137D10, alldraw=0x137D78, put=0x12EB30, door=0x133FCC, task6=0x30C0C8),
         "jpn": dict(frame=0x12B4B0, light=0x136F80, alldraw=0x136FE8, put=0x12EBB0, door=0x13393C, task6=0x302CC8),
         "usa": dict(frame=0x12B4B0, light=0x137730, alldraw=0x137798, put=0x12EBB0, door=0x133D4C, task6=0x303CC8)}[REG]
    lines += [f"patch=1,EE,{H['frame']:08X},word,{jal(sym['w_frame']):08X}",        # njUserMain: jal PS2_jikken
              f"patch=1,EE,{H['light']:08X},word,{jal(sym['w_after_logic']):08X}",  # bhMainSequence: jal bhControlLight
              f"patch=1,EE,{H['alldraw']:08X},word,{jal(sym['w_alldraw']):08X}",    # bhMainSequence: jal bhAllDrawModel
              f"patch=1,EE,{H['put']:08X},word,{0x08000000 | ((sym['w_putmodel'] >> 2) & 0x3FFFFFF):08X}",  # bhPutModel: j w_putmodel
              f"patch=1,EE,{H['put'] + 4:08X},word,00000000",
              f"patch=1,EE,{H['door']:08X},word,{jal(sym['w_controldoor']):08X}"]   # bhSysCallDoordemo: jal bhControlDoor
    if "w_syscallgame" in sym: lines.append(f"patch=1,EE,{H['task6']:08X},word,{sym['w_syscallgame']:08X}")   # lab: task 6 (bhSysCallPad)
else:
    lines.append(f"patch=1,EE,0012B4B0,word,{jal(sym['cvx_frame']):08X}")   # PoC: njUserMain: jal PS2_jikken -> cvx_frame
open(os.path.join(HERE, stem + ".pnach.txt"), "w").write("\n".join(lines) + "\n")
json.dump(sym, open(os.path.join(HERE, stem + ".syms.json"), "w"), indent=0)
print(f"{stem}: base {base:#x}, blob {len(blob):#x} bytes, bss to {bss_end:#x}, {len(lines)} pnach lines")
