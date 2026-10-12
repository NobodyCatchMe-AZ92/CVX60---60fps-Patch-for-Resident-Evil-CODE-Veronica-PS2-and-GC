"""Read (and, explicitly, write) PCSX2's emulated PS2 EE RAM (32 MiB, little-endian) from outside the process.
Finds EE RAM by locating the game's ELF code (SLUS_201.84 bytes at EE 0x100000+0x1000) in a readable region.
CLI: python pmem.py base | r32 <addr> [n] | rf <addr> [n]"""
import ctypes, ctypes.wintypes as wt, struct, subprocess, sys, os
from dmem import MBI, k32, PROCESS_VM_READ, PROCESS_VM_WRITE, PROCESS_VM_OPERATION, PROCESS_QUERY_INFORMATION

k32.VirtualProtectEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, ctypes.POINTER(wt.DWORD)]
REG = os.environ.get("REG") or ("eu" if os.environ.get("PAL") == "1" else "us")   # REG=eu|jp (or PAL=1)
PAL = REG == "eu"
ELF = os.path.join(os.path.dirname(os.path.abspath(__file__)), *{"us": ("ps2us", "SLUS_201.84"), "eu": ("ps2eu", "SLES_503.06"), "jp": ("ps2jp", "SLPM_650.22")}[REG])
SYSP, SYSV = {"us": (0x303C90, 0x433100), "eu": (0x30C090, 0x449930), "jp": (0x302C90, 0x430C00)}[REG]
SIG_EE = 0x00101000
SIG = open(ELF, "rb").read()[0x80 + (SIG_EE - 0x100000):][:64]
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots", "pmem_base.txt")

def pcsx2_pid():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq pcsx2-qt.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith('"pcsx2-qt.exe"'): return int(line.split('","')[1])
    raise SystemExit("PCSX2 not running")

class PMem:
    def __init__(self, write=False):
        acc = PROCESS_VM_READ | PROCESS_QUERY_INFORMATION | (PROCESS_VM_WRITE | PROCESS_VM_OPERATION if write else 0)
        self.pid = pcsx2_pid(); self.h = k32.OpenProcess(acc, False, self.pid); self.base = None
        try:
            pid, b = open(CACHE).read().split()
            if int(pid) == self.pid and self._raw(int(b) + SIG_EE, 64) == SIG and self._raw(int(b) + SYSP, 4) == struct.pack("<I", SYSV): self.base = int(b)
        except Exception: pass
        if self.base is None: self.base = self._scan()
        open(CACHE, "w").write(f"{self.pid} {self.base}")
    def _scan(self):
        mbi, addr, hits = MBI(), 0, []
        while k32.VirtualQueryEx(self.h, addr, ctypes.byref(mbi), ctypes.sizeof(mbi)):
            if mbi.State == 0x1000 and mbi.Protect in (0x02, 0x04, 0x20, 0x40, 0x08, 0x80) and mbi.RegionSize <= 0x8000000:
                data = self._raw(mbi.BaseAddress, mbi.RegionSize); i = data.find(SIG)
                while i >= 0:
                    hits.append(mbi.BaseAddress + i - SIG_EE); i = data.find(SIG, i + 1)
            addr = (mbi.BaseAddress or 0) + mbi.RegionSize
        # PCSX2 holds the game's code in several places (file cache, recompiler buffers): EE RAM is the copy whose
        # sys pointer (SYSP) holds the game's SYS_WORK address
        for b in hits:
            if struct.unpack("<I", self._raw(b + SYSP, 4).ljust(4, b"\x00"))[0] == SYSV: return b
        raise SystemExit("EE RAM not found (game not running yet?)")
    def _raw(self, p, n):
        buf = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
        k32.ReadProcessMemory(self.h, ctypes.c_void_p(p), buf, n, ctypes.byref(got)); return buf.raw[:got.value]
    def read(self, a, n): return self._raw(self.base + (a & 0x01FFFFFF), n)
    def u32(self, a): return struct.unpack("<I", self.read(a, 4))[0]
    def u32s(self, a, n): return list(struct.unpack("<%dI" % n, self.read(a, 4 * n)))
    def f32(self, a): return struct.unpack("<f", self.read(a, 4))[0]
    def write(self, a, data, force=False):
        """force: lift PCSX2's write protection on code pages (it protects pages it has recompiled). PCSX2 does not
        see such a write, so already-compiled code keeps running until its block cache is cleared (state load)."""
        got = ctypes.c_size_t(); p = ctypes.c_void_p(self.base + (a & 0x01FFFFFF))
        if k32.WriteProcessMemory(self.h, p, data, len(data), ctypes.byref(got)): return
        if not force: raise OSError(ctypes.get_last_error())
        old = wt.DWORD()
        if not k32.VirtualProtectEx(self.h, p, len(data), 0x04, ctypes.byref(old)): raise OSError(ctypes.get_last_error())
        ok = k32.WriteProcessMemory(self.h, p, data, len(data), ctypes.byref(got))
        k32.VirtualProtectEx(self.h, p, len(data), old.value, ctypes.byref(old))
        if not ok: raise OSError(ctypes.get_last_error())

if __name__ == "__main__":
    m = PMem(); c = sys.argv[1]
    if c == "base": print(hex(m.base))
    elif c == "r32": print(" ".join("%08x" % x for x in m.u32s(int(sys.argv[2], 16), int(sys.argv[3]) if len(sys.argv) > 3 else 1)))
    elif c == "rf": a = int(sys.argv[2], 16); print([m.f32(a + 4 * i) for i in range(int(sys.argv[3]) if len(sys.argv) > 3 else 1)])
