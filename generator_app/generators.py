"""Generatory i potok strumieniowego wytwarzania fikcyjnych danych testowych."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
import itertools
import random

from generator_app.models import BatchConfig, PersonRecord

FIRST_NAMES = ("Jan", "Anna", "Piotr", "Katarzyna", "Marek", "Zofia", "Tomasz", "Julia")
LAST_NAMES = ("Nowak", "Kowalski", "Wiśniewski", "Wójcik", "Kamiński", "Lewandowska", "Zielińska")
DOMAINS = ("example.org", "testmail.pl", "demo.edu.pl", "sandbox.local")
POSTAL_CODES = ("00-001", "50-370", "30-002", "60-101", "80-001")

"""Nieskończony generator fikcyjnych rekordów (część celowo zawiera błędne dane)."""
def infinite_person_stream(
    seed: int = 42, invalid_ratio: float = 0.2
) -> Iterator[PersonRecord]:
    rng = random.Random(seed)
    for idx in itertools.count(start=1):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        year = rng.randint(1955, 1999)
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)
        serial = rng.randint(1, 9999)

        valid_pesel = BatchConfig.build_pesel_with_checksum(year, month, day, serial)
        valid_email = f"{first.lower()}.{last.lower()}{idx}@{rng.choice(DOMAINS)}"
        valid_phone = f"+48 {rng.randint(500, 799)} {rng.randint(100, 999)} {rng.randint(100, 999)}"
        valid_postal = rng.choice(POSTAL_CODES)

        make_invalid = rng.random() < invalid_ratio
        if make_invalid:
            kind = idx % 4
            if kind == 0:
                # Zepsuta cyfra kontrolna PESEL
                bad_digit = "9" if valid_pesel[-1] != "9" else "8"
                pesel = valid_pesel[:-1] + bad_digit
                email, phone, postal = valid_email, valid_phone, valid_postal
            elif kind == 1:
                email = f"bledny-email-{idx}"
                pesel, phone, postal = valid_pesel, valid_phone, valid_postal
            elif kind == 2:
                phone = "12-abc-999"
                pesel, email, postal = valid_pesel, valid_email, valid_postal
            else:
                postal = "9999"
                pesel, email, phone = valid_pesel, valid_email, valid_phone
        else:
            pesel, email, phone, postal = valid_pesel, valid_email, valid_phone, valid_postal

        yield PersonRecord(
            record_id=idx,
            full_name=f"{first} {last}",
            pesel=pesel,
            email=email,
            phone=phone,
            postal_code=postal,
        )

"""Wyrażenie generujące filtrujące rekordy o parzystym identyfikatorze."""
def select_even_id_records(records: Iterable[PersonRecord]) -> Iterator[PersonRecord]:
    return (rec for rec in records if rec.record_id % 2 == 0)

"""Pobiera dokładnie `count` rekordów z nieskończonego strumienia."""
def build_bounded_stream(
    count: int, seed: int = 42, invalid_ratio: float = 0.2
) -> Iterator[PersonRecord]:
    if count < 0:
        raise ValueError("count nie może być ujemne")
    stream = infinite_person_stream(seed=seed, invalid_ratio=invalid_ratio)
    yield from itertools.islice(stream, count)