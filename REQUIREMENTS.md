# Wymagania i specyfikacja - HomeworkDrop

## Cel aplikacji i na co pozwala
Aplikacja ma na celu ułatwienie i zabezpieczenie procesu oddawania projektów akademickich. Pozwala na wgrywanie plików stanowiących rozwiązania zadań do zdefiniowanego terminu oraz umożliwia wykładowcom ich weryfikację i ocenę w jednym systemie.

## Rodzaje użytkowników i ich możliwości
1. **Student**: Może się zarejestrować, zalogować, przeglądać listę przypisanych zadań, wgrywać i edytować przesłane pliki (tylko do momentu upłynięcia terminu) oraz sprawdzać wystawione oceny i komentarze.
2. **Prowadzący**: Posiada wyższe uprawnienia niż student. Może tworzyć nowe zadania w systemie, ustalać terminy ich oddania, przeglądać i pobierać przesłane prace, a także wystawiać zablokowane do edycji przez studenta oceny.

## Wymagania funkcjonalne
1. Rejestracja i logowanie użytkowników z jawnym podziałem na role.
2. Zapisywanie danych o użytkownikach, zadaniach i przesłanych plikach w relacyjnej bazie danych.
3. Wyświetlanie widoków dopasowanych do roli zalogowanego użytkownika.
4. Możliwość dodawania nowych zadań (tytuł, opis, termin oddania) – funkcja dostępna wyłącznie dla Prowadzącego.
5. Mechanizm wgrywania plików przez studentów z automatyczną blokadą po przekroczeniu ostatecznego terminu.
6. Interfejs pozwalający Prowadzącemu na wystawienie oceny liczbowej oraz dodanie tekstowego komentarza zwrotnego do przesłanej pracy.

## Wymagania bezpieczeństwa
1. **Zabezpieczenie haseł:** Hasła wszystkich użytkowników muszą być haszowane przed zapisem w bazie danych.
2. **Autoryzacja i ochrona sesji:** Wykorzystanie tokenów JWT przesyłanych w ciasteczkach z flagami `HttpOnly` oraz `Secure` w celu ochrony przed atakami XSS.
3. **Kontrola dostępu (RBAC):** Restrykcyjna weryfikacja uprawnień na endpointach API (np. zablokowanie możliwości wywołania metody `POST /grades` przez konto z rolą studenta).
4. **Ochrona przed Mass Assignment:** Wykorzystanie ścisłych modeli i schematów danych na backendzie, aby uniemożliwić studentowi samowolną modyfikację pola z oceną podczas aktualizacji swojego zgłoszenia.
5. **Walidacja załączników:** Filtrowanie wgrywanych plików po stronie serwera – weryfikacja typu MIME, dozwolonych rozszerzeń oraz nałożenie sztywnego limitu rozmiaru pliku (np. max 10 MB).
6. **Zabezpieczenie systemu plików (Path Traversal):** Zapisywanie załączników na serwerze pod losowo generowanymi nazwami (np. UUID) i mapowanie ich w bazie danych, zamiast używania oryginalnych nazw plików podanych przez użytkownika.

## Model zagrożeń

| Zagrożenie | Czego dotyczy | Możliwe konsekwencje | Planowana kontrola/działanie |
| :--- | :--- | :--- | :--- |
| **Atak Path Traversal** | Mechanizm zapisu i pobierania plików prac na serwerze. | Atakujący może odczytać wrażliwe pliki konfiguracyjne serwera (np. `.env`, `/etc/passwd`) lub nieautoryzowanie pobrać prace innych studentów. | Generowanie nazw plików w oparciu o UUID przy zapisie. Bezwzględne odrzucanie w parametrach żądania ciągów znaków takich jak `../`. |
| **Podniesienie uprawnień (Mass Assignment)** | Mechanizm aktualizacji profilu lub edycji przesłanego zadania. | Student poprzez modyfikację zapytania HTTP (np. dopisanie parametru `"grade": 5.0`) samowolnie podwyższa swoją ocenę. | Whitelisting parametrów wejściowych (DTO) – ignorowanie przez API wszelkich nadmiarowych pól, które nie są dozwolone do edycji dla danej roli. |
| **Złośliwy załącznik (Zip Bomb / Web Shell)** | Endpoint `/upload` odbierający pliki od użytkowników. | Wyczerpanie zasobów serwera (OOM / brak miejsca na dysku - DoS) lub wykonanie nieautoryzowanego kodu w przypadku wgrania skryptu. | Twardy limit wielkości przesyłanego pliku na poziomie serwera webowego. Wyłączenie możliwości wykonywania jakichkolwiek plików w katalogu przeznaczonym na upload. |