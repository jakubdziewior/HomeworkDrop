"""
Testy jednostkowe walidacji załączników (app/services/file_validation.py):
whitelista rozszerzeń, zgodność deklarowanego MIME, sygnatury (magic bytes),
kontenery ZIP/DOCX oraz oczyszczanie nazwy do wyświetlenia.
"""

import io

import pytest
from fastapi import HTTPException

from app.services.file_validation import (
    ALLOWED_FILE_TYPES,
    MAX_ORIGINAL_NAME_LENGTH,
    SNIFF_BYTES,
    _is_text,
    allowed_extensions_label,
    get_extension,
    sanitize_display_name,
    validate_file,
)
from tests.helpers import (
    DOCX_MIME, ELF_BINARY, JPG, PDF, PHP_SHELL, PNG, SVG_XSS, WINDOWS_EXE, docx_bytes, zip_bytes,
)

VALID_SAMPLES = {
    ".pdf": (PDF, "application/pdf"),
    ".zip": (zip_bytes({"main.py": "print('ok')"}), "application/zip"),
    ".docx": (docx_bytes(), DOCX_MIME),
    ".png": (PNG, "image/png"),
    ".jpg": (JPG, "image/jpeg"),
    ".jpeg": (JPG, "image/jpeg"),
    ".txt": ("Zażółć gęślą jaźń\n".encode("utf-8"), "text/plain"),
    ".md": (b"# Projekt\n\n- punkt\n", "text/markdown"),
}


def _validate(filename: str, content: bytes, mime: str | None = None):
    return validate_file(filename, mime, io.BytesIO(content), len(content))


def _rejected(filename: str, content: bytes, mime: str | None = None) -> str:
    with pytest.raises(HTTPException) as exc:
        _validate(filename, content, mime)
    assert exc.value.status_code == 400
    return exc.value.detail


# --- Whitelista rozszerzeń -------------------------------------------------

def test_whitelist_covers_exactly_expected_extensions():
    assert set(ALLOWED_FILE_TYPES) == {".pdf", ".zip", ".docx", ".png", ".jpg", ".jpeg", ".txt", ".md"}
    assert set(VALID_SAMPLES) == set(ALLOWED_FILE_TYPES)


def test_allowed_extensions_label_is_sorted_list():
    assert allowed_extensions_label() == ".docx, .jpeg, .jpg, .md, .pdf, .png, .txt, .zip"


@pytest.mark.parametrize("filename,expected", [
    ("raport.pdf", ".pdf"),
    ("RAPORT.PDF", ".pdf"),
    ("Zrzut.JpEg", ".jpeg"),
    ("archiwum.tar.zip", ".zip"),
    ("katalog/podkatalog/notatki.md", ".md"),
    ("C:\\Users\\student\\praca.docx", ".docx"),
    ("shell.php.pdf", ".pdf"),
])
def test_get_extension_accepts_whitelisted(filename, expected):
    assert get_extension(filename) == expected


@pytest.mark.parametrize("filename", [
    "shell.php", "shell.PHP", "x.phtml", "skrypt.exe", "skrypt.bat", "skrypt.ps1", "x.sh",
    "atak.html", "atak.htm", "x.svg", "x.js", "x.jsp", "x.aspx", ".htaccess", "web.config",
    "raport.pdf.php", "bez_rozszerzenia", ".pdf", "raport.pdf.", "raport.pdf ",
    "katalog.pdf/plik.exe",
])
def test_get_extension_rejects_non_whitelisted(filename):
    with pytest.raises(HTTPException) as exc:
        get_extension(filename)
    assert exc.value.status_code == 400
    assert "rozszerzenie" in exc.value.detail


@pytest.mark.parametrize("filename", ["", None])
def test_get_extension_requires_name(filename):
    with pytest.raises(HTTPException) as exc:
        get_extension(filename)
    assert exc.value.detail == "Brak nazwy pliku."


def test_get_extension_rejects_null_byte():
    with pytest.raises(HTTPException) as exc:
        get_extension("shell.php\x00.pdf")
    assert exc.value.detail == "Nieprawidłowa nazwa pliku."


# --- Poprawne pliki --------------------------------------------------------

@pytest.mark.parametrize("ext", sorted(VALID_SAMPLES))
def test_valid_file_passes_and_returns_canonical_mime(ext):
    content, mime = VALID_SAMPLES[ext]
    file_type = _validate(f"plik{ext}", content, mime)
    assert file_type is ALLOWED_FILE_TYPES[ext]


@pytest.mark.parametrize("declared", [
    None, "", "application/octet-stream", "APPLICATION/PDF", "application/pdf; charset=binary",
    "  application/x-pdf  ",
])
def test_declared_mime_variants_accepted(declared):
    assert _validate("raport.pdf", PDF, declared).mime == "application/pdf"


def test_txt_with_charset_parameter_accepted():
    assert _validate("a.txt", b"tekst", "text/plain; charset=utf-8").mime == "text/plain"


def test_md_accepts_text_plain_declared_mime():
    assert _validate("README.md", b"# Tytul", "text/plain").mime == "text/markdown"


def test_stream_is_rewound_after_validation():
    stream = io.BytesIO(docx_bytes())
    stream.seek(5)
    validate_file("praca.docx", DOCX_MIME, stream, len(stream.getvalue()))
    assert stream.tell() == 0


# --- Niezgodny deklarowany MIME ---------------------------------------------

