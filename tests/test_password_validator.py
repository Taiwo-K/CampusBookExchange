import pytest

from app.password_validator import is_strong_password, validate_password


def test_strong_password_passes():
    assert validate_password("Tr1cky#Horse") == []


@pytest.mark.parametrize("password, fragment", [
    ("", "required"),
    (None, "required"),
    ("Ab1!xyz", "at least 8"),
    ("A" * 129 + "a1!", "at most 128"),
    ("lowercase1!", "uppercase"),
    ("UPPERCASE1!", "lowercase"),
    ("NoNumbers!!", "number"),
    ("NoSpecial123", "special"),
    ("Has Space1!x", "spaces"),
    ("Password1", "special"),
])
def test_rejects_weak_passwords(password, fragment):
    errors = validate_password(password)
    assert any(fragment in e for e in errors)


def test_rejects_common_password():
    assert "Password is too common." in validate_password("P@ssw0rd")


def test_rejects_password_with_email_or_name():
    assert not is_strong_password("Yubrajmainali#24", email="yubrajmainali@my.unt.edu")
    assert not is_strong_password("Mainali#2024x", last_name="Mainali")
    assert is_strong_password("Tr1cky#Horse", email="yubrajmainali@my.unt.edu")
