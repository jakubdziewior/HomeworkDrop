"""
Scenariusze ataków na wgrywanie plików: web shell, podwójne rozszerzenia, polyglot,
stored XSS, zip bomb, Path Traversal, wstrzykiwanie nagłówków i obchodzenie limitu rozmiaru.
"""

import asyncio
import json

import pytest

from app.config import settings
from app.middleware import BodySizeLimitMiddleware
from tests.helpers import (
    ELF_BINARY, PDF, PHP_SHELL, PNG, STUDENT, SVG_XSS, TEACHER, WINDOWS_EXE,
    create_task, logged_in, stored_files, upload, zip_bytes,
)


@pytest.fixture
def teacher():
    return logged_in(TEACHER)


@pytest.fixture
def student():
    return logged_in(STUDENT)


@pytest.fixture
def task_id(teacher):
    return create_task(teacher)


# --- Web shell / pliki wykonywalne -------------------------------------------

@pytest.mark.parametrize("filename,content,mime", [
    ("shell.php", PHP_SHELL, "application/x-php"),
    ("shell.PhP", PHP_SHELL, "application/octet-stream"),
    ("shell.phtml", PHP_SHELL, "application/octet-stream"),
    ("shell.php5", PHP_SHELL, "application/octet-stream"),
    ("shell.jsp", b"<% Runtime.getRuntime().exec(request.getParameter(\"c\")); %>", "text/plain"),
    ("shell.aspx", b"<%@ Page Language=\"C#\" %>", "text/plain"),
    ("payload.exe", WINDOWS_EXE, "application/x-msdownload"),
    ("payload.elf", ELF_BINARY, "application/octet-stream"),
    (".htaccess", b"AddType application/x-httpd-php .pdf", "text/plain"),
    ("raport.pdf.php", PHP_SHELL, "application/pdf"),
])
def test_executable_uploads_rejected(student, task_id, upload_dir, filename, content, mime):
    res = upload(student, task_id, filename, content, mime)
    assert res.status_code == 400
    assert stored_files(upload_dir) == []


@pytest.mark.parametrize("filename,content", [
    ("shell.php.pdf", PHP_SHELL),       # podwójne rozszerzenie
    ("shell.pdf", PHP_SHELL),           # zmienione rozszerzenie
    ("payload.jpg", WINDOWS_EXE),
    ("payload.png", ELF_BINARY),
    ("payload.txt", WINDOWS_EXE),
    ("xss.png", SVG_XSS),               # SVG udające PNG
    ("raport.zip", PDF),
])
def test_disguised_payloads_rejected_by_signature(student, task_id, upload_dir, filename, content):
    res = upload(student, task_id, filename, content, "application/octet-stream")
    assert res.status_code == 400
    assert "sygnatur" in res.json()["detail"]
    assert stored_files(upload_dir) == []


