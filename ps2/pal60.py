"""pal60.py: generate the SLES-50306 (PS2 PAL) "60Hz" pnach section -> ps2mod/pal60.pnach.txt

PAL CVX runs the same per-tick game logic as USA, one tick per 2 vblanks, so at 50Hz it plays at 25 ticks/s (17% slow).
Switching the GS to NTSC 60Hz restores USA speed. On top of the video-mode switch, PAL changed a handful of
constants for 25 ticks/s; those that count ticks are put back to the USA values. Everything PAL counts in 50ths of
a second (play time sys->time, the event countdown evt_tim, and what they're compared or displayed with: bhDispTime,
ranking thresholds, the countdown voice, save files) is left in PAL units; the two places that advance those
counters are slowed to 50 units/s instead (code cave at CAVE).
Every reverted word is checked against the USA word at the same place in the matched function (ps2eu_map.json)."""
import json, os, struct, sys
# --480p: "60Hz Mode (480p progressive)" variant -> pal60p.pnach.txt. Video setup from PCSX2's built-in No-Interlacing patch
# for this disc (felixthecat1970), applied on ELF load so it reaches Ps2Init (as a patch=1 cheat it lands after Ps2Init
# has run, so on its own it stays 50Hz interlaced); the timing fixes below are the same for both variants.
P480 = "--480p" in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
def load(p):
    d = open(os.path.join(ROOT, p), "rb").read(); return lambda a: struct.unpack_from("<I", d, 0x80 + a - 0x100000)[0]
US, EU = load("ps2us/SLUS_201.84"), load("ps2eu/SLES_503.06")
MAP = sorted((int(v[1], 16), int(v[0], 16), v[2], k) for k, v in json.load(open(os.path.join(ROOT, "ps2eu_map.json"))).items())
def usa_word(pa):
    for ea, ua, sz, n in MAP:
        if ea <= pa < ea + sz: return US(ua + pa - ea), n
    raise SystemExit(f"{pa:#x}: not in a mapped function")
lines = []
def put(a, w, why): lines.append((a, w, why))
def revert(a, why, expect_pal=None):
    w, fn = usa_word(a)
    if expect_pal is not None and EU(a) != expect_pal: raise SystemExit(f"{a:#x} ({fn}): PAL word {EU(a):08x} != {expect_pal:08x}")
    put(a, w, f"{fn}: {why}")

def low(a, v, bits, expect):   # replace the low byte/half of a word (the No-Interlacing patch's 8/16-bit writes)
    assert EU(a) == expect, hex(a); m = (1 << bits) - 1; put(a, (EU(a) & ~m & 0xFFFFFFFF) | v, "480p")
if P480:
    # --- video mode: 480p progressive (DTV 640x480 60Hz, mode 0x50) ---
    assert EU(0x2D25D0) == 0x24050001 and EU(0x2D25E0) == 0x70003E28
    put(0x2D25D0, 0x0000282D, "480p: sceGsResetGraph interlace 1 -> 0")
    low(0x2D25D4, 0x50, 8, 0x24060003)                    # sceGsResetGraph mode PAL(3) -> DTV 480p (0x50)
    put(0x2D25E0, 0, "480p: ffmode")
    assert EU(0x1002F4) == 0x14A40029; put(0x1002F4, 0x10A40029, "480p: sceGsSetDefDispEnv mode branch")
    low(0x10030C, 0x02D0, 16, 0x260209FF)                 # sceGsSetDefDispEnv: DX
    low(0x100370, 0x23, 8, 0x26450019)                    # sceGsSetDefDispEnv: DY
    low(0x100398, 0x0134, 16, 0x64E3027C)                 # sceGsSetDefDispEnv: DX
    assert EU(0x2F3D60) == 0x1043FFFA; put(0x2F3D60, 0x1443FFFA, "480p: field-wait loop (no fields in progressive)")
    assert EU(0x29CBD0) == 0x24030001; put(0x29CBD0, 0x0000182D, "480p: SetAdjustDisplay off (interlaced offsets)")
    assert EU(0x2D27CC) == 0x3C010114 and EU(0x2D27D0) == 0x8C2243C8
    put(0x2D27CC, 0x0C0B49FD, "480p: Ps2Init skips the interlaced DISPLAY writes (jal 0x2D27F4 = ClearVram + rest)")
    put(0x2D27D0, 0, "480p"); put(0x2D27FC, 0, "480p")
else:
    # --- video mode: NTSC 640x480 interlaced, NTSC display position ---
    revert(0x2D25D4, "sceGsResetGraph mode PAL(3) -> NTSC(2)", 0x24060003)
    revert(0x2D2678, "DISPLAY position (NTSC)", 0x3C0A0006)
    revert(0x2D267C, "DISPLAY position (NTSC)", 0x3C01002A)
    revert(0x2E9084, "njAdjustDisplay NTSC offset", 0x24420060)
    revert(0x2E90A0, "njAdjustDisplay NTSC offset", 0x244202AC)
