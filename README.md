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

W produkcji frontend jest serwowany przez kontenerowy `nginx` na `127.0.0.1:8082`, a backend przez `uvicorn` na `127.0.0.1:8003`. Publiczna domena jest obslugiwana przez hostowy `nginx` z `sites-available`.

Docelowy adres aplikacji to `https://search-agent.webaby.io`.

## Dlaczego porty 8082 i 8003

Te porty zostaly wybrane jako wolne na podstawie listingu z serwera, ktory pokazal konflikt z `office-assistant` na `127.0.0.1:8080` i `127.0.0.1:8001`.

Przed deployem warto to jeszcze potwierdzic na serwerze:

```bash
sudo ss -ltnp | grep -E '8082|8003'
```

Jesli wynik jest pusty, porty sa wolne.

## Host nginx na serwerze

Gotowe pliki do `sites-available` sa w repo:

- `deploy/nginx/search-agent.webaby.io.conf` - wariant startowy bez SSL
- `deploy/nginx/search-agent.webaby.io.ssl-example.conf` - wariant po wystawieniu certyfikatu

Ten uklad dziala tak:

- `location /` -> `http://127.0.0.1:8082`
- `location /api/` -> `http://127.0.0.1:8003`

### Krok 1: uruchom wariant bez SSL

Na serwerze:

```bash
sudo cp /opt/search-agent/deploy/nginx/search-agent.webaby.io.conf /etc/nginx/sites-available/search-agent.webaby.io
sudo ln -sf /etc/nginx/sites-available/search-agent.webaby.io /etc/nginx/sites-enabled/search-agent.webaby.io
sudo nginx -t
sudo systemctl reload nginx
```

### Krok 2: wystaw certyfikat

```bash
sudo certbot --nginx -d search-agent.webaby.io
```

### Krok 3: automatyczne odnawianie certyfikatu

Certbot na tym serwerze ma juz aktywny `certbot.timer`, wiec nie trzeba dokladac drugiego timera, jesli `systemctl status certbot.timer` pokazuje stan `active`.

## GitHub Actions

Dodane workflow:

- `.github/workflows/ci.yml` - build frontu i sprawdzenie backendu
- `.github/workflows/deploy.yml` - deploy na serwer `95.158.64.196`

### Wymagane secrets

W `GitHub -> Settings -> Secrets and variables -> Actions -> Secrets` dodaj:

- `DEPLOY_USER` - uzytkownik SSH na serwerze
- `DEPLOY_SSH_KEY` - prywatny klucz SSH do tego uzytkownika
- `DEPLOY_PATH` - katalog wdrozenia na serwerze, np. `/opt/search-agent`

## Wymagania na serwerze

- zainstalowany Docker
- zainstalowany `docker compose` albo `docker-compose`
- zainstalowany hostowy `nginx`
- zainstalowany `certbot`
- uzytkownik z prawem uruchamiania Dockera
- dostep SSH na `95.158.64.196:2222`
- rekord DNS `search-agent.webaby.io -> 95.158.64.196`
- wolne porty `80` i `443` dla hostowego `nginx`
- wolne lokalne porty `127.0.0.1:8082` i `127.0.0.1:8003`

## Szybka weryfikacja po deployu

- otworz `https://search-agent.webaby.io`
- sprawdz backend: `https://search-agent.webaby.io/api/standings`
- lokalnie na serwerze sprawdz `curl http://127.0.0.1:8082`
- lokalnie na serwerze sprawdz `curl http://127.0.0.1:8003/api/standings`
