# Migracje bazy danych

Migracje są obsługiwane przez Alembic. Po uruchomieniu nowego kontenera
PostgreSQL z pustą bazą należy zastosować wszystkie migracje, aby utworzyć
wymagane tabele.

Polecenia wykonuj z głównego katalogu projektu:

```bash
docker compose up -d
uv run --env-file .env alembic upgrade head
```

Przed uruchomieniem migracji upewnij się, że:

- kontener PostgreSQL jest gotowy do przyjmowania połączeń;
- plik `.env` istnieje i zawiera poprawny `DATABASE_URL` wskazujący na
  uruchomioną bazę;
- zależności projektu zostały zainstalowane (w razie potrzeby wykonaj
  `uv sync`).

Polecenie `alembic upgrade head` wykonuje wszystkie niewykonane migracje aż do
najnowszej wersji. Można więc uruchamiać je zarówno dla pustej bazy, jak i po
dodaniu kolejnych migracji.

Aktualnie zastosowaną wersję migracji można sprawdzić poleceniem:

```bash
uv run --env-file .env alembic current
```