for a in (0x132510, 0x132B5C, 0x2B4A2C, 0x2B7994, 0x2B8298):                      # njSetAspect(.., 1.07 -> 1.0)
    assert EU(a) == 0x3C023F88 and EU(a + 4) == 0x3442F5C3
    put(a, 0x3C023F80, "njSetAspect y 1.07 (PAL) -> 1.0"); put(a + 4, 0, "njSetAspect y: drop ori")
def float_imm(a, pal, why):   # keep PAL's lui register, take the USA float
    assert EU(a) & 0xFFFF == pal and EU(a) >> 26 == 15, hex(a)
    put(a, (EU(a) & 0xFFFF0000) | (usa_word(a)[0] & 0xFFFF), f"{usa_word(a)[1]}: {why}")
# --- per-tick counts that PAL scaled for 25 ticks/s ---
revert(0x13AEA4, "tick count 26 -> 31", 0x2841001A)
revert(0x13CA84, "tick count 251 -> 301", 0x284100FB)
revert(0x29BCFC, "room fade-in 37 -> 42 ticks", 0x24070025)
revert(0x29C618, "movie fade 25 -> 30 ticks", 0x24020019)
revert(0x2D1B44, "fps meter period 50 -> 60", 0x28630032)
assert EU(0x137224) == 0x28632328 and US(0x136DD4) == 0x28632A30   # bhSysCallScreenSaver (size differs: not in map)
put(0x137224, US(0x136DD4), "bhSysCallScreenSaver: screensaver idle 9000 -> 10800 ticks")
for a in (0x2C9AE4, 0x2C9D24): float_imm(a, 0x42FA, "logo time 125.0 -> 150.0 ticks")   # Adv warning / Capcom logo
float_imm(0x2CB690, 0x443B, "title idle 750.0 -> 900.0 ticks")
float_imm(0x2C8328, 0x45EA, "screensaver 7500.0 -> 9000.0 ticks")
# sound fades / Adv fades: ticks = (ms/100)*25 -> *30 (PAL 4 instructions, USA 3 + nop)
for a in (0x294C20, 0x294E20, 0x296DE4, 0x29B9B4, 0x2C7A3C):
    for k in range(3): revert(a + 4 * k, "fade ticks *25 -> *30")
    put(a + 12, 0, "fade ticks: nop")

# --- 50 units/s counters (code cave) ---
CAVE = 0x1E46000; CNT_EVT, CNT_TIME = CAVE + 0x100, CAVE + 0x104
def hi(x): return ((x + 0x8000) >> 16) & 0xFFFF
def lo(x): return x & 0xFFFF
def I(op, rs, rt, imm): return (op << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)
def R(rs, rt, rd, sa, fn): return (rs << 21) | (rt << 16) | (rd << 11) | (sa << 6) | fn
def J(t): return 0x08000000 | ((t >> 2) & 0x3FFFFFF)
AT, V1, A0, A1, A2, T0, T1 = 1, 3, 4, 5, 6, 8, 9
NOP = 0
def LUI(rt, i): return I(15, 0, rt, i)
def LW(rt, off, b): return I(35, b, rt, off)
def SW(rt, off, b): return I(43, b, rt, off)
def ADDIU(rt, rs, i): return I(9, rs, rt, i)
def SLTI(rt, rs, i): return I(10, rs, rt, i)
def BEQ(rs, rt, off): return I(4, rs, rt, off)
def BNE(rs, rt, off): return I(5, rs, rt, off)
def BGEZ(rs, off): return I(1, rs, 1, off)
def MOVE0(rd): return R(0, 0, rd, 0, 0x21)
def wrap6(cnt):   # t0 = &cnt; t1 = (cnt + 1) % 6; cnt = t1
    return [LUI(T0, hi(cnt)), LW(T1, lo(cnt), T0), ADDIU(T1, T1, 1), SLTI(AT, T1, 6),
            BNE(AT, 0, 2), NOP, MOVE0(T1), SW(T1, lo(cnt), T0)]
# evt_tim (bhControlVSync, per tick): PAL "-= 2" (50/s at 25 ticks/s) -> 2,2,2,2,1,1 per 6 ticks (50/s at 30 ticks/s)
# a1 = evt_tim, a2 = &evt_tim; clamps at 0 (game over tests evt_tim == 0)
evt = wrap6(CNT_EVT) + [ADDIU(V1, A1, -2), BEQ(T1, 0, 3), SLTI(AT, T1, 5), BNE(AT, 0, 2), NOP, ADDIU(V1, V1, 1),
                        BGEZ(V1, 2), NOP, MOVE0(V1), SW(V1, 0, A2), J(0x2D1C30), NOP]
