# Lokal kørsel

Vejledningen beskriver øvelsernes oprindelige arbejdsmappe. Ved en genkørsel i en separat kopi placeres scripts/ i aflevering/scripts/ og hver øvelses .py- og .sql-filer i aflevering/loesninger/NN/. Kørselsloggene kan læses direkte her på GitHub.

Afleveringen er kørt den 20. november 2026 på macOS med Docker Desktop. Alle resultater kan læses uden at starte Docker. Denne vejledning beskriver, hvordan samme testforløb kan gentages i en ny labinstans.

## Genkørsel fra det eksisterende arbejdsområde

Docker Desktop skal køre. Python 3.9 eller nyere, OpenSSL og Docker Compose v2 skal være tilgængelige. PostgreSQL og pgbench køres fra det officielle postgres:18-image. Øvelse 13 bruger desuden psycopg som libpq-klient på værten. Det isolerede Python-miljø ligger allerede i kontrol/hostclient. Pakken blev verificeret i version 3.3.9.

```sh
cd ~/Projects/postgres-sec-aflevering
python3 aflevering/scripts/lab.py 01 02 03 04 05 06 07 08 09 10 11 12 13
```

Et enkelt nummer vælger én øvelse, f.eks. `python3 aflevering/scripts/lab.py 12`. Hver genkørsel opretter en ny mappe under `kontrol/gentest-*` og skriver den nøjagtige logsti til terminalen. Status for hver øvelse står i dens seneste.txt. Afleveringens originale beviser bliver liggende. En fejl i en øvelse føres til protokols, de øvrige valgte øvelser fortsætter, og programmet returnerer en fejlkode ved delvise resultater.

## På en anden Mac

Læg denne afleveringsmappe i en ny, tom arbejdsmappe. Kør nedenstående fra den nye arbejdsmappe. Den lokale kildekopi er en søstermappe til aflevering. Kontrolmappen indeholder den private klientinstallation, eventuelle senere backupfiler og midlertidige filer. Første download kræver netadgang til GitHub, Docker Hub og Pythons pakkeregister.

```sh
umask 077
mkdir -p kontrol
git clone https://github.com/andracs/postgres-sec-exercises.git kilde
git -C kilde checkout --detach 8e6c75bd0356755c88e3cd8c3cd58f879b80dec8
docker pull postgres@sha256:eb63372c1e05c755f55fa30cbd07aecc443676fc6c0fa90b9002d01537841e1a
python3 -m venv kontrol/hostclient
kontrol/hostclient/bin/python -m pip install 'psycopg[binary]==3.3.9'
```

Testprogrammet anvender `postgres:18`. Den verificerede kørsel brugte 18.7. Ved genkørsel med samme præcise image kan Docker-referencen angives gennem `DBSEC_IMAGE`. Brug nedenstående for at gentage målingen med den registrerede digest.

```sh
export DBSEC_IMAGE=postgres@sha256:eb63372c1e05c755f55fa30cbd07aecc443676fc6c0fa90b9002d01537841e1a
python3 aflevering/scripts/lab.py 01 02 03 04 05 06 07 08 09 10 11 12 13
```

## Afgrænsning og beviser

- Hvert projekt får et unikt navn og projektets egne volumener. Compose-konfigurationen registreres før opstart. Før og efter den afleverede kørsel blev eksisterende Docker-ressourcer sammenlignet i [miljøkontrollen](miljoe.txt).
- Øvelse 01–12 bruger containerens socket eller et internt Docker-netværk. Øvelse 13 publicerer på en automatisk tildelt port på 127.0.0.1 og vælger to forskellige subnet uden overlap med eksisterende Docker-net. Klienter til positive og negative forsøg har hver sin kildeadresse.
- Almindelige labdatabaser har højst to CPU’er og 1,5 GiB hukommelse. Overdimensionering prøves med et særskilt procesloft. Ved samtidighed bruges adskilte psql-processer med ventepunkter og tidsgrænser. Forventede afvisninger kræver en fejl fra det rigtige lag, f.eks. SQLSTATE 42501 eller en udtrykkelig HBA-afvisning.
- Øvelse 12 bevarer det logiske dump, fysisk backup og WAL i den private mappe `kontrol/dbsec12-*/`. Arbejdsområdets aflevering bruger `kontrol/dbsec12-ad6bgahy/`. Mapperne ligger uden for afleveringen, fordi en fysisk backup også indeholder clusterets egne sikkerhedsdata. Den gendannede instans og begge datavolumener blev fjernet efter testen.
- Øvelse 13 anvender underviserens setup.sh med en forhåndsgenereret app-hemmelighed. De fire forbindelsestests er skrevet om, så hver afvisning skal have den forventede årsag. Certifikatets private nøgle og adgangskoderne ligger kun i kørslens private arbejdsfiler under testen. Kun åbne metadata og testudfald gemmes i bilagene.
- SQL og scripts til en øvelse findes i `loesninger/NN/`. Kør dem via fællesprogrammet, så databasens identitet, testdata, indstillinger og klientroller oprettes som ved den oprindelige kørsel.
