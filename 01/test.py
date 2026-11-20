L.prepare()
L.start()
L.exe('pgbench','-U','studie','-i','-s','30','studiebase',timeout=180)
L.sql("SELECT count(*),pg_size_pretty(pg_total_relation_size('pgbench_accounts')) FROM pgbench_accounts;",expect=r'3000000\|')
settings='SHOW shared_buffers;\nSHOW work_mem;\nSHOW effective_cache_size;\nSHOW maintenance_work_mem;'
order='EXPLAIN (ANALYZE, BUFFERS) SELECT aid, abalance FROM pgbench_accounts ORDER BY abalance DESC'
def bench():
    out=L.exe('pgbench','-U','studie','-c','4','-T','30','studiebase')
    check('number of failed transactions: 0' in out,'Fejlede transaktioner')
    return float(re.search(r'tps = ([\d.]+)',out)[1])
L.sql(settings)
before=bench()
L.sql(order+';',expect='external merge')
L.setconf(['shared_buffers=512MB','work_mem=64MB','effective_cache_size=2GB','maintenance_work_mem=256MB'])
L.start()
L.sql(settings,expect='512MB.*64MB.*2GB.*256MB')
after=bench()
L.note(f'TPS-ændring {(after/before-1)*100:.2f} %')
L.sql(order+';')
L.sql(order+' LIMIT 10;',expect='top-N heapsort')
# Separat midlertidig datamappe og hårdt loft på virtuelt adresserum.
L.run(['docker','exec','-u','postgres',L.cid,'bash','-ec',
       'd=$(mktemp -d); initdb -D "$d" --no-sync >/dev/null; ulimit -v 393216; exec postgres -D "$d" -c shared_buffers=8GB -c huge_pages=off -c port=5544'],
      fail=r'could not map anonymous shared memory|Cannot allocate memory')
L.sql("SELECT current_setting('shared_buffers'), count(*) FROM pgbench_accounts;",expect=r'512MB\|3000000')