def test_raw_null_byte_in_filename_rejected(student, task_id, upload_dir):
    # Ręcznie zbudowany multipart – klienci HTTP zwykle kodują \x00 jako %00.
    boundary = "graniczny"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="shell.php\x00.pdf"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("latin-1") + PDF + f"\r\n--{boundary}--\r\n".encode()
    res = student.post(
        f"/api/v1/tasks/{task_id}/submissions",
        content=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    assert res.status_code == 400
    assert stored_files(upload_dir) == []


def test_percent_encoded_null_byte_is_harmless(student, task_id, upload_dir):
    res = upload(student, task_id, "shell.php%00.pdf", PDF)
    assert res.status_code == 201
    assert "%" not in res.json()["original_filename"]
    [name] = stored_files(upload_dir)
    assert name.endswith(".pdf")


def test_uppercase_extension_accepted_but_stored_lowercase(student, task_id, upload_dir):
    res = upload(student, task_id, "RAPORT.PDF", PDF)
    assert res.status_code == 201
    [name] = stored_files(upload_dir)
    assert name.endswith(".pdf") and len(name) == 36


# --- Polyglot / stored XSS -----------------------------------------------------

def test_polyglot_pdf_is_served_only_as_inert_attachment(teacher, student, task_id, upload_dir):
    # Poprawna sygnatura PDF z doklejonym kodem PHP/HTML – przechodzi walidację,
    # ale nigdy nie jest wykonywalny ani renderowany przez przeglądarkę.
    polyglot = PDF + PHP_SHELL + b"<script>alert(document.cookie)</script>"
    sub_id = upload(student, task_id, "polyglot.pdf", polyglot).json()["id"]

    [name] = stored_files(upload_dir)
    assert name.endswith(".pdf")
    assert not any(f.endswith((".php", ".html")) for f in stored_files(upload_dir))

    res = teacher.get(f"/api/v1/submissions/{sub_id}/download")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/octet-stream"
    assert res.headers["content-disposition"].startswith("attachment;")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in res.headers["content-security-policy"]
    assert "default-src 'none'" in res.headers["content-security-policy"]
    assert res.headers["cache-control"] == "no-store"


def test_html_in_txt_is_never_rendered_inline(teacher, student, task_id):
    html = b"<html><body><script>fetch('/api/v1/auth/me')</script></body></html>"
    res = upload(student, task_id, "notatki.txt", html, "text/plain")
    assert res.status_code == 201
    assert res.json()["content_type"] == "text/plain"

    dl = teacher.get(f"/api/v1/submissions/{res.json()['id']}/download")
    assert dl.headers["content-type"] == "application/octet-stream"
    assert "text/html" not in dl.headers["content-type"]
    assert dl.headers["content-disposition"].startswith("attachment")


def test_declared_html_mime_rejected_even_for_text_file(student, task_id):
    assert upload(student, task_id, "notatki.txt", b"<b>x</b>", "text/html").status_code == 400


def test_xss_in_filename_is_neutralized_in_api_and_header(teacher, student, task_id):
    res = upload(student, task_id, '"><img src=x onerror=alert(1)>.txt', b"tekst", "text/plain")
    assert res.status_code == 201
    name = res.json()["original_filename"]
    assert "<" not in name and ">" not in name and '"' not in name

    dl = teacher.get(f"/api/v1/submissions/{res.json()['id']}/download")
    assert "<img" not in dl.headers["content-disposition"]


def test_rtl_override_removed_from_display_name(student, task_id):
    res = upload(student, task_id, "faktura\u202efdp.txt", b"tekst", "text/plain")
    assert res.status_code == 201
    assert "\u202e" not in res.json()["original_filename"]


# --- Zip bomb --------------------------------------------------------------------

def test_zip_bomb_is_stored_compressed_and_never_extracted(teacher, student, task_id, upload_dir):
    # ~50 MB zer kompresuje się do kilkudziesięciu KB – mieści się w limicie wgrywania.
    bomb = zip_bytes({f"zera_{i}.bin": b"\x00" * (10 * 1024 * 1024) for i in range(5)})
    assert len(bomb) < settings.max_upload_size_bytes

    res = upload(student, task_id, "projekt.zip", bomb, "application/zip")
    assert res.status_code == 201
    assert res.json()["size_bytes"] == len(bomb)

    files = stored_files(upload_dir)
    assert len(files) == 1
    assert (upload_dir / files[0]).stat().st_size == len(bomb)

    dl = teacher.get(f"/api/v1/submissions/{res.json()['id']}/download")
    assert dl.content == bomb


def test_nested_zip_with_traversal_entries_is_not_extracted(student, task_id, upload_dir):
    evil = zip_bytes({"../../../../tmp/pwned.txt": "x", "..\\..\\evil.bat": "del *"})
    assert upload(student, task_id, "zip_slip.zip", evil, "application/zip").status_code == 201
    assert len(stored_files(upload_dir)) == 1
    assert not (upload_dir.parent / "pwned.txt").exists()


# --- Path Traversal przy zapisie i pobieraniu --------------------------------------

@pytest.mark.parametrize("filename", [
    "../../../app/main.txt",
    "..%2f..%2fapp%2fconfig.txt",
    "/etc/cron.d/backdoor.txt",
    "C:\\Windows\\System32\\drivers\\etc\\hosts.txt",
    "....//....//x.txt",
])
def test_traversal_filename_never_reaches_filesystem(student, task_id, upload_dir, filename):
    res = upload(student, task_id, filename, b"tekst", "text/plain")
    assert res.status_code == 201
    [name] = stored_files(upload_dir)
    assert len(name) == 36 and name.endswith(".txt")
    assert "/" not in res.json()["original_filename"]
    assert "\\" not in res.json()["original_filename"]
    assert list(upload_dir.parent.iterdir()) == [upload_dir]


@pytest.mark.parametrize("path", [
    "/api/v1/submissions/..%2F..%2Fetc%2Fpasswd/download",
    "/api/v1/submissions/0/download",
    "/api/v1/submissions/-1/download",
    "/api/v1/submissions/1%20OR%201=1/download",
    "/api/v1/submissions/1.0/download",
])
def test_download_id_must_be_positive_integer(student, path):
    assert student.get(path).status_code in (404, 422)


def test_download_after_file_removed_from_disk_returns_404(student, task_id, upload_dir):
    sub_id = upload(student, task_id).json()["id"]
    [name] = stored_files(upload_dir)
    (upload_dir / name).unlink()
    assert student.get(f"/api/v1/submissions/{sub_id}/download").status_code == 404


# --- Limit rozmiaru (DoS) ----------------------------------------------------------

def test_size_limit_applies_to_every_endpoint(student, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    big = json.dumps({"title": "x" * (2 * 1024 * 1024)})
    res = student.post("/api/v1/tasks", content=big, headers={"Content-Type": "application/json"})
    assert res.status_code == 413


def _call_middleware(headers, chunks):
    """Wywołanie middleware'u bezpośrednio na poziomie ASGI (bez klienta HTTP, który poprawia nagłówki)."""
    sent: list[dict] = []
    reached = {"app": False}

    async def inner_app(scope, receive, send):
        reached["app"] = True
        while True:
            msg = await receive()
            if not msg.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    queue = [{"type": "http.request", "body": c, "more_body": i < len(chunks) - 1} for i, c in enumerate(chunks)]

    async def receive():
        return queue.pop(0)

    async def send(msg):
        sent.append(msg)

    scope = {"type": "http", "method": "POST", "path": "/", "headers": headers}
    asyncio.run(BodySizeLimitMiddleware(inner_app)(scope, receive, send))
    return sent[0]["status"], reached["app"]


def test_middleware_rejects_invalid_content_length():
    status, reached = _call_middleware([(b"content-length", b"abc")], [b"x"])
    assert (status, reached) == (400, False)


def test_middleware_rejects_declared_oversize_before_reading_body(monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    status, reached = _call_middleware([(b"content-length", str(50 * 1024 * 1024).encode())], [b"x"])
    assert (status, reached) == (413, False)


def test_middleware_counts_real_bytes_when_content_length_lies(monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    chunks = [b"0" * (256 * 1024)] * 8   # 2 MB mimo zadeklarowanych 10 bajtów
    status, _ = _call_middleware([(b"content-length", b"10")], chunks)
    assert status == 413


def test_middleware_passes_small_requests(monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    assert _call_middleware([(b"content-length", b"5")], [b"hello"]) == (200, True)


# --- Wyciek informacji ---------------------------------------------------------------

def test_api_never_exposes_storage_paths(teacher, student, task_id, upload_dir):
    sub = upload(student, task_id).json()
    [name] = stored_files(upload_dir)
    listing = teacher.get(f"/api/v1/tasks/{task_id}/submissions").text
    mine = student.get(f"/api/v1/tasks/{task_id}/submissions/me").text
    for body in (json.dumps(sub), listing, mine):
        assert name not in body
        assert str(upload_dir) not in body
        assert "stored_filename" not in body
