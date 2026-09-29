"""Ethiopic helpers: name normalisation (homophones) and the Ethiopian calendar.

This module has no Django dependency so it can be tested on its own. Every date
calculation and the homophone-folding table here have been cross-checked
against known reference dates and are load-bearing for §4.1/§4.2 (the
existing-student match check) and every Ethiopian-calendar display/entry in
the SRS — treat this file as verified, not a first draft.
"""
import datetime as dt
import re
import unicodedata

# ---------------------------------------------------------------- homophones
# Each family of letters is folded onto one canonical family, order by order
# (1st..7th form), so e.g. ሐ/ኀ -> ሀ, ሠ -> ሰ, ዐ -> አ, ፀ -> ጸ.
_HOMOPHONES = {}


def _fold(src_start, dst_start, count=7):
    for i in range(count):
        _HOMOPHONES[chr(src_start + i)] = chr(dst_start + i)


_fold(0x1210, 0x1200)  # ሐ family -> ሀ family
_fold(0x1280, 0x1200)  # ኀ family -> ሀ family
_fold(0x1220, 0x1230)  # ሠ family -> ሰ family
_fold(0x12D0, 0x12A0)  # ዐ family -> አ family
_fold(0x1340, 0x1338)  # ፀ family -> ጸ family
_TRANS = str.maketrans(_HOMOPHONES)

_INVISIBLE = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")
_PUNCT = re.compile("[\u1361-\u1368.,;:'\"`()_/\\\\-]")
_SPACES = re.compile(r"\s+")


def _normalize_text(value):
    """Lower-case, fold homophone letters, drop punctuation, collapse spaces."""
    value = unicodedata.normalize("NFC", value or "")
    value = _INVISIBLE.sub("", value)
    value = value.translate(_TRANS)
    value = _PUNCT.sub(" ", value)
    return _SPACES.sub(" ", value).strip().lower()


def normalize_name(first, father, grandfather):
    """Key used to detect the same person (positions matter: student|father|grandfather).
    This is what models.Student.save() and services.find_existing_student() call."""
    return "|".join(_normalize_text(x) for x in (first, father, grandfather))


# ------------------------------------------------------------------ calendar
MONTHS = [
    "መስከረም", "ጥቅምት", "ኅዳር", "ታኅሣሥ", "ጥር", "የካቲት", "መጋቢት",
    "ሚያዝያ", "ግንቦት", "ሰኔ", "ሐምሌ", "ነሐሴ", "ጳጉሜን",
]
# Python weekday(): Monday=0 ... Sunday=6
WEEKDAYS = ["ሰኞ", "ማክሰኞ", "ረቡዕ", "ሐሙስ", "ዓርብ", "ቅዳሜ", "እሑድ"]

_EPOCH = 1723856  # JDN offset of the Ethiopian (Amete Mihret) calendar
_ORD_TO_JDN = 1721425  # date.toordinal() + this == Julian Day Number


def to_ethiopian(d):
    """Gregorian date -> (year, month, day) in the Ethiopian calendar."""
    if isinstance(d, dt.datetime):
        d = d.date()
    jdn = d.toordinal() + _ORD_TO_JDN
    r = (jdn - _EPOCH) % 1461
    n = r % 365 + 365 * (r // 1460)
    year = 4 * ((jdn - _EPOCH) // 1461) + r // 365 - r // 1460
    return year, n // 30 + 1, n % 30 + 1


def from_ethiopian(year, month, day):
    """Ethiopian (year, month, day) -> Gregorian date. Raises ValueError if invalid."""
    if not (1 <= month <= 13 and 1 <= day <= 30 and year >= 1):
        raise ValueError("invalid Ethiopian date")
    jdn = (_EPOCH + 365) + 365 * (year - 1) + year // 4 + 30 * month + day - 31
    result = dt.date.fromordinal(jdn - _ORD_TO_JDN)
    if to_ethiopian(result) != (year, month, day):
        raise ValueError("invalid Ethiopian date")
    return result


def days_in_month(year, month):
    if month < 13:
        return 30
    return 6 if year % 4 == 3 else 5


def sundays_in_month(year, month):
    """Every Sunday (as a Gregorian date) falling in a given Ethiopian month —
    this is what an attendance sheet's columns are built from (SRS §4.5)."""
    days = []
    for day in range(1, days_in_month(year, month) + 1):
        d = from_ethiopian(year, month, day)
        if d.weekday() == 6:
            days.append(d)
    return days


def current_year(today=None):
    return to_ethiopian(today or dt.date.today())[0]


def format_date(d, with_weekday=False):
    if not d:
        return ""
    y, m, day = to_ethiopian(d)
    text = f"{day} {MONTHS[m - 1]} {y}"
    if with_weekday:
        text = f"{WEEKDAYS[d.weekday()]} {text}"
    return text


def format_short(d):
    if not d:
        return ""
    y, m, day = to_ethiopian(d)
    return f"{day}/{m}"


def format_input(d):
    """dd/mm/yyyy in the Ethiopian calendar — what a date <input> should show/accept."""
    if not d:
        return ""
    y, m, day = to_ethiopian(d)
    return f"{day:02d}/{m:02d}/{y}"


_DATE_RE = re.compile(r"^\s*(\d{1,2})\s*[/\-.\s]\s*(\d{1,2})\s*[/\-.\s]\s*(\d{4})\s*$")


def parse_date(text):
    """Parse 'dd/mm/yyyy' typed in the Ethiopian calendar -> Gregorian date."""
    match = _DATE_RE.match(text or "")
    if not match:
        raise ValueError("bad format")
    day, month, year = (int(x) for x in match.groups())
    return from_ethiopian(year, month, day)