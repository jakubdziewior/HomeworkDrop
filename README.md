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
