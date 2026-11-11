"""
Walidacja wgrywanych plików.

Zasada: nie ufamy niczemu, co przysyła klient. Nazwa pliku służy wyłącznie do
odczytania rozszerzenia (whitelista) i jako etykieta do wyświetlenia, a faktyczny
typ pliku jest ustalany na podstawie jego zawartości (sygnatury / "magic bytes").
"""

import os
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from typing import BinaryIO, Callable, Dict, FrozenSet

from fastapi import HTTPException, status


def _starts_with(*signatures: bytes) -> Callable[[bytes], bool]:
    return lambda head: any(head.startswith(sig) for sig in signatures)


def _is_text(head: bytes) -> bool:
    if b"\x00" in head:
        return False
    try:
        head.decode("utf-8")
    except UnicodeDecodeError as exc:
        # Nagłówek mógł uciąć znak wielobajtowy na końcu – to nie błąd.
        if exc.start < len(head) - 3:
            return False
    return True


@dataclass(frozen=True)
class FileType:
    mime: str
    declared_mimes: FrozenSet[str]
    matches: Callable[[bytes], bool]
    is_zip_container: bool = False


_ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06")
_ZIP_DECLARED = frozenset({
    "application/zip",
    "application/x-zip-compressed",
    "application/x-zip",
    "multipart/x-zip",
})

ALLOWED_FILE_TYPES: Dict[str, FileType] = {
    ".pdf": FileType(
        mime="application/pdf",
        declared_mimes=frozenset({"application/pdf", "application/x-pdf"}),
        matches=_starts_with(b"%PDF-"),
    ),
    ".zip": FileType(
        mime="application/zip",
        declared_mimes=_ZIP_DECLARED,
        matches=_starts_with(*_ZIP_SIGNATURES),
        is_zip_container=True,
    ),
    ".docx": FileType(
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        declared_mimes=frozenset({
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }),
        matches=_starts_with(*_ZIP_SIGNATURES),
        is_zip_container=True,
    ),
    ".png": FileType(
        mime="image/png",
        declared_mimes=frozenset({"image/png"}),
        matches=_starts_with(b"\x89PNG\r\n\x1a\n"),
    ),
    ".jpg": FileType(
        mime="image/jpeg",
        declared_mimes=frozenset({"image/jpeg", "image/pjpeg"}),
        matches=_starts_with(b"\xff\xd8\xff"),
    ),
    ".jpeg": FileType(
        mime="image/jpeg",
        declared_mimes=frozenset({"image/jpeg", "image/pjpeg"}),
        matches=_starts_with(b"\xff\xd8\xff"),
    ),
    ".txt": FileType(
        mime="text/plain",
        declared_mimes=frozenset({"text/plain"}),
        matches=_is_text,
    ),
    ".md": FileType(
        mime="text/markdown",
        declared_mimes=frozenset({"text/markdown", "text/x-markdown", "text/plain"}),
        matches=_is_text,
    ),
}

# Część przeglądarek wysyła ogólny typ, gdy nie rozpoznaje rozszerzenia.
_GENERIC_DECLARED_MIMES = frozenset({"application/octet-stream", ""})

SNIFF_BYTES = 8192
MAX_ORIGINAL_NAME_LENGTH = 255

_UNSAFE_NAME_CHARS = re.compile(r"[^\w.\- ()\[\]]", re.UNICODE)


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def allowed_extensions_label() -> str:
    return ", ".join(sorted(ALLOWED_FILE_TYPES))


def sanitize_display_name(filename: str) -> str:
    """
    Zwraca bezpieczną nazwę do wyświetlenia / nagłówka Content-Disposition.
    Nigdy nie jest używana jako ścieżka na dysku.
    """
    name = unicodedata.normalize("NFC", filename or "")
    # Odcięcie ewentualnej ścieżki (zarówno "/" jak i "\").
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C")
    name = _UNSAFE_NAME_CHARS.sub("_", name).strip(" .")
    if not name:
        name = "plik"
    if len(name) > MAX_ORIGINAL_NAME_LENGTH:
        stem, ext = os.path.splitext(name)
        name = stem[: MAX_ORIGINAL_NAME_LENGTH - len(ext)] + ext
    return name


def get_extension(filename: str) -> str:
    if not filename:
        raise _bad_request("Brak nazwy pliku.")
    if "\x00" in filename:
        raise _bad_request("Nieprawidłowa nazwa pliku.")
    base = filename.replace("\\", "/").rsplit("/", 1)[-1]
    _, ext = os.path.splitext(base)
    ext = ext.lower()
    if ext not in ALLOWED_FILE_TYPES:
        raise _bad_request(
            f"Niedozwolone rozszerzenie pliku. Dozwolone: {allowed_extensions_label()}."
        )
    return ext


def validate_file(filename: str, declared_mime: str | None, stream: BinaryIO, size: int) -> FileType:
    """
    Sprawdza rozszerzenie, deklarowany typ MIME, rozmiar i rzeczywistą zawartość pliku.
    `stream` musi być przewinięty na początek; po walidacji pozycja jest przywracana na 0.
    """
    ext = get_extension(filename)
    file_type = ALLOWED_FILE_TYPES[ext]

    if size == 0:
        raise _bad_request("Przesłany plik jest pusty.")

    declared = (declared_mime or "").split(";", 1)[0].strip().lower()
    if declared not in file_type.declared_mimes and declared not in _GENERIC_DECLARED_MIMES:
        raise _bad_request("Typ MIME pliku nie zgadza się z jego rozszerzeniem.")

    stream.seek(0)
    head = stream.read(SNIFF_BYTES)
    stream.seek(0)

    if not file_type.matches(head):
        raise _bad_request("Zawartość pliku nie odpowiada jego rozszerzeniu (weryfikacja sygnatury).")

    if file_type.is_zip_container:
        _validate_zip_container(stream, ext)
        stream.seek(0)

    return file_type


def _validate_zip_container(stream: BinaryIO, ext: str) -> None:
    # Odczyt samego katalogu archiwum (bez rozpakowywania) – archiwum nie jest nigdy
    # rozpakowywane na serwerze, więc zip bomb nie zagraża zasobom.
    try:
        with zipfile.ZipFile(stream) as zf:
            names = zf.namelist()
    except (zipfile.BadZipFile, zipfile.LargeZipFile, ValueError, OSError):
        raise _bad_request("Uszkodzone lub nieprawidłowe archiwum.")

    if ext == ".docx" and "word/document.xml" not in names:
        raise _bad_request("Plik nie jest prawidłowym dokumentem DOCX.")