# sys->time (vsync interrupt, per vblank): skip every 6th vblank -> 50/s at 60Hz.  a0 = sys, v1 = time
EVT_AT = CAVE; TIME_AT = CAVE + 4 * len(evt)
tim = wrap6(CNT_TIME) + [BEQ(T1, 0, 3), NOP, ADDIU(V1, V1, 1), SW(V1, 0x8A0, A0), J(0x2E8B4C), NOP]
assert TIME_AT + 4 * len(tim) <= CNT_EVT
for k, w in enumerate(evt + tim): put(CAVE + 4 * k, w, "cave")
# (no lines for the counters: patch=1 lines are re-applied every frame; that RAM is zero and any value wraps)
if EU(0x2D1C28) != 0x24A3FFFE or EU(0x2D1C2C) != 0xACC30000: raise SystemExit("evt_tim site mismatch")
if EU(0x2E8B44) != 0x24630001 or EU(0x2E8B48) != 0xAC8308A0: raise SystemExit("time site mismatch")
put(0x2D1C28, J(EVT_AT), "bhControlVSync: evt_tim -= 2 -> cave"); put(0x2D1C2C, NOP, "")
put(0x2E8B44, J(TIME_AT), "vsync_func: sys->time++ -> cave"); put(0x2E8B48, NOP, "")

# --- savestates made in PAL mode: Ps2Init already ran with PAL settings, so once per frame (njUserMain, in place of
# its call to bhCheckSoftReset) check libgraph's output mode; if it is PAL (3; leaves e.g. No-Interlacing's 480p
# alone) switch the CRT to NTSC (SetGsCrt, no GS reset), replay Ps2Init's double-buffer/display setup with the NTSC
# values (minus ClearVram), and raise SystemAdjustFlag so the game re-applies the user's screen offset.
SW_AT = CAVE + 0x200
def SH(rt, off, b): return I(41, b, rt, off)
def LH(rt, off, b): return I(33, b, rt, off)
def JAL(t): return 0x0C000000 | ((t >> 2) & 0x3FFFFFF)
def SD(rt, off, b): return I(63, b, rt, off)
def LD(rt, off, b): return I(55, b, rt, off)
SP, RA, V0, A3, T2 = 29, 31, 2, 7, 10
assert EU(0x12B438) == JAL(0x2D2340) and EU(0x2D27F8) == JAL(0x2EF2A0) and EU(0x2D25E4) == JAL(0x100A18)
patched = {a: w for a, w, _ in lines}
if P480:   # gparam = {interlace 0, mode 0x50, ffmode 0}; SetGsCrt(0, 0x50, 0); replay up to the skipped DISPLAY writes
    seg = [patched.get(a, EU(a)) for a in range(0x2D25EC, 0x2D27CC, 4)]
    body = [LH(T0, 2, V0), ADDIU(AT, 0, 3), BNE(T0, AT, 0), NOP,
            SH(0, 0, V0), ADDIU(T0, 0, 0x50), SH(T0, 2, V0), SH(0, 4, V0),
            ADDIU(A0, 0, 0), ADDIU(A1, 0, 0x50), JAL(0x10B760), ADDIU(A2, 0, 0)] + seg
else:
    seg = [patched.get(a, EU(a)) for a in range(0x2D25EC, 0x2D27F8, 4)] + [EU(0x2D27FC)]
    body = [LH(T0, 2, V0), ADDIU(AT, 0, 3), BNE(T0, AT, 0), NOP,
            ADDIU(T0, 0, 2), SH(T0, 2, V0), ADDIU(A0, 0, 1), ADDIU(A1, 0, 2), JAL(0x10B760), ADDIU(A2, 0, 0)] + seg +            [LUI(AT, hi(0x50D2B8)), ADDIU(T0, 0, 1), SW(T0, lo(0x50D2B8), AT)]
body[2] = BNE(T0, AT, len(body) - 3)          # -> DONE (first word after body)
sw = [ADDIU(SP, SP, -0x20), SD(RA, 0x10, SP), JAL(0x1001D0), NOP] + body +      [LD(RA, 0x10, SP), J(0x2D2340), ADDIU(SP, SP, 0x20)]
assert SW_AT + 4 * len(sw) <= CAVE + 0x800
for k, w in enumerate(sw): put(SW_AT + 4 * k, w, "cave")
put(0x12B438, JAL(SW_AT), "njUserMain: jal bhCheckSoftReset -> PAL-state switch (tail-calls it)")

out = [f"patch=2,EE,{a:08X},word,{w:08X}" for a, w, _ in lines]   # 2 = on ELF load (before Ps2Init runs) + every frame
open(os.path.join(HERE, "pal60p.pnach.txt" if P480 else "pal60.pnach.txt"), "w").write("\n".join(out) + "\n")
for a, w, why in lines:
    if why != "cave": print(f"{a:08X} {EU(a) if a < 0x400000 else 0:08X} -> {w:08X}  {why}")
print(len(out), "lines")
