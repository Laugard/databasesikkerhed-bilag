L.prepare()
L.start()
L.sql('SELECT count(*) FROM ordrer;',expect='^1000000$')
p='EXPLAIN (ANALYZE, BUFFERS) '
q="SELECT * FROM ordrer WHERE kunde_id=5000 AND status='afsluttet';"
single='CREATE INDEX idx_ordrer_kunde ON ordrer(kunde_id);'
double='CREATE INDEX idx_ordrer_kunde_status ON ordrer(kunde_id,status);'
for ddl,pattern in [('', 'Seq Scan'),(single,'idx_ordrer_kunde'),(double,'idx_ordrer_kunde_status')]:
    L.sql(ddl+'\n\\timing on\n'+q+'\n'+p+q,expect=pattern)
def writes():
    # Begge serier bruger de samme værdier og samme primærnøgler. ROLLBACK fjerner alle nye rækker.
    L.sql("""BEGIN;
EXPLAIN (ANALYZE,BUFFERS,WAL) INSERT INTO ordrer(id,kunde_id,status,beloeb,ordre_dato)
SELECT 1000000+i,1+(i%10000),'pendende',i/10.0,DATE '2026-01-01' FROM generate_series(1,10000) i;
EXPLAIN (ANALYZE,BUFFERS,WAL) UPDATE ordrer SET status='afsluttet' WHERE id BETWEEN 1000001 AND 1010000;
SELECT count(*) FROM ordrer WHERE id>1000000 AND status='afsluttet';
ROLLBACK;""",expect=r'^10000$')
L.sql('DROP INDEX idx_ordrer_kunde,idx_ordrer_kunde_status;')
writes()
L.sql('VACUUM (ANALYZE) ordrer;\n'+single+'\n'+double)
writes()
L.sql(p+'SELECT * FROM ordrer WHERE kunde_id=100;\n'+p+"SELECT * FROM ordrer WHERE status='afsluttet';\n"+p+q)
L.sql("SELECT indexrelname,idx_scan,idx_tup_read,idx_tup_fetch FROM pg_stat_user_indexes WHERE relname='ordrer' ORDER BY indexrelname;")
L.sql('VACUUM ordrer;\nSELECT count(*),count(*) FILTER (WHERE id>1000000) FROM ordrer;',expect=r'1000000\|0')
