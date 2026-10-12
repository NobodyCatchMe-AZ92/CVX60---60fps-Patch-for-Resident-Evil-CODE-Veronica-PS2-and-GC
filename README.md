# CVX60: true 60fps for Resident Evil CODE: Veronica X (GameCube and PS2)

CVX60 makes RE CODE: Veronica X render at 60fps **without speeding anything up**: an Action Replay code
for the GameCube versions in Dolphin and a patch for the PS2 versions in PCSX2. The game still runs its
logic at its native 30 ticks per second, so timers, enemy AI, animations, physics, audio and input are
exactly as in the original. Each tick is shown as two frames:

1. a frame halfway between the previous tick and this one (camera, characters, enemies and effects
   interpolated),
2. the exact frame of this tick.

Smooth at 60: Chris/Claire, enemies, the camera, shadows, gun flashes, sparks/smoke, shell casings, blood
spray, poison clouds, snow, in-game cutscenes, subtitles and message boxes, door transitions, alarm-light
rooms, the sniper scope and the self-destruct countdown (GameCube also the Battle Game timer). Menus,
inventory, map and FMVs stay at 30. About one extra frame (16 ms) of display latency.

## Downloads

Get the ready-to-use files from the **Releases** page:

- `CVX60-v2.0-GameCube.zip`: Dolphin, game IDs GCDP08 (PAL), GCDE08 (USA), GCDJ08 (Japan).
- `CVX60-v2.0-PS2.zip`: PCSX2, serials SLES-50306 (PAL), SLUS-20184 (USA), SLPM-65022 (Japan).

Each zip has one folder per region with a ready-made file (Dolphin game settings `.ini` / PCSX2 `.pnach`)
and the same code as plain text to add by hand, plus a README with install steps. The generated codes are
also in this repository: `cvx60_ar.txt` (GC PAL), `cvx60_usa_ar.txt` (GC USA), `cvx60_jpn_ar.txt` (GC Japan).

### Notes

- GameCube PAL needs a 60Hz code as well (the releases include "Enable 60hz Output for PAL version" by
  Ralf@gc-forever). CVX60 does nothing at 50Hz.
- PS2 PAL runs at 50Hz and plays 17% slow (25 updates per second instead of 30). The PAL release includes two
  "60Hz Mode" patches that run it at 60Hz at the intended speed: **480p progressive (recommended)** or NTSC
  480i (safe fallback). Enable exactly one. Speed-related constants PAL changed are restored, and play time
  and the countdown stay in PAL units, so PAL saves are unaffected. 50Hz savestates switch over when loaded.
- Savestates contain the mod's code and state: after updating CVX60, make new savestates (an old one may
  freeze). Memory card saves are unaffected.
- GameCube USA: don't combine with a "Door Skip" code that patches `0x80169FAC` (CVX60 hooks it).

## How it works (technical)

GameCube (`cvx60.c`, PowerPC, linked into free OS arena memory above the game's heaps):

- Hooks the main loop's `njWaitVSync` call, the logic/draw seam in `bhMainSequence`, the draw-all calls and
  `bhPutModel`.
- Frame A: per-bone world matrices and the view matrix are blended halfway between the previous and current
  tick (camera by eye position + orientation, bones renormalised); lights are re-applied for the blended camera.
  Effects (shadows, sparks, casings, particles, blood, snow) are drawn at their in-between positions and
  restored afterwards.
- Frame B: a draw-only pass with the tick's own camera, bones and lights, presented one field later, without
  the end-of-render callback or sound sync, so no game state advances. Message windows, the countdown, the
  Battle Game timer, the scope and screen fades are redrawn by the game's own draw code with their state saved
  and restored.
- Door transitions: the scene is redrawn by the game's own `bhControlDoor` with its logic paused, once at the
  midpoint and once exact.
- Falls back to vanilla 30fps for anything unusual (menus, inventory/map, mirrors, thermal view, FMVs, pause),
  and drops frame B when a cut relocates the camera after the draw, so cuts stay clean.

PS2 (`ps2/cvx60_ps2.c`, C89 for EE GCC 2.9, loaded into free RAM above the game's memory by PCSX2 patch lines):
the same scheme, ported to the PS2 engine (row-vector matrices, the non-rigid PS2 view matrix, the EE FPU's
non-IEEE rounding). One source builds all three regions; only addresses differ (`RG(usa, pal, jpn)`).
`ps2/pal60.py` generates the PAL 60Hz Modes.

## Known limits

- Mirror rooms and the thermal view run at the original 30fps; the lighter flame flicker, Claire's blinking
  and a few special effects animate at 30 (PS2: also damage effects and animated room objects).
- GameCube USA/Japan have less free memory: in very crowded scenes some characters are drawn without
  smoothing (the player always is).

## Building

GameCube: Python 3.10+ with `pip install ziglang pyelftools` (`capstone` optional). `build.py` compiles
`cvx60.c` with Zig's clang (`powerpc-freestanding-eabihf`, `-mcpu=750`) and emits the AR code;
`--usa` / `--jpn` for the other regions, `--lab` adds diagnostics (don't ship lab builds). `deploy.py` writes the
code into Dolphin's GameSettings ini.

PS2: Python 3.10+ with `pyelftools`, and the EE GCC 2.9 toolchain from a
[recvx-decomp](https://github.com/AshfordFamily/recvx-decomp) checkout (`ps2-decomp/` next to `ps2/`, or set
`EE_GCC`; the old compiler can't handle spaces or `!` in paths, so `ps2build.py` reaches the project through a
`subst W:` drive). `ps2/ps2build.py cvx60_ps2.c [--pal|--jpn]` builds the patch lines; `ps2/patch_deploy.py`
(USA, `--jpn`) and `ps2/pal_deploy.py` (PAL, `--480p`) install them into PCSX2 (set `PCSX2_DIR`).
`ps2/pal60.py` and the `ps2/tools` scripts need your own game executables (`ps2us/SLUS_201.84`,
`ps2eu/SLES_503.06`, `ps2jp/SLPM_650.22`) and the decomp's `config/symbol_addrs.txt`; run them from the project
root.

## Credits

Built with AI assistance (Claude). Engine names and structure come from the community decompilations of
CODE: Veronica X: [recvx-decomp (PS2)](https://github.com/AshfordFamily/recvx-decomp) and
[recvx-gc-decomp](https://github.com/fmil95/recvx-gc-decomp). Ghidra + GameCube Loader for analysis.
GameCube PAL 60Hz code by Ralf@gc-forever. The PS2 PAL 480p video setup comes from PCSX2's "No-Interlacing"
patch for this game by felixthecat1970. No game code or assets are included.
