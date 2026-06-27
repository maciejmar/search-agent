# Search Agent

Projekt jest przygotowany do uruchamiania w Docker Compose:

- `frontend/` - Angular 19
- `backend/` - Python + FastAPI + LangGraph

## Start przez Docker Compose

```powershell
docker-compose up --build
```

Po starcie:

- frontend: `http://localhost:4200`
- backend: `http://localhost:8000`
- endpoint danych: `http://localhost:8000/api/standings`

Frontend uzywa proxy `/api`, wiec z poziomu przegladarki komunikuje sie z backendem przez Angular dev server uruchomiony w kontenerze.

## Zatrzymanie

```powershell
docker-compose down
```

## Uwagi

- backend jest uruchamiany z `--reload`
- frontend jest uruchamiany przez `ng serve` na `0.0.0.0`
- zmiany w `frontend/src` i `backend/app` sa montowane jako volume, wiec odswiezanie dziala podczas pracy z kontenerami