@pytest.mark.parametrize("filename,content,declared", [
    ("raport.pdf", PDF, "text/html"),
    ("raport.pdf", PDF, "image/png"),
    ("zrzut.png", PNG, "image/jpeg"),
    ("zdjecie.jpg", JPG, "image/png"),
    ("notatki.txt", b"tekst", "application/x-php"),
    ("notatki.txt", b"tekst", "text/html"),
    ("archiwum.zip", zip_bytes({"a": "b"}), "application/x-msdownload"),
    ("praca.docx", docx_bytes(), "application/zip"),
    ("zrzut.png", PNG, "image/svg+xml"),
])
def test_mismatched_declared_mime_rejected(filename, content, declared):
    assert "MIME" in _rejected(filename, content, declared)


# --- Sygnatury (magic bytes) -------------------------------------------------

@pytest.mark.parametrize("filename,content", [
    ("raport.pdf", PHP_SHELL),
    ("raport.pdf", PNG),
    ("raport.pdf", b" %PDF-1.7"),          # sygnatura musi być na samym początku
    ("raport.pdf", b"%PDF"),               # niepełna sygnatura
    ("zrzut.png", JPG),
    ("zrzut.png", SVG_XSS),
    ("zrzut.png", b"\x89PNG"),             # ucięty nagłówek PNG
    ("zdjecie.jpg", PNG),
    ("zdjecie.jpeg", WINDOWS_EXE),
    ("archiwum.zip", PDF),
    ("archiwum.zip", ELF_BINARY),
    ("praca.docx", PDF),
    ("notatki.txt", WINDOWS_EXE),
    ("notatki.txt", ELF_BINARY),
    ("notatki.md", PNG),
])
def test_signature_mismatch_rejected(filename, content):
    assert "sygnatur" in _rejected(filename, content, "application/octet-stream")


def test_empty_file_rejected_before_signature_check():
    assert _rejected("raport.pdf", b"", "application/pdf") == "Przesłany plik jest pusty."


# --- Pliki tekstowe -----------------------------------------------------------

def test_is_text_accepts_utf8():
    # \U00020000 - znak CJK zapisywany w UTF-8 na 4 bajtach
    assert _is_text("Zażółć gęślą jaźń \U00020000".encode("utf-8"))


def test_is_text_rejects_null_byte():
    assert not _is_text(b"tekst\x00ukryty")


def test_is_text_rejects_invalid_utf8_in_the_middle():
    assert not _is_text("Zażółć gęślą jaźń".encode("cp1250"))


def test_is_text_tolerates_multibyte_char_cut_at_the_end():
    assert _is_text("abc ż".encode("utf-8")[:-1])


def test_text_file_longer_than_sniff_window_with_char_on_boundary():
    # 'ż' (2 bajty) zaczyna się na ostatnim bajcie okna SNIFF_BYTES – nie może to dać fałszywego odrzucenia.
    content = b"a" * (SNIFF_BYTES - 1) + "ż".encode("utf-8") + b" dalszy tekst"
    assert _validate("dlugi.txt", content, "text/plain").mime == "text/plain"


def test_binary_after_sniff_window_is_not_inspected_for_text():
    # Udokumentowane zachowanie: dla tekstu sprawdzany jest nagłówek (8 KiB),
    # dlatego plik jest zawsze pobierany jako załącznik application/octet-stream.
    content = b"a" * SNIFF_BYTES + b"\x00\x01"
    assert _validate("plik.txt", content, "text/plain").mime == "text/plain"


# --- Kontenery ZIP / DOCX ----------------------------------------------------

def test_corrupted_zip_rejected():
    assert "archiwum" in _rejected("a.zip", b"PK\x03\x04" + b"\x00" * 50, "application/zip")


def test_truncated_zip_rejected():
    data = zip_bytes({"main.py": "print(1)" * 100})
    assert "archiwum" in _rejected("a.zip", data[: len(data) // 2], "application/zip")


def test_docx_without_document_xml_rejected():
    assert "DOCX" in _rejected("praca.docx", zip_bytes({"a.txt": "x"}), DOCX_MIME)


def test_docx_with_signature_but_corrupted_rejected():
    assert "archiwum" in _rejected("praca.docx", b"PK\x03\x04garbage" * 10, DOCX_MIME)


# --- Nazwa do wyświetlenia -----------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("raport.pdf", "raport.pdf"),
    ("Zażółć gęślą jaźń.txt", "Zażółć gęślą jaźń.txt"),
    ("../../etc/passwd.txt", "passwd.txt"),
    ("..\\..\\Windows\\win.ini.txt", "win.ini.txt"),
    ("<script>alert(1)</script>.txt", "script_.txt"),
    ("raport\r\nSet-Cookie: a=b.txt", "raportSet-Cookie_ a_b.txt"),
    ('a";b.pdf', "a__b.pdf"),
    ("faktura\u202efdp.txt", "fakturafdp.txt"),       # RTL override (podszywanie rozszerzenia)
    ("zero\u200bwidth.pdf", "zerowidth.pdf"),
    ("e\u0301.pdf", "é.pdf"),                          # normalizacja NFC
    ("  ..raport.pdf..  ", "raport.pdf"),
    ("", "plik"),
    (None, "plik"),
    ("...", "plik"),
    ("/", "plik"),
    ("\x00\x01\x02", "plik"),
])
def test_sanitize_display_name(raw, expected):
    assert sanitize_display_name(raw) == expected


def test_sanitize_display_name_truncates_and_keeps_extension():
    name = sanitize_display_name("a" * 1000 + ".pdf")
    assert len(name) == MAX_ORIGINAL_NAME_LENGTH
    assert name.endswith(".pdf")


def test_sanitize_display_name_never_contains_path_separators_or_controls():
    nasty = "..\\../\x7f\x1b[31m/\t\n" + "a/b\\c.pdf"
    name = sanitize_display_name(nasty)
    assert "/" not in name and "\\" not in name
    assert all(ord(ch) >= 32 and ord(ch) != 127 for ch in name)
