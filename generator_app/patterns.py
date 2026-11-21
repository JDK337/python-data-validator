"""Wyrażenia regularne z grupami nazwanymi do walidacji i parsowania danych testowych."""

from __future__ import annotations

import re

# PESEL: 11 cyfr z grupami nazwanymi (rok, miesiąc, dzień, serial, kontrolna)
PESEL_RE: re.Pattern[str] = re.compile(
    r"^(?P<yy>\d{2})(?P<mm>\d{2})(?P<dd>\d{2})(?P<serial>\d{4})(?P<ctrl>\d)$"
)

# E-mail z grupami nazwanymi (użytkownik, domena)
EMAIL_RE: re.Pattern[str] = re.compile(
    r"^(?P<user>[A-Za-z0-9._%+-]+)@(?P<domain>[A-Za-z0-9.-]+\.[A-Za-z]{2,})$"
)

# Polski numer telefonu: opcjonalny prefiks +48 lub 0048 i 9 cyfr (rozdzielanych spacją/myślnikiem lub ciągiem)
PHONE_RE: re.Pattern[str] = re.compile(
    r"^(?P<prefix>(?:\+48|0048)?)\s*(?P<d1>\d{3})[-\s]?(?P<d2>\d{3})[-\s]?(?P<d3>\d{3})$"
)

# Polski kod pocztowy: XX-XXX
POSTAL_CODE_RE: re.Pattern[str] = re.compile(
    r"^(?P<part1>\d{2})-(?P<part2>\d{3})$"
)

"""Sprawdza poprawność składni oraz wagowej sumy kontrolnej numeru PESEL."""
def is_valid_pesel_checksum(pesel: str) -> bool:
    match = PESEL_RE.fullmatch(pesel.strip())
    if not match:
        return False

    digits = [int(ch) for ch in pesel.strip()]
    weights = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)
    weighted_sum = sum(w * d for w, d in zip(weights, digits[:10]))
    expected_check = (10 - (weighted_sum % 10)) % 10
    return digits[10] == expected_check

"""Waliduje wszystkie pola rekordu za pomocą wyrażeń regularnych i sumy kontrolnej PESEL."""
def validate_record_fields(
    pesel: str, email: str, phone: str, postal_code: str
) -> dict[str, bool]:
    return {
        "pesel_valid": is_valid_pesel_checksum(pesel),
        "email_valid": EMAIL_RE.fullmatch(email.strip()) is not None,
        "phone_valid": PHONE_RE.fullmatch(phone.strip()) is not None,
        "postal_code_valid": POSTAL_CODE_RE.fullmatch(postal_code.strip()) is not None,
    }

"""Zwraca nazwane grupy z numeru PESEL lub pusty słownik przy braku dopasowania."""
def extract_pesel_parts(pesel: str) -> dict[str, str]:
    match = PESEL_RE.fullmatch(pesel.strip())
    return match.groupdict() if match else {}