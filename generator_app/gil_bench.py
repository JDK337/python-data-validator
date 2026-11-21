"""Pomiar porównawczy GIL: sekwencyjnie vs wątki vs procesy dla obciążenia CPU."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import sys
import sysconfig
import time
from typing import Any

from generator_app.generators import build_bounded_stream
from generator_app.patterns import validate_record_fields

"""Waliduje blok wygenerowanych rekordów w czystym Pythonie (CPU-bound)."""
def _cpu_validate_block(count: int) -> int:
    records = list(build_bounded_stream(count=count, seed=123, invalid_ratio=0.25))
    valid_total = 0
    for rec in records:
        res = validate_record_fields(rec.pesel, rec.email, rec.phone, rec.postal_code)
        if all(res.values()):
            valid_total += 1
    return valid_total

"""Zwraca podstawowe informacje o interpreterze i statusie GIL."""
def get_gil_status() -> dict[str, Any]:
    gil_enabled: bool | None = None
    if hasattr(sys, "_is_gil_enabled"):
        gil_enabled = bool(sys._is_gil_enabled())  # type: ignore[attr-defined]
    return {
        "python_version": sys.version.split()[0],
        "switch_interval_s": sys.getswitchinterval(),
        "free_threading_build": bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
        "gil_enabled": gil_enabled,
    }

"""Porównuje czas wykonania tego samego obciążenia CPU w 3 trybach."""
def run_gil_comparison(blocks: list[int] | None = None, workers: int = 4) -> list[dict[str, Any]]:
    work_items = blocks if blocks is not None else [2_500] * workers

    t0 = time.perf_counter()
    for n in work_items:
        _cpu_validate_block(n)
    seq_s = time.perf_counter() - t0

    t1 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(_cpu_validate_block, work_items))
    thr_s = time.perf_counter() - t1

    t2 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        list(pool.map(_cpu_validate_block, work_items))
    proc_s = time.perf_counter() - t2

    return [
        {"mode": "Sekwencyjnie", "seconds": round(seq_s, 4), "speedup": 1.0},
        {
            "mode": f"Wątki ({workers})",
            "seconds": round(thr_s, 4),
            "speedup": round(seq_s / thr_s, 2) if thr_s > 0 else 0.0,
        },
        {
            "mode": f"Procesy ({workers})",
            "seconds": round(proc_s, 4),
            "speedup": round(seq_s / proc_s, 2) if proc_s > 0 else 0.0,
        },
    ]