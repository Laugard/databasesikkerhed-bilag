L.prepare()
L.start()
L.sql("SELECT navn,pris FROM produkter ORDER BY id;\nSELECT count(*) FROM audit_log;",expect=r'Bog\|199.00.*\n0$')
L.sql("""CREATE FUNCTION log_aendring() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 INSERT INTO audit_log(tabel,handling,detaljer) VALUES(TG_TABLE_NAME,TG_OP,
    format('id=%s bruger=%s',coalesce(NEW.id,OLD.id),session_user));
 RETURN NULL;
END $$;
CREATE TRIGGER produkter_audit AFTER INSERT OR UPDATE OR DELETE ON produkter FOR EACH ROW EXECUTE FUNCTION log_aendring();
UPDATE produkter SET pris=249 WHERE navn='Bog';
INSERT INTO produkter(navn,pris) VALUES('Kalender',89);
DELETE FROM produkter WHERE navn='Pen';
SELECT handling,detaljer,tid FROM audit_log ORDER BY id;
CREATE FUNCTION tjek_pris() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.pris<0 THEN RAISE EXCEPTION 'Negativ pris' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER produkter_tjek_pris BEFORE INSERT OR UPDATE ON produkter FOR EACH ROW EXECUTE FUNCTION tjek_pris();
SELECT tgname,tgtype,tgenabled FROM pg_trigger WHERE NOT tgisinternal;""",expect=r'UPDATE\|id=1.*INSERT\|id=4.*DELETE\|id=3')
for q in ["UPDATE produkter SET pris=-5 WHERE navn='Bog';","INSERT INTO produkter(navn,pris) VALUES('Ugyldig',-2);"]:
    L.sql(q,fail='23514.*Negativ pris')
L.sql("""SELECT pris,(SELECT count(*) FROM audit_log),(SELECT count(*) FROM produkter WHERE navn='Ugyldig') FROM produkter WHERE navn='Bog';
ALTER TABLE produkter DISABLE TRIGGER produkter_audit;
UPDATE produkter SET pris=1 WHERE navn='Bog';
SELECT pris,(SELECT count(*) FROM audit_log) FROM produkter WHERE navn='Bog';
ALTER TABLE produkter ENABLE TRIGGER produkter_audit;
UPDATE produkter SET pris=2 WHERE navn='Bog';
SELECT pris,(SELECT count(*) FROM audit_log) FROM produkter WHERE navn='Bog';""",expect=r'249.00\|3\|0.*1.00\|3.*2.00\|4')
