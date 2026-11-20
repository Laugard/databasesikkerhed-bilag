L.prepare()
L.start()
L.sql("SHOW log_destination;\nSHOW log_statement;\nSHOW log_min_duration_statement;\nSHOW log_connections;\nSELECT name,setting FROM pg_settings WHERE name LIKE 'log%' ORDER BY name;")
L.sql("""SET log_statement='all';
SELECT * FROM konto_log /* hele_tabellen */;
SELECT * FROM konto_log WHERE beloeb>1000 /* kun_store */;
SET log_statement='none';
SET log_min_duration_statement=0;
SELECT pg_sleep(0.05) /* maal_alle */;
SET log_min_duration_statement=500;
SELECT 42 /* hurtig_usynlig */;
SELECT pg_sleep(0.55) /* overskrider_500 */;""")
L.sql("SET log_statement='all';\nSELECT 1/0 /* nulfejl */;",fail='22012.*division by zero')
L.sql('SELECT 1;',expect='^1$')
out=L.run(['docker','logs','--timestamps',L.cid])
for pattern in ['statement: SELECT .*hele_tabellen','statement: SELECT .*kun_store','duration: .*maal_alle','duration: .*overskrider_500','division by zero','nulfejl','connection authorized']:
    check(re.search(pattern,out),pattern)
check('hurtig_usynlig' not in out,'Hurtig query blev logget')
L.note('Logkontrol: to SELECT, to varigheder, fejl og forbindelse fundet. Markør hurtig_usynlig forekommer 0 gange i serverloggen.')
