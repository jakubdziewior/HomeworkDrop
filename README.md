# HomeworkDrop (Platforma do przesyłania prac studenckich)

## Członkowie zespołu
* Jakub Dziewior
* Jakub Wodyk

## Wybrane technologie
* **Backend:** Python + FastAPI
* **Frontend:** TypeScript + Next.js (React) + Tailwind CSS
* **Baza danych:** PostgreSQL (docelowo) / SQLite (dewelopersko)

## Opis
HomeworkDrop to bezpieczna platforma edukacyjna rozwiązująca problem w komunikacji podczas oddawania projektów akademickich. Umożliwia studentom wgrywanie rozwiązań zadań przed upływem określonego terminu, a prowadzącym zapewnia dedykowane miejsce do zarządzania pracami, ich bezpiecznego pobierania oraz wystawiania ocen i komentarzy zwrotnych.

---

## Wymagania środowiskowe
* **System operacyjny:** Windows 10/11, Linux lub macOS
* **Python:** wersja 3.10 lub nowsza
* **Node.js:** wersja 18.0 lub nowsza
* **Menedżer pakietów:** pip oraz npm

---

## Sposób instalacji

1. Sklonuj repozytorium:
   ```bash
   git clone https://github.com/jakubdziewior/HomeworkDrop.git
   cd HomeworkDrop
   ```

2. Konfiguracja środowiska backendowego (Python):
   ```bash
   python -m venv .venv
   ```
   Aktywacja środowiska:
   * **Windows (PowerShell):**
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   * **Linux / macOS:**
     ```bash
     source .venv/bin/activate
     ```

   Instalacja zależności backendowych:
   ```bash
   pip install -r requirements.txt
   ```

   Utworzenie pliku konfiguracyjnego:
   ```bash
   cp .env.example .env
   ```

3. Konfiguracja środowiska frontendowego (Next.js):
   ```bash
   cd frontend
   npm install
   cd ..
   ```

---

## Sposób uruchomienia

### 1. Uruchomienie Backend API (FastAPI)
W głównym katalogu projektu wykonaj polecenie:
```bash
python run.py
```
Alternatywnie bezpośrednio za pomocą uvicorn:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Uruchomienie Frontendu (Next.js)
W osobnym oknie terminala przejdź do katalogu `frontend` i uruchom serwer deweloperski:
```bash
cd frontend
npm run dev
```

---

