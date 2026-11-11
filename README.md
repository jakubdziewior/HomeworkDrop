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
