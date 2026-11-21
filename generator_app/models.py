"""Modele danych opisujące wygenerowane rekordy i konfigurację partii."""

from __future__ import annotations

from dataclasses import dataclass, field

from generator_app.decorators import require_active_config

"""Pojedynczy rekord testowych danych osobowych."""
@dataclass(frozen=True)
class PersonRecord:

    record_id: int
    full_name: str
    pesel: str
    email: str
    phone: str
    postal_code: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "record_id": self.record_id,
            "full_name": self.full_name,
            "pesel": self.pesel,
            "email": self.email,
            "phone": self.phone,
            "postal_code": self.postal_code,
        }

"""Konfiguracja generowania i eksportu partii danych."""
@dataclass
class BatchConfig:

    total_records: int
    files_count: int = 4
    invalid_ratio: float = 0.2
    locked: bool = False
    _batch_size: int = field(default=250, repr=False)

    """Zwraca rozmiar pojedynczej partii rekordów."""
    @property
    def batch_size(self) -> int:
        return self._batch_size

    """Waliduje i ustawia rozmiar partii."""
    @batch_size.setter
    def batch_size(self, value: int) -> None:
        if not isinstance(value, int) or value < 1:
            raise ValueError("batch_size musi być liczbą całkowitą >= 1")
        self._batch_size = value

    """Alternatywny konstruktor tworzący konfigurację z parametrów CLI."""
    @classmethod
    def from_cli_args(
        cls, total_records: int, files_count: int, batch_size: int, invalid_ratio: float
    ) -> BatchConfig:
        if total_records < 1:
            raise ValueError("total_records musi być >= 1")
        if files_count < 1:
            raise ValueError("files_count musi być >= 1")
        if not 0.0 <= invalid_ratio <= 1.0:
            raise ValueError("invalid_ratio musi mieścić się w przedziale [0.0, 1.0]")
        cfg = cls(
            total_records=total_records,
            files_count=files_count,
            invalid_ratio=invalid_ratio,
        )
        cfg.batch_size = batch_size
        return cfg

    """Buduje poprawny numer PESEL (dla lat 1900-1999) wraz z cyfrą kontrolną."""
    @staticmethod
    def build_pesel_with_checksum(year: int, month: int, day: int, serial_num: int) -> str:
        if not (1900 <= year <= 1999):
            raise ValueError("Obsługiwany zakres roczników w tym helperze: 1900..1999")
        yy = f"{year % 100:02d}"
        mm = f"{month:02d}"
        dd = f"{day:02d}"
        serial = f"{serial_num % 10000:04d}"
        base = f"{yy}{mm}{dd}{serial}"
        weights = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)
        total = sum(w * int(d) for w, d in zip(weights, base))
        check_digit = (10 - (total % 10)) % 10
        return f"{base}{check_digit}"

    """Blokuje modyfikację konfiguracji (dekorator metody używający self)."""
    @require_active_config
    def lock_config(self) -> None:
        self.locked = True