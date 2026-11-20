L.prepare()
L.start()
plan="EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM kunder WHERE status='inaktiv' AND aldersgruppe='30-40';"
stat="SELECT attname,n_distinct,most_common_vals,most_common_freqs FROM pg_stats WHERE tablename='kunder' AND attname IN ('status','aldersgruppe') ORDER BY attname;"
L.sql("SELECT status,count(*) FROM kunder GROUP BY status ORDER BY count(*) DESC;",expect=r'aktiv\|900000.*inaktiv\|100000')
L.sql("SELECT count(*) FROM pg_stats WHERE tablename='kunder';",expect='^0$')
def repeat():
    L.sql('\\timing on\n'+("SELECT count(*) FROM kunder WHERE status='inaktiv';\n"+plan+'\n')*3,expect='16667')
repeat()
L.sql('ANALYZE kunder;\n'+stat,expect='aktiv')
repeat()
L.sql('ALTER TABLE kunder ALTER COLUMN status SET STATISTICS 0;\nANALYZE kunder;\n'+stat+'\n'+plan)
L.sql("ALTER TABLE kunder ALTER COLUMN status SET STATISTICS 100;\nALTER TABLE kunder SET (autovacuum_enabled=on);\nANALYZE kunder;\n"+stat+"\nSELECT attstattarget,reloptions FROM pg_attribute JOIN pg_class ON attrelid=pg_class.oid WHERE attrelid='kunder'::regclass AND attname='status';",expect=r'100\|\{autovacuum_enabled=on\}')
