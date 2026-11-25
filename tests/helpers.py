"""Wspólne dane i funkcje pomocnicze dla testów unit / integration / security."""

import io
import zipfile
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app

STUDENT = {"email": "p.zielinski@student.edu.pl", "password": "HasloStudenta123!",
           "full_name": "Piotr Zieliński", "role": "student"}
OTHER_STUDENT = {"email": "k.lewandowska@student.edu.pl", "password": "HasloStudentki123!",
                 "full_name": "Katarzyna Lewandowska", "role": "student"}
THIRD_STUDENT = {"email": "m.wisniewski@student.edu.pl", "password": "HasloTrzecie123!",
                 "full_name": "Marek Wiśniewski", "role": "student"}
TEACHER = {"email": "t.kaminski@uczelnia.edu.pl", "password": "HasloProwadzacego123!",
           "full_name": "dr Tomasz Kamiński", "role": "teacher"}
OTHER_TEACHER = {"email": "a.nowak@uczelnia.edu.pl", "password": "InneHaslo123!",
                 "full_name": "dr Anna Nowak", "role": "teacher"}

PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 64
PHP_SHELL = b"<?php system($_GET['c']); ?>"
WINDOWS_EXE = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
ELF_BINARY = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 32
SVG_XSS = b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(document.cookie)"/>'

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def zip_bytes(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def docx_bytes() -> bytes:
    return zip_bytes({"[Content_Types].xml": "<Types/>", "word/document.xml": "<w:document/>"})


def future(days: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def anonymous() -> TestClient:
    return TestClient(app, base_url="https://testserver")


def register(user: dict) -> int:
    res = anonymous().post("/api/v1/auth/register", json=user)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def login(user: dict) -> TestClient:
    c = anonymous()
    res = c.post("/api/v1/auth/login", json={"email": user["email"], "password": user["password"]})
    assert res.status_code == 200, res.text
    return c


def logged_in(user: dict) -> TestClient:
    register(user)
    return login(user)


def create_task(teacher: TestClient, title: str = "Analiza podatności", days: int = 2) -> int:
    res = teacher.post("/api/v1/tasks", json={
        "title": title, "description": "Raport OWASP ZAP", "deadline": future(days),
    })
    assert res.status_code == 201, res.text
    return res.json()["id"]


def upload(client: TestClient, task_id: int, filename: str = "raport.pdf", content: bytes = PDF,
           mime: str = "application/pdf", data: dict | None = None, params: dict | None = None):
    return client.post(
        f"/api/v1/tasks/{task_id}/submissions",
        files={"file": (filename, content, mime)},
        data=data,
        params=params,
    )


def grade(client: TestClient, submission_id: int, body):
    return client.put(f"/api/v1/submissions/{submission_id}/grade", json=body)


def stored_files(upload_dir) -> list[str]:
    return sorted(p.name for p in upload_dir.iterdir()) if upload_dir.exists() else []
