"""Windows: snapshot all processes in one NtQuerySystemInformation call.

psutil queries each process separately and, for processes owned by SYSTEM or
services, falls back to a full system snapshot per process (~7 s for ~400
processes). One snapshot here takes ~15 ms and returns the same data.
"""

import ctypes
from ctypes import wintypes

SYSTEM_PROCESS_INFORMATION_CLASS = 5
STATUS_INFO_LENGTH_MISMATCH = 0xC0000004


class _UnicodeString(ctypes.Structure):
    _fields_ = [("Length", wintypes.USHORT), ("MaximumLength", wintypes.USHORT), ("Buffer", ctypes.c_void_p)]


class _SystemProcessInformation(ctypes.Structure):
    # Leading fields of SYSTEM_PROCESS_INFORMATION (winternl.h / ntexapi.h)
    _fields_ = [
        ("NextEntryOffset", wintypes.ULONG),
        ("NumberOfThreads", wintypes.ULONG),
        ("WorkingSetPrivateSize", ctypes.c_longlong),
        ("HardFaultCount", wintypes.ULONG),
        ("NumberOfThreadsHighWatermark", wintypes.ULONG),
        ("CycleTime", ctypes.c_ulonglong),
        ("CreateTime", ctypes.c_longlong),
        ("UserTime", ctypes.c_longlong),     # 100 ns units
        ("KernelTime", ctypes.c_longlong),   # 100 ns units
        ("ImageName", _UnicodeString),
        ("BasePriority", ctypes.c_long),
        ("UniqueProcessId", ctypes.c_void_p),
        ("InheritedFromUniqueProcessId", ctypes.c_void_p),
        ("HandleCount", wintypes.ULONG),
        ("SessionId", wintypes.ULONG),
        ("UniqueProcessKey", ctypes.c_size_t),
        ("PeakVirtualSize", ctypes.c_size_t),
        ("VirtualSize", ctypes.c_size_t),
        ("PageFaultCount", wintypes.ULONG),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),  # == psutil memory_info().rss
    ]


_ntdll = ctypes.WinDLL("ntdll")


def snapshot():
    """Return {(pid, create_time): (pid, name, cpu_seconds, rss_bytes)}."""
    size = ctypes.c_ulong(1 << 20)
    while True:
        buf = ctypes.create_string_buffer(size.value)
        status = _ntdll.NtQuerySystemInformation(
            SYSTEM_PROCESS_INFORMATION_CLASS, buf, size, ctypes.byref(size)) & 0xFFFFFFFF
        if status == 0:
            break
        if status != STATUS_INFO_LENGTH_MISMATCH:
            raise OSError(f"NtQuerySystemInformation failed: NTSTATUS {status:#010x}")
        size = ctypes.c_ulong(size.value + 65536)  # process list grew; retry with headroom

    procs = {}
    base, offset = ctypes.addressof(buf), 0
    while True:
        e = _SystemProcessInformation.from_address(base + offset)
        pid = e.UniqueProcessId or 0
        if pid != 0:  # skip System Idle Process
            name = ctypes.wstring_at(e.ImageName.Buffer, e.ImageName.Length // 2) if e.ImageName.Buffer else ""
            procs[(pid, e.CreateTime)] = (pid, name, (e.UserTime + e.KernelTime) / 1e7, e.WorkingSetSize)
        if not e.NextEntryOffset:
            break
        offset += e.NextEntryOffset
    return procs
