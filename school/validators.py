"""Validators reused across multiple forms — password rules (with Amharic
messages) and the phone-number format used throughout the Student and
Account forms, so the same rule can't drift between fields that check it
separately.
"""
import re

from django.contrib.auth.password_validation import CommonPasswordValidator, MinimumLengthValidator
from django.core.exceptions import ValidationError


# ---------------------------------------------------------------- passwords
class AmMinimumLengthValidator(MinimumLengthValidator):
    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                f"የይለፍ ቃል ቢያንስ {self.min_length} ቁምፊዎች መሆን አለበት።", code="password_too_short"
            )

    def get_help_text(self):
        return f"የይለፍ ቃል ቢያንስ {self.min_length} ቁምፊዎች ይኑረው።"


class AmNumericValidator:
    def validate(self, password, user=None):
        if password.isdigit():
            raise ValidationError("የይለፍ ቃል ቁጥሮች ብቻ መሆን የለበትም።", code="password_entirely_numeric")

    def get_help_text(self):
        return "የይለፍ ቃል ቁጥሮች ብቻ መሆን የለበትም።"


class AmCommonPasswordValidator(CommonPasswordValidator):
    def validate(self, password, user=None):
        if password.lower().strip() in self.passwords:
            raise ValidationError("ይህ የይለፍ ቃል በጣም የተለመደ ነው።", code="password_too_common")

    def get_help_text(self):
        return "በጣም የተለመደ የይለፍ ቃል አይጠቀሙ።"


class AmNotUsernameValidator:
    def validate(self, password, user=None):
        if user is not None and getattr(user, "username", None) and password.lower() == user.username.lower():
            raise ValidationError("የይለፍ ቃል ከተጠቃሚ ስም ጋር አንድ መሆን የለበትም።", code="password_same_as_username")

    def get_help_text(self):
        return "የይለፍ ቃል ከተጠቃሚ ስም ጋር አንድ መሆን የለበትም።"


# ------------------------------------------------------------------- phones
_PHONE_RE = re.compile(r"^(?:\+251[97]\d{8}|0[97]\d{8})$")


def validate_ethiopian_phone(value):
    if not value:
        return  # blank is allowed; required-ness is each field's own concern
    cleaned = value.strip().replace(" ", "")
    if not _PHONE_RE.match(cleaned):
        raise ValidationError(
            "ትክክለኛ የስልክ ቁጥር ያስገቡ (ለምሳሌ 0912345678)።", code="invalid_phone"
        )