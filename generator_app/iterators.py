"""Własny iterator dzielący sekwencję rekordów na paczki (partie)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from generator_app.models import PersonRecord

"""Iterator zwracający kolejne paczki obiektów PersonRecord o zadanym rozmiarze."""
class BatchIterator(Iterator[list[PersonRecord]]):

    def __init__(self, records: Sequence[PersonRecord], batch_size: int = 100) -> None:
        if batch_size < 1:
            raise ValueError("batch_size musi być >= 1")
        self._records: list[PersonRecord] = list(records)
        self._batch_size: int = batch_size
        self._cursor: int = 0

    def __iter__(self) -> BatchIterator:
        return self

    def __next__(self) -> list[PersonRecord]:
        if self._cursor >= len(self._records):
            raise StopIteration
        chunk = self._records[self._cursor : self._cursor + self._batch_size]
        self._cursor += self._batch_size
        return chunk