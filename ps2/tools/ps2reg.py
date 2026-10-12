"""ps2reg.py: which PS2 region the mapping tools target. REG=eu (default, SLES-50306) or REG=jp (SLPM-65022)."""
import os
REG = os.environ.get("REG", "eu")
ELF = {"eu": "ps2eu/SLES_503.06", "jp": "ps2jp/SLPM_650.22"}[REG]
MAPJ, DATAJ = f"ps2{REG}_map.json", f"ps2{REG}_data.json"
