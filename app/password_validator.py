"""Password strength validation for registration (FR-1)."""

import re

MIN_LENGTH = 8
MAX_LENGTH = 128

# Small blocklist of passwords students tend to pick.
COMMON_PASSWORDS = {
    "password", "password1", "password123", "passw0rd", "p@ssw0rd",
    "12345678", "123456789", "1234567890", "qwerty123", "qwertyuiop",
    "iloveyou", "welcome1", "welcome123", "letmein123", "admin123",
    "abc12345", "unt12345", "meangreen", "gomeangreen",
}

SPECIAL_CHARS = r"""!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?`~"""


def validate_password(password, email="", first_name="", last_name=""):
    """Return a list of problems with the password. Empty list means it is valid."""
    errors = []

    if not isinstance(password, str) or not password:
        return ["Password is required."]

    if len(password) < MIN_LENGTH:
        errors.append(f"Password must be at least {MIN_LENGTH} characters long.")
    if len(password) > MAX_LENGTH:
        errors.append(f"Password must be at most {MAX_LENGTH} characters long.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain an uppercase letter.")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain a lowercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must contain a number.")
    if not re.search(f"[{SPECIAL_CHARS}]", password):
        errors.append("Password must contain a special character.")
    if re.search(r"\s", password):
        errors.append("Password must not contain spaces.")

    lowered = password.lower()

    if lowered in COMMON_PASSWORDS:
        errors.append("Password is too common.")

    for part in _personal_parts(email, first_name, last_name):
        if part in lowered:
            errors.append("Password must not contain your name or email.")
            break

    return errors


def is_strong_password(password, **kwargs):
    return not validate_password(password, **kwargs)


def _personal_parts(email, first_name, last_name):
    parts = []
    if email:
        parts.append(email.split("@")[0].lower())
    parts.append((first_name or "").lower())
    parts.append((last_name or "").lower())
    # Ignore very short pieces, they would match almost anything.
    return [p for p in parts if len(p) >= 3]
