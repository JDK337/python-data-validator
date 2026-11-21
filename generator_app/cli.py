"""Punkt wejścia CLI generatora i walidatora danych testowych."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

from generator_app.generators import build_bounded_stream, select_even_id_records
from generator_app.gil_bench import get_gil_status, run_gil_comparison
from generator_app.iterators import BatchIterator
from generator_app.models import BatchConfig
from generator_app.validator_proc import validate_batches_parallel
from generator_app.writer_threads import write_batches_concurrently

logger = logging.getLogger("data_generator_validator")


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data_generator_validator",
        description="Generator i walidator testowych danych osobowych (PESEL, e-mail, telefon, kod).",
    )
    parser.add_argument("--count", type=int, default=1000, help="Liczba generowanych rekordów.")
    parser.add_argument("--batch-size", type=int, default=250, help="Rozmiar pojedynczej paczki.")
    parser.add_argument("--workers", type=int, default=4, help="Liczba wątków/procesów roboczych.")
    parser.add_argument(
        "--invalid-ratio",
        type=float,
        default=0.2,
        help="Udział celowo błędnych rekordów (0.0 .. 1.0).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("output_batches"),
        help="Katalog docelowy dla plików JSON.",
    )
    parser.add_argument(
        "--benchmark-gil",
        action="store_true",
        help="Uruchamia benchmark porównawczy sekwencyjnie vs wątki vs procesy.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Szczegółowe logi.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    try:
        config = BatchConfig.from_cli_args(
            total_records=args.count,
            files_count=args.workers,
            batch_size=args.batch_size,
            invalid_ratio=args.invalid_ratio,
        )
        config.lock_config()
        logger.info("Konfiguracja: %s", config)

        records = list(
            build_bounded_stream(
                count=config.total_records,
                invalid_ratio=config.invalid_ratio,
            )
        )
        even_count = sum(1 for _ in select_even_id_records(records))
        logger.debug("Wygenerowano %d rekordów (w tym %d z parzystym ID)", len(records), even_count)

        batches = list(BatchIterator(records, batch_size=config.batch_size))
        logger.info("Utworzono %d paczek po maks. %d rekordów", len(batches), config.batch_size)

        # Równoległa walidacja w procesach
        summary = validate_batches_parallel(batches, max_workers=args.workers)
        logger.info(
            "Walidacja: poprawnych=%d, błędnych=%d (łącznie=%d)",
            summary["valid"],
            summary["invalid"],
            summary["total"],
        )

        # Współbieżny zapis plików w wątkach
        written_files, file_count = write_batches_concurrently(
            batches, output_dir=args.out_dir, max_workers=args.workers
        )
        logger.info("Zapisano %d plików w katalogu %s: %s", file_count, args.out_dir, [p.name for p in written_files])

        if args.benchmark_gil:
            logger.info("Status GIL: %s", get_gil_status())
            for row in run_gil_comparison(workers=args.workers):
                logger.info(
                    "GIL [%s]: %.4f s (przyspieszenie %.2fx)",
                    row["mode"],
                    row["seconds"],
                    row["speedup"],
                )

        return 0
    except Exception as exc:
        logger.error("Błąd wykonania: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())