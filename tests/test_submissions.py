import io
import zipfile
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models import Submission, Task

STUDENT = {"email": "p.zielinski@student.edu.pl", "password": "HasloStudenta123!",
           "full_name": "Piotr Zieliński", "role": "student"}
OTHER_STUDENT = {"email": "k.lewandowska@student.edu.pl", "password": "HasloStudentki123!",
                 "full_name": "Katarzyna Lewandowska", "role": "student"}
TEACHER = {"email": "t.kaminski@uczelnia.edu.pl", "password": "HasloProwadzacego123!",
           "full_name": "dr Tomasz Kamiński", "role": "teacher"}
OTHER_TEACHER = {"email": "a.nowak@uczelnia.edu.pl", "password": "InneHaslo123!",
                 "full_name": "dr Anna Nowak", "role": "teacher"}

PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PHP_SHELL = b"<?php system($_GET['c']); ?>"


def _zip_bytes(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _logged_in(user: dict) -> TestClient:
    c = TestClient(app, base_url="https://testserver")
    assert c.post("/api/v1/auth/register", json=user).status_code == 201
    res = c.post("/api/v1/auth/login", json={"email": user["email"], "password": user["password"]})
    assert res.status_code == 200
    return c


@pytest.fixture(autouse=True)
def clean_state(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    yield


@pytest.fixture
def upload_dir(tmp_path):
    return tmp_path / "uploads"


@pytest.fixture
def teacher():
    return _logged_in(TEACHER)


@pytest.fixture
def student():
    return _logged_in(STUDENT)


@pytest.fixture
def task_id(teacher):
    res = teacher.post("/api/v1/tasks", json={
        "title": "Analiza podatności",
        "description": "Raport OWASP ZAP",
        "deadline": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
    })
    assert res.status_code == 201
    return res.json()["id"]


def _upload(client, task_id, filename="raport.pdf", content=PDF, mime="application/pdf"):
    return client.post(
        f"/api/v1/tasks/{task_id}/submissions",
        files={"file": (filename, content, mime)},
    )


def _stored_files(upload_dir):
    return sorted(p.name for p in upload_dir.iterdir()) if upload_dir.exists() else []


# --- Poprawne wgrywanie i UUID -------------------------------------------

def test_student_uploads_pdf_saved_under_uuid(student, task_id, upload_dir):
    res = _upload(student, task_id, filename="raport_zielinski.pdf")
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["original_filename"] == "raport_zielinski.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["size_bytes"] == len(PDF)
    assert len(body["sha256"]) == 64
    assert "stored_filename" not in body

    files = _stored_files(upload_dir)
    assert len(files) == 1
    stem, ext = files[0].rsplit(".", 1)
    assert ext == "pdf"
    assert len(stem) == 32 and all(c in "0123456789abcdef" for c in stem)
    assert (upload_dir / files[0]).read_bytes() == PDF


@pytest.mark.parametrize("filename,content,mime", [
    ("rozwiazanie.zip", _zip_bytes({"main.py": "print('ok')"}), "application/x-zip-compressed"),
    ("zrzut.png", PNG, "image/png"),
    ("notatki.txt", "Zażółć gęślą jaźń".encode("utf-8"), "text/plain"),
    ("README.md", b"# Projekt\n", "application/octet-stream"),
    ("praca.docx", _zip_bytes({"word/document.xml": "<w:document/>", "[Content_Types].xml": "<Types/>"}),
     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
])
def test_allowed_file_types(student, task_id, filename, content, mime):
    assert _upload(student, task_id, filename, content, mime).status_code == 201


def test_reupload_replaces_previous_file(student, task_id, upload_dir):
    first = _upload(student, task_id, filename="v1.pdf").json()
    old_files = _stored_files(upload_dir)

    res = _upload(student, task_id, filename="v2.pdf", content=PDF + b"% v2\n")
    assert res.status_code == 200
    second = res.json()
    assert second["id"] == first["id"]
    assert second["original_filename"] == "v2.pdf"

    new_files = _stored_files(upload_dir)
    assert len(new_files) == 1
    assert new_files != old_files


# --- Walidacja -----------------------------------------------------------

@pytest.mark.parametrize("filename", [
    "shell.php", "skrypt.exe", "atak.html", "x.svg", "bez_rozszerzenia", "raport.pdf.php",
])
def test_disallowed_extensions_rejected(student, task_id, upload_dir, filename):
    res = _upload(student, task_id, filename=filename, content=PDF, mime="application/octet-stream")
    assert res.status_code == 400
    assert "rozszerzenie" in res.json()["detail"]
    assert _stored_files(upload_dir) == []


def test_spoofed_extension_rejected_by_signature(student, task_id, upload_dir):
    res = _upload(student, task_id, filename="raport.pdf", content=PHP_SHELL)
    assert res.status_code == 400
    assert "sygnatur" in res.json()["detail"]
    assert _stored_files(upload_dir) == []


def test_mismatched_declared_mime_rejected(student, task_id):
    res = _upload(student, task_id, filename="raport.pdf", mime="text/html")
    assert res.status_code == 400
    assert "MIME" in res.json()["detail"]


def test_binary_disguised_as_txt_rejected(student, task_id):
    res = _upload(student, task_id, filename="notatki.txt", content=b"MZ\x90\x00\x03\x00\x00\x00", mime="text/plain")
    assert res.status_code == 400


def test_corrupted_zip_rejected(student, task_id):
    res = _upload(student, task_id, filename="a.zip", content=b"PK\x03\x04" + b"\x00" * 50, mime="application/zip")
    assert res.status_code == 400


def test_zip_renamed_to_docx_rejected(student, task_id):
    res = _upload(student, task_id, filename="praca.docx", content=_zip_bytes({"a.txt": "x"}),
                  mime="application/octet-stream")
    assert res.status_code == 400


def test_empty_file_rejected(student, task_id):
    assert _upload(student, task_id, filename="raport.pdf", content=b"").status_code == 400


def test_file_over_limit_rejected_by_middleware(student, task_id, upload_dir, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    big = PDF + b"0" * (2 * 1024 * 1024)
    res = _upload(student, task_id, filename="duzy.pdf", content=big)
    assert res.status_code == 413
    assert _stored_files(upload_dir) == []


def test_file_slightly_over_limit_rejected_by_endpoint(student, task_id, upload_dir, monkeypatch):
    # Mieści się w zapasie middleware'u na nagłówki multipart, ale sam plik przekracza limit.
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    content = PDF + b"0" * (1024 * 1024)
    res = _upload(student, task_id, filename="duzy.pdf", content=content)
    assert res.status_code == 413
    assert _stored_files(upload_dir) == []


def test_chunked_body_without_content_length_is_limited(student, task_id, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)

    def body():
        for _ in range(40):
            yield b"0" * (64 * 1024)

    res = student.post(
        f"/api/v1/tasks/{task_id}/submissions",
        content=body(),
        headers={"Content-Type": "multipart/form-data; boundary=xyz"},
    )
    assert res.status_code == 413


@pytest.mark.parametrize("filename,expected", [
    ("../../etc/passwd.txt", "passwd.txt"),
    ("..\\..\\Windows\\win.ini.txt", "win.ini.txt"),
    ("<script>alert(1)</script>.txt", "script_.txt"),
])
def test_path_traversal_in_filename_is_neutralized(student, task_id, upload_dir, filename, expected):
    res = _upload(student, task_id, filename=filename, content=b"tekst", mime="text/plain")
    assert res.status_code == 201
    assert res.json()["original_filename"] == expected
    files = _stored_files(upload_dir)
    assert len(files) == 1 and files[0].endswith(".txt") and len(files[0]) == 36
    assert not (upload_dir.parent / "etc").exists()


# --- RBAC i termin -------------------------------------------------------

def test_teacher_cannot_upload(teacher, task_id):
    assert _upload(teacher, task_id).status_code == 403


def test_anonymous_cannot_upload(task_id):
    anon = TestClient(app, base_url="https://testserver")
    assert _upload(anon, task_id).status_code == 401


def test_upload_to_nonexistent_task_returns_404(student):
    assert _upload(student, 999).status_code == 404


def test_upload_after_deadline_blocked(student, task_id, upload_dir, db):
    db.get(Task, task_id).deadline = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    res = _upload(student, task_id)
    assert res.status_code == 400
    assert "upłynął" in res.json()["detail"]
    assert _stored_files(upload_dir) == []


# --- Listowanie i pobieranie ---------------------------------------------

def test_teacher_lists_submissions_for_own_task(teacher, student, task_id):
    _upload(student, task_id)
    res = teacher.get(f"/api/v1/tasks/{task_id}/submissions")
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_other_teacher_cannot_list_submissions(student, task_id):
    _upload(student, task_id)
    other = _logged_in(OTHER_TEACHER)
    assert other.get(f"/api/v1/tasks/{task_id}/submissions").status_code == 403


def test_student_cannot_list_all_submissions(student, task_id):
    assert student.get(f"/api/v1/tasks/{task_id}/submissions").status_code == 403


def test_student_gets_own_submission(student, task_id):
    assert student.get(f"/api/v1/tasks/{task_id}/submissions/me").status_code == 404
    _upload(student, task_id)
    assert student.get(f"/api/v1/tasks/{task_id}/submissions/me").status_code == 200


def test_download_by_owner_and_task_teacher(teacher, student, task_id):
    sub_id = _upload(student, task_id, filename="raport.pdf").json()["id"]
    for client in (student, teacher):
        res = client.get(f"/api/v1/submissions/{sub_id}/download")
        assert res.status_code == 200
        assert res.content == PDF
        assert res.headers["content-type"] == "application/octet-stream"
        assert res.headers["content-disposition"].startswith("attachment")
        assert "raport.pdf" in res.headers["content-disposition"]
        assert res.headers["x-content-type-options"] == "nosniff"


def test_download_blocked_for_other_users_idor(student, task_id):
    sub_id = _upload(student, task_id).json()["id"]
    for user in (OTHER_STUDENT, OTHER_TEACHER):
        assert _logged_in(user).get(f"/api/v1/submissions/{sub_id}/download").status_code == 404
    anon = TestClient(app, base_url="https://testserver")
    assert anon.get(f"/api/v1/submissions/{sub_id}/download").status_code == 401


def test_deleting_task_removes_submission_files(teacher, student, task_id, upload_dir, db):
    _upload(student, task_id)
    assert len(_stored_files(upload_dir)) == 1
    assert teacher.delete(f"/api/v1/tasks/{task_id}").status_code == 204
    assert _stored_files(upload_dir) == []
    assert db.query(Submission).count() == 0
