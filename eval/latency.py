"""Time embedding models on this machine: load, embed all chunks, embed one query.

    python -m eval.latency MODEL [MODEL ...]

Queries are embedded one at a time, as the app does. Peak memory is the process working set (Windows).
"""
import argparse
import ctypes
import json
import statistics
import time
from ctypes import wintypes

from sentence_transformers import SentenceTransformer

from eval.experiments import MODELS, ROOT, passage_body
from ingest.load import build_chunks


class MemoryCounters(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]


def peak_memory_mb() -> float:
    counters = MemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(MemoryCounters), wintypes.DWORD]
    kernel32.K32GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
    return counters.PeakWorkingSetSize / 2**20


def main(keys: list[str]) -> None:
    chunks = build_chunks()
    path = ROOT / "eval" / "blind.jsonl"
    questions = [json.loads(l)["pregunta"] for l in path.read_text(encoding="utf-8").splitlines()]
    print(f"{'modelo':<10}{'carga s':>9}{'chunks s':>10}{'consulta mediana s':>20}{'p95 s':>8}{'pico MB':>9}")
    for key in keys:
        hf_id, qprefix, pprefix = MODELS[key]
        t = time.perf_counter()
        model = SentenceTransformer(hf_id, device="cpu")
        load = time.perf_counter() - t
        t = time.perf_counter()
        model.encode([pprefix + passage_body(c) for c in chunks], normalize_embeddings=True, batch_size=8)
        embed_all = time.perf_counter() - t
        model.encode([qprefix + questions[0]], normalize_embeddings=True)  # warm-up
        times = []
        for q in questions:
            t = time.perf_counter()
            model.encode([qprefix + q], normalize_embeddings=True)
            times.append(time.perf_counter() - t)
        times.sort()
        print(f"{key:<10}{load:>9.1f}{embed_all:>10.1f}{statistics.median(times):>20.3f}"
              f"{times[int(0.95 * len(times)) - 1]:>8.3f}{peak_memory_mb():>9.0f}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("models", nargs="+", choices=list(MODELS))
    main(parser.parse_args().models)
