L.prepare()
L.start()
L.sql('SELECT (SELECT count(*) FROM forfattere),(SELECT count(*) FROM boeger),(SELECT count(*) FROM laan);',expect=r'^10000\|100000\|1000000$')
p='EXPLAIN (ANALYZE, BUFFERS) '
L.sql(p+"SELECT * FROM laan WHERE extract(year FROM laan_dato)=2023;",expect='Seq Scan')
nested=p+'SELECT f.navn,b.titel FROM forfattere f JOIN boeger b ON b.forfatter_id=f.id WHERE f.id<=100;'
out=L.sql(nested)
if 'Nested Loop' not in out:
    L.sql('BEGIN;\nSET LOCAL enable_hashjoin=off;\nSET LOCAL enable_mergejoin=off;\n'+nested+'\nROLLBACK;',expect='Nested Loop')
h=p+"SELECT count(*) FROM laan l JOIN boeger b ON b.id=l.bog_id WHERE l.laan_dato>'2023-01-01';"
L.sql(h,expect='Hash Join')
L.sql("BEGIN;\nSET LOCAL work_mem='64kB';\n"+p+'SELECT * FROM laan ORDER BY laaner_id,bog_id;\nROLLBACK;',expect='external merge')
L.sql("BEGIN;\nSET LOCAL work_mem='64kB';\nSET LOCAL enable_hashjoin=off;\nSET LOCAL enable_nestloop=off;\n"+p+'SELECT f.navn,b.titel FROM forfattere f JOIN boeger b ON b.forfatter_id=f.id;\nROLLBACK;\nSHOW enable_hashjoin;\nSHOW enable_nestloop;\nSHOW work_mem;',expect='Merge Join.*on\non\n4MB')
L.sql(h,expect='Buffers: shared')
