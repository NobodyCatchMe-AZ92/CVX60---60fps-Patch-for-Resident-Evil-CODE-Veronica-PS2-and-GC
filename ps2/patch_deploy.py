"""patch_deploy.py LINES_FILE [--jpn] [--remove]: install CVX60 as a PCSX2 *patch* (Game Properties > Patches) for USA
SLUS-20184 (default) or JP SLPM-65022 (--jpn). (PAL SLES-50306: pal_deploy.py.)
User patch file = PCSX2's built-in SLUS-20184 patches (from resources/patches.zip, unchanged) + our section, so the
user's widescreen / door-skip / logo-skip patches stay available whether PCSX2 merges or overrides. Enabled via
[Patches] in gamesettings. Touches nothing else."""
import sys, zipfile, os
P = os.environ.get("PCSX2_DIR", r"C:\PCSX2")   # PCSX2 folder (PCSX2_DIR overrides)
NAME = "CVX60" + chr(92) + "60 FPS (interpolated)"
KEY = "SLPM-65022_D0CF2395" if "--jpn" in sys.argv else "SLUS-20184_24036809"
UP = os.path.join(P, "patches", KEY + ".pnach"); GS = os.path.join(P, "gamesettings", KEY + ".ini")
base = zipfile.ZipFile(os.path.join(P, "resources", "patches.zip")).read(KEY + ".pnach").decode("utf-8").replace("\r\n", "\n").rstrip("\n") + "\n"
if "--remove" in sys.argv:
    if os.path.exists(UP): os.remove(UP)
else:
    body = open(sys.argv[1]).read().strip()
    import re as _re   # log the installed base so the next build can avoid it (savestates hold the old code)
    _b = int(_re.search(r"patch=1,EE,([0-9A-F]{8}),word", body).group(1), 16)
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "deployed_bases_jpn.txt" if "--jpn" in sys.argv else "deployed_bases.txt"), "a").write(("lab" if "_lab" in sys.argv[1] else "rel") + f" {_b:#x}\n")
    open(UP, "w", encoding="utf-8", newline="\r\n").write(base + f"\n[{NAME}]\nauthor=CVX60\ndescription=True 60fps: interpolated extra frame per game tick\n{body}\n")
g = open(GS, encoding="utf-8").read().replace("\r\n", "\n")
line = f"Enable = {NAME}\n"
g = g.replace(line, "")                       # remove from wherever it is ([Cheats] or [Patches])
if "--remove" not in sys.argv:
    if "[Patches]\n" not in g: g = g.rstrip("\n") + ("\n\n" if g.strip() else "") + "[Patches]\n"
    g = g.replace("[Patches]\n", "[Patches]\n" + line, 1)
open(GS, "w", encoding="utf-8", newline="\r\n").write(g)
print("user patch file:", os.path.exists(UP), " enabled in [Patches]:", "[Patches]\n" + line in g)
