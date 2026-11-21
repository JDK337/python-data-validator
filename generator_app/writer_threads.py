"""Równoległy zapis partii danych do wielu plików z użyciem wątków, Lock i Queue."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import queue
import threading

from generator_app.decorators import retry_call
from generator_app.models import PersonRecord

"""Licznik zapisanych plików chroniony blokadą Lock."""
class SafeFileCounter:

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._count = 0

    def increment(self) -> int:
        with self._lock:
            self._count += 1
            return self._count

    @property
    def count(self) -> int:
        with self._lock:
            return self._count

"""Zapisuje listę rekordów do pliku JSON i zwraca liczbę zapisanych wierszy."""
@retry_call(attempts=2, delay=0.05, exceptions=(OSError,))
def _write_single_json_file(path: Path, records: list[PersonRecord]) -> int:
    payload = [rec.to_dict() for rec in records]
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return len(records)

"""Zapisuje paczki równolegle do plików w puli wątków, rejestrując zdarzenia w Queue."""
def write_batches_concurrently(
    batches: list[list[PersonRecord]],
    output_dir: Path,
    max_workers: int = 4,
) -> tuple[list[Path], int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_queue: queue.Queue[str] = queue.Queue()
    counter = SafeFileCounter()
    written_paths: list[Path] = []

    def _task(idx: int, chunk: list[PersonRecord]) -> Path:
        file_path = output_dir / f"part_{idx:03d}.json"
        written_rows = _write_single_json_file(file_path, chunk)
        total_files = counter.increment()
        log_queue.put(f"Zapisano {file_path.name} ({written_rows} rekordów), plików={total_files}")
        return file_path

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_task, i, chunk) for i, chunk in enumerate(batches, start=1)]
        for fut in as_completed(futures):
            written_paths.append(fut.result())

    while not log_queue.empty():
        _ = log_queue.get_nowait()
        log_queue.task_done()

    return sorted(written_paths), counter.count