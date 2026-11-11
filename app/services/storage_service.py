"""
Zapis plików na dysku pod losowymi nazwami (UUID).

Oryginalna nazwa pliku od użytkownika nigdy nie trafia do ścieżki, a każda ścieżka
jest dodatkowo sprawdzana, czy po rozwiązaniu leży wewnątrz katalogu uploadu
(obrona w głąb przed Path Traversal).
"""

import hashlib
import os
import re
import stat
import uuid
from pathlib import Path
from typing import BinaryIO, Tuple

from fastapi import HTTPException, status

from app.config import settings

_STORED_NAME_RE = re.compile(r"^[0-9a-f]{32}\.[a-z0-9]{1,10}$")
_CHUNK = 1024 * 1024


def get_upload_root() -> Path:
    root = Path(settings.UPLOAD_DIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _resolve_inside_root(stored_name: str) -> Path:
    if not _STORED_NAME_RE.fullmatch(stored_name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nieprawidłowy identyfikator pliku.")
    root = get_upload_root()
    path = (root / stored_name).resolve()
    if path.parent != root:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nieprawidłowy identyfikator pliku.")
    return path


def save_file(stream: BinaryIO, extension: str) -> Tuple[str, str]:
    """Zapisuje plik pod nazwą <uuid4>.<ext>. Zwraca (nazwa_na_dysku, sha256)."""
    stored_name = f"{uuid.uuid4().hex}{extension}"
    path = _resolve_inside_root(stored_name)

    digest = hashlib.sha256()
    stream.seek(0)
    # "xb" – nigdy nie nadpisujemy istniejącego pliku.
    with open(path, "xb") as out:
        while chunk := stream.read(_CHUNK):
            digest.update(chunk)
            out.write(chunk)

    # Tylko odczyt/zapis dla właściciela, bez prawa wykonywania.
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    return stored_name, digest.hexdigest()


def get_file_path(stored_name: str) -> Path:
    path = _resolve_inside_root(stored_name)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plik nie istnieje.")
    return path


def delete_file(stored_name: str) -> None:
    path = _resolve_inside_root(stored_name)
    try:
        path.unlink()
    except FileNotFoundError:
        pass

