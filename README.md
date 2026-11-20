# Databasesikkerhed – bilag til PostgreSQL 18

Bilag til Lauges aflevering i Systemsikkerhed, 20. november 2026. Tabellen fører til SQL og testkode, registreret slutstatus og de faktiske kørselslogs for hver øvelse. SQL, der blev sendt fra Python, findes både i testprogrammet og i loggen.

| Øvelse | Løsning | Testresultat | Kørselslogs |
|---|---|---|---|
| [01 · Hukommelse og gennemløb](01/) | [Test og SQL](01/test.py) | [PASS](01/seneste.txt) | [Afsluttende log](01/dbsec01-8tul2kp4.txt) · [Gentagelse](01/dbsec01-q_wu9adu.txt) |
| [02 · Statistik og ANALYZE](02/) | [Test og SQL](02/test.py) | [PASS](02/seneste.txt) | [Afsluttende log](02/dbsec02-qf571e50.txt) |
| [03 · Eksekveringsplaner](03/) | [Test og SQL](03/test.py) | [PASS](03/seneste.txt) | [Afsluttende log](03/dbsec03-slap332g.txt) |
| [04 · Indeksøkonomi](04/) | [Test og SQL](04/test.py) | [PASS](04/seneste.txt) | [Afsluttende log](04/dbsec04-cz_8r9ol.txt) |
| [05 · Normalisering til 3NF](05/) | [migrering.sql](05/migrering.sql) · [Test og SQL](05/test.py) | [PASS](05/seneste.txt) | [Afsluttende log](05/dbsec05-c6vffng1.txt) |
| [06 · Aktivitet og låse](06/) | [Test og SQL](06/test.py) | [PASS](06/seneste.txt) | [Afsluttende log](06/dbsec06-w2cco0qb.txt) |
| [07 · Logging](07/) | [Test og SQL](07/test.py) | [PASS](07/seneste.txt) | [Afsluttende log](07/dbsec07-srn65cvu.txt) |
| [08 · Roller og RLS](08/) | [Test og SQL](08/test.py) | [PASS](08/seneste.txt) | [Afsluttende log](08/dbsec08-tksi_dqc.txt) · [Gentagelse](08/dbsec08-2jfp8pwy.txt) |
| [09 · Transaktioner](09/) | [Test og SQL](09/test.py) | [PASS](09/seneste.txt) | [Afsluttende log](09/dbsec09-saihljau.txt) |
| [10 · Triggere og audit](10/) | [Test og SQL](10/test.py) | [PASS](10/seneste.txt) | [Afsluttende log](10/dbsec10-zh5wl6il.txt) · [Gentagelse](10/dbsec10-fdttonsi.txt) |
| [11 · Kryptering](11/) | [Test og SQL](11/test.py) | [PASS](11/seneste.txt) | [Afsluttende log](11/dbsec11-nh27rcnt.txt) · [Første forsøg](11/dbsec11-j4y9358n.txt) · [Andet forsøg](11/dbsec11-sdhx62pa.txt) |
| [12 · Backup og PITR](12/) | [Test og SQL](12/test.py) | [PASS](12/seneste.txt) | [Afsluttende log](12/dbsec12-ad6bgahy.txt) |
| [13 · Hardening og challenge](13/) | [rettigheder.sql](13/rettigheder.sql) · [Test og SQL](13/test.py) | [PASS](13/seneste.txt) | [Afsluttende log](13/dbsec13-hmwm2fj9.txt) |

De 13 afsluttende kørsler bestod. Øvelse 11 indeholder også de to tidligere forsøg med en fejlet kontrol, så rettelsen kan følges. Den selvstændige challenge i øvelse 13 indgår i samme testprogram og afsluttende log som netværks- og TLS-testene.

## Fælles dokumentation

- [Miljø, Docker-versioner og kildecommit](dokumentation/miljoe.txt)
- [Lokal kørselsvejledning](dokumentation/KOERSEL.md)
- [Historisk slutkontrol af den oprindelige afleveringsmappe](dokumentation/slutkontrol.txt)
- [Fælles kørselsprogram](scripts/lab.py), [samtidige sessioner](scripts/session.py) og [TLS-kontrol fra værten](scripts/host_tls.py)

Brugerstier, identifikatorer for andre projekters containere og kontaktfelter i syntetiske kundedata er anonymiseret. Tidsmålinger, rækker, fejlbeskeder, SQLSTATE-koder og testudfald er bevaret. Den historiske slutkontrol beskriver den daværende PDF og dens lokale filhenvisninger.
