"""pal_deploy.py [--480p] [--remove] : install the SLES-50306 (PS2 PAL) patches as PCSX2 *patches* (Game Properties > Patches).
User patch file = PCSX2's built-in SLES-50306 patches (resources/patches.zip, unchanged) + our sections:
  "60Hz Mode (NTSC)"          <- ps2mod/pal60.pnach.txt  (pal60.py)
  "60Hz Mode (480p progressive)" <- ps2mod/pal60p.pnach.txt (pal60.py --480p)
  (both 60Hz modes are written; only one is enabled: NTSC, or 480p with --480p. No-Interlacing gets disabled.)
  "CVX60\\60 FPS (interpolated)" <- ps2mod/cvx60_ps2_pal.pnach.txt, when it exists (needs 60Hz Mode)
Each section present is enabled in gamesettings [Patches]. Touches nothing else."""
import sys, zipfile, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.environ.get("PCSX2_DIR", r"C:\PCSX2")   # PCSX2 folder (PCSX2_DIR overrides)
KEY = "SLES-50306_6EA9DDA9"
UP = os.path.join(P, "patches", KEY + ".pnach"); GS = os.path.join(P, "gamesettings", KEY + ".ini")
SECTIONS = [("60Hz Mode (NTSC)", "pal60.pnach.txt", "SAFE FALLBACK. Runs the PAL version at 60Hz (480i interlaced) with NTSC-speed game logic (PAL plays 17% slow at 50Hz). Use this only if 60Hz Mode (480p progressive) gives you problems. Do NOT enable both 60Hz Modes at the same time."),
            ("60Hz Mode (480p progressive)", "pal60p.pnach.txt", "RECOMMENDED. Runs the PAL version at 60Hz with 480p progressive output and NTSC-speed game logic (video setup from the No-Interlacing patch by felixthecat1970). Do NOT enable both 60Hz Modes at the same time, and do not combine with No-Interlacing (this replaces it). If you have problems, use 60Hz Mode (NTSC) instead."),
            ("CVX60" + chr(92) + "60 FPS (interpolated)", "cvx60_ps2_pal.pnach.txt", "True 60fps: interpolated extra frame per game tick. Requires one (only one) of the 60Hz Modes: 480p progressive recommended, NTSC as a safe fallback.")]
base = zipfile.ZipFile(os.path.join(P, "resources", "patches.zip")).read(KEY + ".pnach").decode("utf-8").replace("\r\n", "\n").rstrip("\n") + "\n"
installed = []
if "--remove" in sys.argv:
    if os.path.exists(UP): os.remove(UP)
else:
    text = base
    for name, f, desc in SECTIONS:
        fp = os.path.join(HERE, f)
        if not os.path.exists(fp): continue
        body = open(fp).read().strip()
        if f.startswith("cvx60"):   # log the installed base so the next build can avoid it (savestates hold the old code)
            b = int(re.search(r"patch=1,EE,([0-9A-F]{8}),word", body).group(1), 16)
            open(os.path.join(HERE, "deployed_bases_pal.txt"), "a").write(f"rel {b:#x}\n")
        extra = "gsinterlacemode=1\n" if f == "pal60p.pnach.txt" else ""   # (as the No-Interlacing section: deinterlacing off)
        text += f"\n[{name}]\n{extra}author=CVX60\ndescription={desc}\n{body}\n"
        if not f.startswith("pal60") or f == ("pal60p.pnach.txt" if "--480p" in sys.argv else "pal60.pnach.txt"): installed.append(name)
    open(UP, "w", encoding="utf-8", newline="\r\n").write(text)
g = open(GS, encoding="utf-8").read().replace("\r\n", "\n") if os.path.exists(GS) else ""
for name in [n for n, _, _ in SECTIONS] + ["No-Interlacing"]: g = g.replace(f"Enable = {name}\n", "")   # (480p mode supersedes No-Interlacing)
if installed:
    if "[Patches]\n" not in g: g = g.rstrip("\n") + ("\n\n" if g.strip() else "") + "[Patches]\n"
    g = g.replace("[Patches]\n", "[Patches]\n" + "".join(f"Enable = {n}\n" for n in installed), 1)
open(GS, "w", encoding="utf-8", newline="\r\n").write(g)
print("user patch file:", os.path.exists(UP), " enabled:", installed)
