"""
Industry check-digit validation for freight identifiers.

- Container numbers follow ISO 6346 (4-letter owner+category, 6-digit serial,
  1 check digit).
- Air Waybill (AWB) numbers are an 11-digit number (3-digit airline prefix +
  8-digit serial) where the last serial digit is `serial[:7] mod 7`.

The build_* helpers produce valid identifiers (used by the data seeder so the
sample data always passes validation).
"""
import re

from django.core.exceptions import ValidationError

# ISO 6346 letter values: A=10, B=12, ... skipping multiples of 11.
_LETTER_VALUES = {}
_v = 10
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    while _v % 11 == 0:
        _v += 1
    _LETTER_VALUES[_c] = _v
    _v += 1


def container_check_digit(code10: str) -> int:
    """Check digit for the first 10 chars of an ISO 6346 container number."""
    total = 0
    for i, ch in enumerate(code10.upper()):
        value = _LETTER_VALUES[ch] if ch.isalpha() else int(ch)
        total += value * (2 ** i)
    cd = total % 11
    return 0 if cd == 10 else cd


def is_valid_container_number(value: str) -> bool:
    value = (value or "").upper().replace(" ", "")
    if not re.fullmatch(r"[A-Z]{3}[UJZ]\d{6}\d", value):
        return False
    return int(value[10]) == container_check_digit(value[:10])


def validate_container_number(value: str) -> None:
    if not is_valid_container_number(value):
        raise ValidationError(
            f"'{value}' is not a valid ISO 6346 container number (check digit failed)."
        )


def build_container_number(owner_category: str, serial6: str) -> str:
    """e.g. build_container_number('MSKU', '076259') -> 'MSKU0762595'."""
    code10 = f"{owner_category.upper()}{serial6}"
    return f"{code10}{container_check_digit(code10)}"


def awb_check_digit(prefix3: str, serial7: str) -> int:
    return int(serial7) % 7


def is_valid_awb(value: str) -> bool:
    digits = re.sub(r"[\s-]", "", value or "")
    if not re.fullmatch(r"\d{11}", digits):
        return False
    return int(digits[3:10]) % 7 == int(digits[10])


def validate_awb_number(value: str) -> None:
    if not is_valid_awb(value):
        raise ValidationError(
            f"'{value}' is not a valid Air Waybill number (mod-7 check digit failed)."
        )


def build_awb_number(prefix3: str, serial7: str) -> str:
    """e.g. build_awb_number('160', '1234567') -> '16012345675'."""
    return f"{prefix3}{serial7}{awb_check_digit(prefix3, serial7)}"
