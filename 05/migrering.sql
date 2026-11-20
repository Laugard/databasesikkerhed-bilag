BEGIN;
CREATE TABLE kunder (kunde_id int PRIMARY KEY, navn text NOT NULL, email text NOT NULL, telefon text NOT NULL);
CREATE TABLE runder (runde_id int PRIMARY KEY, navn text NOT NULL, dato date NOT NULL, status text NOT NULL);
CREATE TABLE produkter (produkt_id int PRIMARY KEY, navn text NOT NULL);
CREATE TABLE ordrer (ordre_id int PRIMARY KEY, runde_id int NOT NULL REFERENCES runder, kunde_id int NOT NULL REFERENCES kunder,
    beloeb numeric(10,2), ordre_dato timestamp, status text, forventet_levering date);
CREATE TABLE ordre_linjer (linje_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, ordre_id int NOT NULL REFERENCES ordrer,
    produkt_id int NOT NULL REFERENCES produkter, antal int NOT NULL, pris numeric(10,2) NOT NULL);
INSERT INTO kunder SELECT DISTINCT kunde_id,kunde_info->>'navn',kunde_info->>'email',kunde_info->>'telefon' FROM ordrer_denormaliseret;
INSERT INTO runder SELECT DISTINCT runde_id,runde_navn,runde_dato,runde_status FROM ordrer_denormaliseret;
INSERT INTO produkter SELECT DISTINCT produkt_id,produkt_navn FROM ordrer_denormaliseret;
INSERT INTO ordrer SELECT ordre_id,runde_id,kunde_id,beloeb,ordre_dato,status,forventet_levering FROM ordrer_denormaliseret;
INSERT INTO ordre_linjer(ordre_id,produkt_id,antal,pris) SELECT ordre_id,produkt_id,antal,enhedspris FROM ordrer_denormaliseret;
COMMIT;
CREATE VIEW rekonstrueret AS
SELECT o.ordre_id,k.kunde_id,jsonb_build_object('navn',k.navn,'email',k.email,'telefon',k.telefon) AS kunde_info,
 r.runde_id,r.navn AS runde_navn,r.dato AS runde_dato,r.status AS runde_status,o.beloeb,o.ordre_dato,o.status,
 p.produkt_id,p.navn AS produkt_navn,l.antal,l.pris AS enhedspris,o.forventet_levering
FROM ordrer o JOIN kunder k USING(kunde_id) JOIN runder r USING(runde_id)
JOIN ordre_linjer l USING(ordre_id) JOIN produkter p USING(produkt_id);
SELECT (SELECT count(*) FROM kunder),(SELECT count(*) FROM runder),(SELECT count(*) FROM produkter),
 (SELECT count(*) FROM ordrer),(SELECT count(*) FROM ordre_linjer);
SELECT count(*) AS afvigelser FROM (
 (TABLE rekonstrueret EXCEPT ALL TABLE ordrer_denormaliseret)
 UNION ALL (TABLE ordrer_denormaliseret EXCEPT ALL TABLE rekonstrueret)) diff;
