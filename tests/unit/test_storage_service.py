"""Testy jednostkowe zapisu plików pod nazwami UUID (app/services/storage_service.py)."""

import hashlib
import io
import re

import pytest
from fastapi import HTTPException

from app.services import storage_service
from tests.helpers import PDF

UUID_NAME = re.compile(r"^[0-9a-f]{32}\.pdf$")


def test_save_file_uses_uuid_name_and_returns_sha256(upload_dir):
    name, digest = storage_service.save_file(io.BytesIO(PDF), ".pdf")
    assert UUID_NAME.fullmatch(name)
    assert digest == hashlib.sha256(PDF).hexdigest()
    assert (upload_dir / name).read_bytes() == PDF


def test_save_file_generates_unique_names(upload_dir):
    names = {storage_service.save_file(io.BytesIO(PDF), ".pdf")[0] for _ in range(20)}
    assert len(names) == 20
    assert len(list(upload_dir.iterdir())) == 20


def test_save_file_reads_stream_from_start(upload_dir):
    stream = io.BytesIO(PDF)
    stream.seek(10)
    name, _ = storage_service.save_file(stream, ".pdf")
    assert (upload_dir / name).read_bytes() == PDF


@pytest.mark.parametrize("stored_name", [
    "../secret.pdf",
    "..\\secret.pdf",
    "/etc/passwd",
    "C:\\Windows\\win.ini",
    "raport.pdf",
    "0" * 31 + ".pdf",
    "0" * 33 + ".pdf",
    "A" * 32 + ".pdf",
    "0" * 32 + ".pdf/../../x",
    "0" * 32 + ".PDF",
    "0" * 32,
    "0" * 32 + ".",
    "0" * 32 + ".pdf\x00.php",
    "",
])
def test_invalid_stored_names_rejected(stored_name):
    for func in (storage_service.get_file_path, storage_service.delete_file):
        with pytest.raises(HTTPException) as exc:
            func(stored_name)
        assert exc.value.status_code == 400


def test_get_file_path_missing_returns_404():
    with pytest.raises(HTTPException) as exc:
        storage_service.get_file_path("0" * 32 + ".pdf")
    assert exc.value.status_code == 404


def test_get_file_path_stays_inside_upload_root(upload_dir):
    name, _ = storage_service.save_file(io.BytesIO(PDF), ".pdf")
    path = storage_service.get_file_path(name)
    assert path.parent == upload_dir.resolve()


def test_delete_file_removes_and_is_idempotent(upload_dir):
    name, _ = storage_service.save_file(io.BytesIO(PDF), ".pdf")
    storage_service.delete_file(name)
    assert not (upload_dir / name).exists()
    storage_service.delete_file(name)  # brak wyjątku przy ponownym usunięciu
