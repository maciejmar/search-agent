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

W produkcji frontend jest serwowany przez kontenerowy `nginx` na `127.0.0.1:8080`, a backend przez `uvicorn` na `127.0.0.1:8001`. Publiczna domena jest obslugiwana przez hostowy `nginx` z `sites-available`.

Docelowy adres aplikacji to `https://search-agent.webaby.io`.

## Host nginx na serwerze

Gotowe pliki do `sites-available` sa w repo:

- `deploy/nginx/search-agent.webaby.io.conf` - wariant startowy bez SSL
- `deploy/nginx/search-agent.webaby.io.ssl-example.conf` - wariant po wystawieniu certyfikatu

Ten uklad dziala tak:

- `location /` -> `http://127.0.0.1:8080`
- `location /api/` -> `http://127.0.0.1:8001`

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

W repo sa gotowe pliki:

- `deploy/certbot/certbot-renew-nginx.sh`
- `deploy/certbot/certbot-renew.service`
- `deploy/certbot/certbot-renew.timer`

Instalacja na serwerze:

```bash
sudo cp /opt/search-agent/deploy/certbot/certbot-renew.service /etc/systemd/system/certbot-renew.service
sudo cp /opt/search-agent/deploy/certbot/certbot-renew.timer /etc/systemd/system/certbot-renew.timer
sudo systemctl daemon-reload
sudo systemctl enable --now certbot-renew.timer
sudo systemctl status certbot-renew.timer
```

Timer odpala odnowienie dwa razy dziennie i po skutecznym odnowieniu robi `systemctl reload nginx`.

Reczne sprawdzenie:

```bash
sudo systemctl start certbot-renew.service
sudo journalctl -u certbot-renew.service -n 50 --no-pager
```

Jesli wolisz cron zamiast systemd timera, mozesz uzyc:

```bash
sudo crontab -e
```

i dodac:

```cron
0 3,15 * * * certbot renew --quiet --deploy-hook "systemctl reload nginx"
```

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

## Szybka weryfikacja po deployu

- otworz `http://search-agent.webaby.io` przed SSL
- po certyfikacie otworz `https://search-agent.webaby.io`
- sprawdz backend: `http://search-agent.webaby.io/api/standings`
- lokalnie na serwerze sprawdz `curl http://127.0.0.1:8080`
- lokalnie na serwerze sprawdz `curl http://127.0.0.1:8001/api/standings`
