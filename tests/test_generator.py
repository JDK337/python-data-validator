from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from generator_app.decorators import retry_call, time_limit
from generator_app.generators import build_bounded_stream
from generator_app.iterators import BatchIterator
from generator_app.models import BatchConfig
from generator_app.patterns import is_valid_pesel_checksum, validate_record_fields
from generator_app.validator_proc import validate_batches_parallel
from generator_app.writer_threads import write_batches_concurrently


class TestGeneratorValidator(unittest.TestCase):
    def test_pesel_and_fields_validation(self) -> None:
        valid_pesel = BatchConfig.build_pesel_with_checksum(1990, 5, 15, 1234)
        self.assertTrue(is_valid_pesel_checksum(valid_pesel))
        bad_pesel = valid_pesel[:-1] + ("0" if valid_pesel[-1] != "0" else "1")
        self.assertFalse(is_valid_pesel_checksum(bad_pesel))

        ok_res = validate_record_fields(
            pesel=valid_pesel,
            email="jan.kowalski@example.org",
            phone="+48 501 234 567",
            postal_code="50-370",
        )
        self.assertTrue(all(ok_res.values()))

        bad_res = validate_record_fields(
            pesel=bad_pesel,
            email="niepoprawny",
            phone="abc",
            postal_code="123",
        )
        self.assertFalse(all(bad_res.values()))

    def test_decorators(self) -> None:
        attempts_made = {"n": 0}

        @retry_call(attempts=3, delay=0.01, exceptions=(RuntimeError,))
        def unstable() -> str:
            attempts_made["n"] += 1
            if attempts_made["n"] < 2:
                raise RuntimeError("tymczasowy błąd")
            return "ok"

        self.assertEqual(unstable(), "ok")
        self.assertEqual(attempts_made["n"], 2)

        @time_limit(0.05)
        def slow() -> None:
            import time

            time.sleep(0.25)

        with self.assertRaises(TimeoutError):
            slow()

    def test_iterator_process_validation_and_thread_writer(self) -> None:
        records = list(build_bounded_stream(count=25, seed=7, invalid_ratio=0.2))
        self.assertEqual(len(records), 25)

        batches = list(BatchIterator(records, batch_size=10))
        self.assertEqual(len(batches), 3)

        report = validate_batches_parallel(batches, max_workers=2)
        self.assertEqual(report["total"], 25)
        self.assertEqual(report["valid"] + report["invalid"], 25)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            files, count = write_batches_concurrently(batches, output_dir=out_dir, max_workers=2)
            self.assertEqual(count, 3)
            self.assertEqual(len(files), 3)
            for f in files:
                self.assertTrue(f.exists())


if __name__ == "__main__":
    unittest.main()