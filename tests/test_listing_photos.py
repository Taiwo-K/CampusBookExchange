import io

from flask import request
from werkzeug.datastructures import FileStorage

from app.blueprints.listings import MAX_PHOTO_BYTES, MAX_PHOTOS, validate_photos

JPEG_HEADER = b"\xff\xd8\xff" + b"\x00" * 100
PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
WEBP_HEADER = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 100


def _upload(filename, content):
    return FileStorage(stream=io.BytesIO(content), filename=filename)


def test_valid_jpeg_passes():
    assert validate_photos([_upload("book.jpg", JPEG_HEADER)]) == []


def test_valid_png_passes():
    assert validate_photos([_upload("book.png", PNG_HEADER)]) == []


def test_valid_webp_passes():
    assert validate_photos([_upload("book.webp", WEBP_HEADER)]) == []


def test_disallowed_extension_rejected():
    errors = validate_photos([_upload("book.gif", b"GIF89a" + b"\x00" * 50)])

    assert len(errors) == 1
    assert "jpg, png or webp" in errors[0]


def test_disguised_executable_rejected_on_extension_alone():
    errors = validate_photos([_upload("malware.exe", JPEG_HEADER)])

    assert len(errors) == 1
    assert "jpg, png or webp" in errors[0]


def test_renamed_file_with_wrong_magic_bytes_is_rejected():
    errors = validate_photos([_upload("fake.jpg", b"not-actually-a-jpeg" * 5)])

    assert len(errors) == 1
    assert "doesn't look like a real image" in errors[0]


def test_oversized_file_rejected():
    big = JPEG_HEADER + b"\x00" * MAX_PHOTO_BYTES
    errors = validate_photos([_upload("huge.jpg", big)])

    assert len(errors) == 1
    assert "larger than 5 MB" in errors[0]


def test_empty_file_rejected():
    errors = validate_photos([_upload("empty.jpg", b"")])

    assert len(errors) == 1
    assert "empty" in errors[0]


def test_too_many_photos_rejected():
    uploads = [_upload(f"book{i}.jpg", JPEG_HEADER) for i in range(MAX_PHOTOS + 1)]

    errors = validate_photos(uploads)

    assert any("at most 5 photos" in e for e in errors)


def test_valid_uploads_report_no_errors_together():
    uploads = [
        _upload("front.jpg", JPEG_HEADER),
        _upload("back.png", PNG_HEADER),
    ]

    assert validate_photos(uploads) == []


def test_stream_is_rewound_for_save_photos_to_use_afterwards():
    upload = _upload("book.jpg", JPEG_HEADER)

    validate_photos([upload])

    assert upload.stream.tell() == 0


def _sign_in_verified(monkeypatch):
    monkeypatch.setattr(
        "app.auth.current_user",
        lambda: {"id": 1, "email": "student@unt.edu", "verified": True},
    )


def test_oversized_request_redirects_back_to_form_with_message(app, client, monkeypatch):
    _sign_in_verified(monkeypatch)
    app.config["MAX_CONTENT_LENGTH"] = 1024

    response = client.post(
        "/create_listing",
        data={"textbook_image": (io.BytesIO(JPEG_HEADER + b"\x00" * 2048), "big.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/create_listing")
    with client.session_transaction() as session:
        messages = [m for _, m in session["_flashes"]]
    assert any("under 5 MB" in m for m in messages)


def test_oversized_request_elsewhere_gets_plain_413(app, client, monkeypatch):
    _sign_in_verified(monkeypatch)
    app.config["MAX_CONTENT_LENGTH"] = 1024

    @app.post("/echo")
    def echo():
        return request.form.get("x", "")

    response = client.post("/echo", data={"x": "a" * 4096})

    assert response.status_code == 413
    assert b"too large" in response.data
