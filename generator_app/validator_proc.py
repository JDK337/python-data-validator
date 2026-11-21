"""Równoległa walidacja rekordów i sprawdzanie sum kontrolnych PESEL w procesach."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any

from generator_app.models import PersonRecord
from generator_app.patterns import validate_record_fields

"""Funkcja wykonywana w procesie roboczym dla paczki rekordów."""
def _validate_chunk(chunk: list[PersonRecord]) -> dict[str, Any]:
    valid_count = 0
    invalid_records: list[dict[str, Any]] = []

    for rec in chunk:
        checks = validate_record_fields(
            pesel=rec.pesel,
            email=rec.email,
            phone=rec.phone,
            postal_code=rec.postal_code,
        )
        if all(checks.values()):
            valid_count += 1
        else:
            invalid_records.append(
                {
                    "record_id": rec.record_id,
                    "full_name": rec.full_name,
                    "errors": [k for k, ok in checks.items() if not ok],
                }
            )

    return {
        "total": len(chunk),
        "valid": valid_count,
        "invalid": len(invalid_records),
        "sample_errors": invalid_records[:5],
    }

"""Przetwarza paczki rekordów równolegle w ProcessPoolExecutor i agreguje wyniki."""
def validate_batches_parallel(
    batches: list[list[PersonRecord]], max_workers: int | None = None
) -> dict[str, Any]:
    if not batches:
        return {"total": 0, "valid": 0, "invalid": 0, "sample_errors": []}

    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        chunk_reports = list(pool.map(_validate_chunk, batches))

    total = sum(r["total"] for r in chunk_reports)
    valid = sum(r["valid"] for r in chunk_reports)
    invalid = sum(r["invalid"] for r in chunk_reports)
    sample_errors: list[dict[str, Any]] = []
    for r in chunk_reports:
        for err in r["sample_errors"]:
            if len(sample_errors) < 10:
                sample_errors.append(err)

    return {
        "total": total,
        "valid": valid,
        "invalid": invalid,
        "sample_errors": sample_errors,
    }