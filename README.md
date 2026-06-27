# Search Agent

Projekt ma dwa tryby uruchamiania:

- `docker-compose.yml` - development
- `docker-compose.prod.yml` - production

## Development lokalnie

```powershell
docker-compose up --build
```

Po starcie:

- frontend: `http://localhost:4200`
- backend: `http://localhost:8000`

## Production lokalnie lub na serwerze

```powershell
docker-compose -f docker-compose.prod.yml up --build -d
```

W produkcji frontend jest serwowany przez `nginx` na porcie `80`, a backend dziala wewnatrz sieci Compose.

## GitHub Actions

Dodane workflow:

- `.github/workflows/ci.yml` - build frontu i sprawdzenie backendu
- `.github/workflows/deploy.yml` - deploy na serwer `95.158.64.196`

### Wymagane secrets

W `GitHub -> Settings -> Secrets and variables -> Actions -> Secrets` dodaj:

- `DEPLOY_USER` - uzytkownik SSH na serwerze
- `DEPLOY_SSH_KEY` - prywatny klucz SSH do tego uzytkownika
- `DEPLOY_PATH` - katalog wdrozenia na serwerze, np. `/opt/search-agent`

Workflow deploy jest przypiety do environment `production`, ale sekrety moga byc trzymane na poziomie repo w `Actions secrets`.

### Wymagania na serwerze

- zainstalowany Docker
- zainstalowany `docker compose` albo `docker-compose`
- uzytkownik z prawem uruchamiania Dockera
- otwarty port `80`
- dostep SSH na `95.158.64.196:2222`

## Pierwszy deploy z GitHuba

1. Sprawdz, czy branch z kodem to `master`.
2. Sprawdz, czy w repo sa ustawione secrets:
   - `DEPLOY_USER`
   - `DEPLOY_SSH_KEY`
   - `DEPLOY_PATH`
3. Sprawdz, czy user z `DEPLOY_USER` loguje sie na serwer po porcie `2222` i moze uruchamiac Dockera.
4. Zrob push do `master` lub odpal workflow recznie.

### Reczne odpalenie workflow

1. Wejdz w repo na GitHubie.
2. Otworz zakladke `Actions`.
3. Wybierz workflow `Deploy`.
4. Kliknij `Run workflow`.
5. Wybierz branch i potwierdz uruchomienie.

### Co zrobi workflow

1. Spakuje repo do archiwum.
2. Polaczy sie po SSH na `95.158.64.196:2222`.
3. Wrzuci paczke do `/tmp/search-agent.tar.gz`.
4. Rozpakuje kod do katalogu z `DEPLOY_PATH`.
5. Uruchomi `docker compose -f docker-compose.prod.yml up -d --build`.

### Szybka weryfikacja po deployu

- otwórz `http://95.158.64.196`
- sprawdz backend: `http://95.158.64.196/api/standings`
- jesli cos nie dziala, sprawdz logi workflow w zakladce `Actions`
