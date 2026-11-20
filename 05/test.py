L.prepare()
L.start()
L.sql("""\d ordrer_denormaliseret
SELECT * FROM ordrer_denormaliseret LIMIT 10;
SELECT count(DISTINCT kunde_info),count(*) FROM ordrer_denormaliseret;
SELECT runde_id,count(*) FROM ordrer_denormaliseret GROUP BY 1 HAVING count(*)>1 ORDER BY 1 LIMIT 5;
SELECT count(*) FROM (SELECT runde_id FROM ordrer_denormaliseret GROUP BY 1 HAVING count(DISTINCT (runde_navn,runde_dato,runde_status))>1) x;
SELECT count(*) FILTER (WHERE forventet_levering<ordre_dato::date),count(*) FILTER (WHERE forventet_levering>CURRENT_DATE) FROM ordrer_denormaliseret;""")
L.sql((A/'loesninger/05/migrering.sql').read_text(),expect=r'\|100\|500\|100000\|100000\n0$')
L.sql('INSERT INTO ordre_linjer(ordre_id,produkt_id,antal,pris) VALUES(-1,1,1,5);',fail='23503')
L.sql("""BEGIN;
ALTER TABLE ordrer ADD COLUMN kunde_navn text;
UPDATE ordrer o SET kunde_navn=k.navn FROM kunder k WHERE o.kunde_id=k.kunde_id;
ALTER TABLE ordrer ALTER COLUMN kunde_navn SET NOT NULL;
CREATE FUNCTION hent_navn() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 SELECT navn INTO STRICT NEW.kunde_navn FROM kunder WHERE kunde_id=NEW.kunde_id FOR SHARE;
 RETURN NEW;
END $$;
CREATE TRIGGER ordre_navn BEFORE INSERT OR UPDATE OF kunde_id,kunde_navn ON ordrer FOR EACH ROW EXECUTE FUNCTION hent_navn();
CREATE INDEX ordre_kunde_idx ON ordrer(kunde_id);
CREATE FUNCTION udbred_navn() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 UPDATE ordrer SET kunde_navn=NEW.navn WHERE kunde_id=NEW.kunde_id;
 RETURN NEW;
END $$;
CREATE TRIGGER kunde_navn AFTER UPDATE OF navn ON kunder FOR EACH ROW WHEN (OLD.navn IS DISTINCT FROM NEW.navn) EXECUTE FUNCTION udbred_navn();
COMMIT;
VACUUM ANALYZE ordrer;
ANALYZE kunder;
BEGIN;
UPDATE kunder SET navn='Omdøbt' WHERE kunde_id=1;
INSERT INTO ordrer(ordre_id,runde_id,kunde_id) VALUES(-1,1,1);
SELECT kunde_navn FROM ordrer WHERE ordre_id=-1;
UPDATE ordrer SET kunde_id=2 WHERE ordre_id=-1;
SELECT kunde_navn FROM ordrer WHERE ordre_id=-1;
SELECT count(*) AS uens FROM ordrer o JOIN kunder k USING(kunde_id) WHERE o.kunde_navn<>k.navn;
ROLLBACK;""",expect=r'Omdøbt.*Kunde 2\n0\nROLLBACK')
p='EXPLAIN (ANALYZE,BUFFERS) '
a=p+'SELECT o.ordre_id,o.beloeb,k.navn FROM ordrer o JOIN kunder k USING(kunde_id) WHERE runde_id=5;'
b=p+'SELECT ordre_id,beloeb,kunde_navn FROM ordrer WHERE runde_id=5;'
L.sql('\n'.join([a,b,b,a]))