## Adresy aplikacji
* **Aplikacja kliencka (Frontend):** [http://localhost:3000](http://localhost:3000)
* **Backend API:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Endpoint sprawdzania stanu (Health Check):** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
* **Interaktywna dokumentacja Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Dokumentacja ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Opis endpointu /health

Endpoint służy do weryfikacji dostępności usługi i stanu działania aplikacji. Jest dostępny publicznie (bez wymogu uwierzytelniania).

* **Metoda HTTP:** `GET`
* **Ścieżka:** `/health`
* **Wymagane uprawnienia:** Brak (dostęp publiczny)
* **Zwracany kod statusu HTTP:** `200 OK`
* **Format odpowiedzi:** `application/json`

### Zwracana odpowiedź JSON:
```json
{
  "status": "ok"
}
```

---

## Przykładowe żądania do endpointu /health

### cURL:
```bash
curl -X GET http://127.0.0.1:8000/health
```

### PowerShell:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get
```

### JavaScript (fetch):
```javascript
const response = await fetch("http://127.0.0.1:8000/health");
const data = await response.json();
console.log(data);
```

---

## Autoryzacja (JWT w ciasteczkach HttpOnly)

* `POST /api/v1/auth/login` – po poprawnym logowaniu backend ustawia ciasteczko `access_token` z tokenem JWT (flagi `HttpOnly`, `Secure`, `SameSite=Strict`). Token **nie** jest zwracany w treści odpowiedzi, więc JavaScript (i ewentualny atak XSS) nie ma do niego dostępu.
* `GET /api/v1/auth/me` – zwraca dane zalogowanego użytkownika na podstawie ciasteczka (401, jeśli brak/niepoprawny token).
* `POST /api/v1/auth/logout` – usuwa ciasteczko.
* Token zawiera `sub`, `role`, `iat`, `nbf`, `exp`, `iss`, `aud`, `jti`; weryfikowany jest podpis, czas ważności, wystawca i odbiorca (tokeny `alg=none` są odrzucane).
* Ochrona endpointów w kodzie: `Depends(get_current_user)` lub RBAC `Depends(require_role("teacher"))` z [app/dependencies.py](app/dependencies.py).
* Frontend łączy się z API przez proxy Next.js (`/api/*` → `BACKEND_URL`, domyślnie `http://127.0.0.1:8000`), dzięki czemu ciasteczko jest first-party. Aplikację otwieraj pod adresem `http://localhost:3000`.
* W trybie `APP_ENV=development` backend tworzy konta testowe używane przez przyciski „Szybkie logowanie testowe”.
* W produkcji (`APP_ENV=production`) aplikacja nie wystartuje z domyślnym `SECRET_KEY` ani z wyłączonym `AUTH_COOKIE_SECURE`.

---

## Zadania (CRUD z RBAC)

| Metoda | Ścieżka | Dostęp |
| :--- | :--- | :--- |
| `GET` | `/api/v1/tasks` | każdy zalogowany (lista posortowana po terminie) |
| `GET` | `/api/v1/tasks/{id}` | każdy zalogowany |
| `POST` | `/api/v1/tasks` | tylko prowadzący |
| `PATCH` | `/api/v1/tasks/{id}` | tylko prowadzący – autor zadania |
| `DELETE` | `/api/v1/tasks/{id}` | tylko prowadzący – autor zadania |

* Brak zalogowania → `401`, zła rola lub cudze zadanie → `403`, brak zadania → `404`.
* Pola wejściowe: `title` (3–200 znaków), `description` (do 5000 znaków), `deadline` (data ISO 8601 ze strefą czasową, musi być w przyszłości).
* Schematy odrzucają nadmiarowe pola (np. `created_by`, `id`) – ochrona przed Mass Assignment.
* Odpowiedź zawiera pole `is_expired`, wyliczane na podstawie terminu.

---

## Wgrywanie plików (zgłoszenia)

| Metoda | Ścieżka | Dostęp |
| :--- | :--- | :--- |
| `POST` | `/api/v1/tasks/{id}/submissions` | student, tylko przed terminem (`multipart/form-data`, pole `file`) |
| `GET` | `/api/v1/tasks/{id}/submissions` | prowadzący – autor zadania |
| `GET` | `/api/v1/tasks/{id}/submissions/me` | student – własne zgłoszenie |
| `GET` | `/api/v1/submissions/{id}/download` | autor zgłoszenia lub prowadzący zadania |

Zabezpieczenia:
* **Limit rozmiaru** (`MAX_UPLOAD_SIZE_MB`, domyślnie 10 MB) egzekwowany przez middleware na strumieniu żądania – zbyt duże żądania są przerywane (`413`), zanim trafią na dysk.
* **Whitelista rozszerzeń:** `.pdf`, `.zip`, `.docx`, `.png`, `.jpg`/`.jpeg`, `.txt`, `.md`.
* **Weryfikacja MIME:** deklarowany `Content-Type` musi pasować do rozszerzenia, a rzeczywisty typ jest sprawdzany po sygnaturze pliku (magic bytes); archiwa ZIP/DOCX są sprawdzane pod kątem poprawności (bez rozpakowywania).
* **UUID zamiast nazw użytkownika:** pliki zapisywane są jako `<uuid4>.<rozszerzenie>` w `UPLOAD_DIR`; oryginalna nazwa jest oczyszczana i służy tylko do wyświetlenia. Każda ścieżka jest sprawdzana, czy leży w katalogu uploadu.
* **Pobieranie** zawsze jako załącznik `application/octet-stream` z `X-Content-Type-Options: nosniff` i restrykcyjnym CSP; brak dostępu do cudzych plików (`404`, ochrona przed IDOR).
* Ponowne wgranie przed terminem zastępuje poprzedni plik; po terminie wgrywanie jest blokowane.

---

## Ocenianie (ochrona przed Mass Assignment)

`PUT /api/v1/submissions/{id}/grade` – tylko prowadzący, który utworzył zadanie (inny prowadzący → `404`, student → `403`).

```json
{ "grade": 4.5, "feedback": "Dobra robota." }
```

* `grade` – liczba ze skali `2.0, 3.0, 3.5, 4.0, 4.5, 5.0` (bez niejawnej konwersji tekstu czy wartości logicznych), `feedback` – do 2000 znaków.
* Schemat `GradeRequest` ma `extra="forbid"`: każde inne pole (`graded_by`, `student_id`, `status`, …) → `422`. Pola `status`, `graded_by`, `graded_at` ustawia wyłącznie serwer.
* Endpoint wgrywania pliku przyjmuje wyłącznie pole `file` – próba dosłania np. `grade=5.0` w formularzu kończy się `422`.
* Po wystawieniu oceny student nie może podmienić pliku (`409`) – ocena dotyczy zawsze tej wersji, którą sprawdził prowadzący.

---

## Baza danych

Warstwa danych oparta jest na SQLAlchemy 2 ([app/models.py](app/models.py), [app/database.py](app/database.py)). Adres bazy ustawia `DATABASE_URL`:
* dewelopersko: `sqlite:///./homeworkdrop.db` (domyślnie),
* docelowo PostgreSQL: `postgresql+psycopg://user:haslo@host:5432/homeworkdrop` (wymaga `pip install "psycopg[binary]"`).

Inicjalizacja schematu (tabele tworzone są też automatycznie przy starcie API):
```bash
python -m app.init_db            # tworzy brakujące tabele
python -m app.init_db --seed     # + konta testowe (tylko APP_ENV=development)
python -m app.init_db --sql      # podgląd DDL (CREATE TABLE ...)
```

```mermaid
erDiagram
    users ||--o{ tasks : "tworzy (created_by)"
    users ||--o{ submissions : "przesyła (student_id)"
    users |o--o{ submissions : "ocenia (graded_by)"
    tasks ||--o{ submissions : "dotyczy (task_id)"

    users {
        int id PK
        varchar email UK
        varchar hashed_password
        varchar full_name
        varchar role "student | teacher"
        datetime created_at
    }
    tasks {
        int id PK
        varchar title
        text description
        datetime deadline
        int created_by FK
        datetime created_at
        datetime updated_at
    }
    submissions {
        int id PK
        int task_id FK
        int student_id FK
        varchar original_filename
        varchar stored_filename UK "UUID"
        varchar content_type
        int size_bytes
        varchar sha256
        varchar status "submitted | graded"
        numeric grade "2.0-5.0"
        text feedback
        int graded_by FK
        datetime submitted_at
        datetime updated_at
        datetime graded_at
    }
```

Integralność wymuszana na poziomie bazy (nie tylko w API):
* unikalny e-mail, rola tylko `student`/`teacher`,
* jedno zgłoszenie studenta na zadanie (`UNIQUE (task_id, student_id)`), unikalna nazwa pliku na dysku,
* ocena tylko ze skali, a `status = 'graded'` ⇔ ocena ustawiona (`CHECK`),
* usunięcie zadania usuwa jego zgłoszenia (`ON DELETE CASCADE`), nie można usunąć prowadzącego, który ma zadania (`RESTRICT`),
* wszystkie daty przechowywane w UTC; w SQLite włączane jest `PRAGMA foreign_keys=ON`.

Testy korzystają z osobnej bazy SQLite w pamięci ([tests/conftest.py](tests/conftest.py)).

---

## Testy

**Narzędzie:** [pytest](https://docs.pytest.org/) 9.2.0 (instalowany z `requirements.txt`) + `fastapi.testclient.TestClient`. Aplikacja jest uruchamiana w procesie testów – nie trzeba startować serwera, frontendu ani bazy danych, a testy nie łączą się z siecią.

### Uruchomienie

Jedno polecenie uruchamiające **wszystkie** testy (z katalogu głównego projektu, przy aktywnym `.venv`):

```bash
python -m pytest
```

Pozostałe warianty:

```bash
python -m pytest -v                    # pełny zestaw z nazwą każdego testu (511 testów, ~15 s)
python -m pytest -m unit               # tylko testy jednostkowe
python -m pytest -m integration        # tylko testy integracyjne
python -m pytest -m security           # tylko scenariusze bezpieczeństwa
python -m pytest -m endpoint           # tylko test endpointu /health
python -m pytest tests/security/test_jwt_attacks.py -v       # pojedynczy plik
python -m pytest -k "zip_bomb or polyglot" -v                # wybrane testy po nazwie
python -m pytest tests/test_health.py -v                     # test endpointu /health
python -m pytest --junitxml=raport-testow.xml                # wynik w formacie JUnit XML (CI, plik w .gitignore)
```

### Zakres testów (wymagania etapu 3)

| Rodzaj | Wymagane minimum | Liczba testów | Lokalizacja |
| :--- | ---: | ---: | :--- |
| Testy jednostkowe (`-m unit`) | 8 | 219 | `tests/unit/`, `tests/test_auth.py`, `tests/test_deadline.py`, `tests/test_schemas_validation.py` |
| Testy integracyjne (`-m integration`) | 5 | 12 | `tests/integration/`, `tests/test_integration_auth_tasks.py` |
| Scenariusze bezpieczeństwa (`-m security`) | 2 | 143 | `tests/security/`, `tests/test_security_access.py` |
| Test endpointu `/health` (`-m endpoint`, kod 200 i `{"status": "ok"}`) | 1 | 1 | `tests/test_health.py` |
| Pozostałe testy API z wcześniejszych etapów (bez markera) | – | 136 | `tests/test_*.py` |

Liczby to przypadki testowe w rozumieniu pytest (każdy wariant parametryzacji liczy się osobno).

Konfiguracja znajduje się w [pytest.ini](pytest.ini) (katalog `tests`, `pythonpath = .`, rejestracja markerów, `--strict-markers`). Testy w katalogach `tests/unit`, `tests/integration` i `tests/security` dostają marker automatycznie na podstawie katalogu ([tests/conftest.py](tests/conftest.py)); testy w `tests/test_*.py` mają marker podany jawnie dekoratorem (np. `@pytest.mark.unit`).

### Izolacja środowiska testowego

* Baza: SQLite w pamięci (`DATABASE_URL=sqlite://`), tworzona od zera przed **każdym** testem – każdy test sam tworzy potrzebne dane, więc wynik nie zależy od poprzednich uruchomień ani od kolejności testów.
* `APP_ENV=test` – lokalny plik `.env` nie jest wczytywany (testy nie zależą od konfiguracji komputera), nie są tworzone konta demonstracyjne.
* bcrypt w testach używa kosztu 4 zamiast 12 (fixture `fast_password_hashing`) – dzięki temu cały zestaw trwa kilkanaście sekund.
* Pliki: każdy test dostaje własny katalog tymczasowy jako `UPLOAD_DIR` (fixture `upload_dir`), więc testy nigdy nie zapisują nic w `./uploads`.
* Wspólne dane testowe (użytkownicy, przykładowe pliki PDF/PNG/ZIP/DOCX, ładunki ataków) i funkcje pomocnicze: [tests/helpers.py](tests/helpers.py).

### Struktura

| Katalog / plik | Rodzaj | Co sprawdza |
| :--- | :--- | :--- |
| [tests/unit/test_file_validation.py](tests/unit/test_file_validation.py) | jednostkowe | whitelista rozszerzeń, zgodność deklarowanego MIME, sygnatury (magic bytes) wszystkich typów, pliki tekstowe (UTF-8, bajt NUL, granica 8 KiB), kontenery ZIP/DOCX, oczyszczanie nazwy (Path Traversal, CRLF, RTL override, NFC, długość) |
| [tests/unit/test_grade_scale.py](tests/unit/test_grade_scale.py) | jednostkowe | skala `2.0–5.0`, brak niejawnej konwersji (`"5.0"`, `true`, `Decimal`), NaN/∞, wartości graniczne, komentarz (przycinanie, limit 2000), `extra="forbid"`, zgodność skali z ograniczeniem `CHECK` w bazie |
| [tests/unit/test_storage_service.py](tests/unit/test_storage_service.py) | jednostkowe | zapis pod nazwą UUID, SHA-256, unikalność nazw, odrzucanie nazw spoza wzorca (`../`, ścieżki bezwzględne, NUL), 404 dla brakującego pliku |
| [tests/integration/test_submission_workflow.py](tests/integration/test_submission_workflow.py) | integracyjne | pełny obieg: rejestracja → zadanie → wgranie (PDF/ZIP/DOCX) → poprawka → lista i pobranie przez prowadzącego (zgodność SHA-256) → ocena → podgląd oceny przez studenta → blokada po ocenie → termin → zmiana oceny → usunięcie zadania z plikami; izolacja między zadaniami i prowadzącymi |
| [tests/security/test_upload_attacks.py](tests/security/test_upload_attacks.py) | bezpieczeństwo | web shell (`.php`, `.jsp`, `.aspx`, `.htaccess`), podwójne rozszerzenia, polyglot PDF/PHP, HTML/SVG (stored XSS), zip bomb i zip slip, Path Traversal w nazwie i identyfikatorze, bajt NUL, limit rozmiaru (fałszywy/niepoprawny `Content-Length`), brak wycieku ścieżek |
| [tests/security/test_mass_assignment.py](tests/security/test_mass_assignment.py) | bezpieczeństwo | student próbuje wystawić sobie ocenę (JSON, formularz, query string, drugi plik), podmiana `graded_by`/`student_id`, przejęcie zadania, eskalacja roli przy rejestracji, brak hasha hasła w odpowiedziach |
| [tests/security/test_jwt_attacks.py](tests/security/test_jwt_attacks.py) | bezpieczeństwo | fałszywa rola w tokenie, manipulacja payloadem, `alg=none` (różne wielkości liter), inny algorytm HMAC, słabe klucze, `jku`/`kid`, błędne `iss`/`aud`/`exp`/`nbf`/`sub`, wymagane claimy, token tylko z ciasteczka, wylogowanie, odmowa startu z niebezpieczną konfiguracją |
| [tests/test_auth.py](tests/test_auth.py) | jednostkowe | hashowanie i weryfikacja haseł (też uszkodzony hash), każda reguła siły hasła osobno, rejestracja (normalizacja e-maila, duplikat, zły e-mail, zła rola), logowanie |
| [tests/test_deadline.py](tests/test_deadline.py) | jednostkowe | blokada terminu: przed/po terminie, dokładna granica, sekunda po terminie, różne strefy czasowe |
| [tests/test_schemas_validation.py](tests/test_schemas_validation.py) | jednostkowe | schematy wejściowe: przycinanie imienia i tytułu, odrzucanie pustych/za krótkich wartości, puste hasło przy logowaniu |
| [tests/test_integration_auth_tasks.py](tests/test_integration_auth_tasks.py) | integracyjne | rejestracja → logowanie → tworzenie, edycja, usuwanie i lista zadań; student widzi zadania prowadzącego; wylogowanie odcina dostęp; termin blokuje spóźnione wgranie |
| [tests/test_security_access.py](tests/test_security_access.py) | bezpieczeństwo | słabe hasła przy rejestracji, żądania bez logowania, RBAC (student nie tworzy/edytuje/usuwa zadań), cudze zadania prowadzącego, eskalacja uprawnień i wyciek hasha przy rejestracji |
| [tests/test_health.py](tests/test_health.py) | endpoint | `GET /health` zwraca 200 i `{"status": "ok"}` |
| pozostałe `tests/test_*.py` | funkcjonalne (API) | JWT w ciasteczku, CRUD zadań z RBAC, wgrywanie plików, ocenianie, ograniczenia bazy danych |

### Ostatni wynik

| Zestaw | Liczba testów | Wynik |
| :--- | ---: | :--- |
| jednostkowe (`-m unit`) | 219 | zaliczone |
| integracyjne (`-m integration`) | 12 | zaliczone |
| bezpieczeństwa (`-m security`) | 143 | zaliczone |
| endpoint (`-m endpoint`) | 1 | zaliczone |
| pozostałe testy API | 136 | zaliczone |
| **Razem** | **511** | **511 passed, 0 failed (~15 s)** |

Python 3.11.9, pytest 9.2.0, Windows 11 (25.11.2026). Wynik nie zależy od kolejności (sprawdzone w kolejności odwróconej i losowej). Pełny raport ze zrzutami ekranu: [docs/Raport_testow_HomeworkDrop.pdf](docs/Raport_testow_HomeworkDrop.pdf).

### Dodawanie nowych testów

* Test jednostkowy → `tests/unit/`, integracyjny → `tests/integration/`, scenariusz bezpieczeństwa → `tests/security/` – marker zostanie dodany automatycznie. Test umieszczony bezpośrednio w `tests/` trzeba oznaczyć dekoratorem (`@pytest.mark.unit` itd.); dzięki `--strict-markers` literówka w nazwie markera kończy się błędem.
* Do logowania używaj `logged_in(USER)` z [tests/helpers.py](tests/helpers.py) – zwraca klienta z ciasteczkiem JWT (`base_url="https://testserver"`, bo ciasteczko ma flagę `Secure`).
* Testy bezpieczeństwa powinny sprawdzać nie tylko kod odpowiedzi, ale też **brak skutku** ataku (stan bazy przed/po, zawartość `upload_dir`).
