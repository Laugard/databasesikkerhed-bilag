"""Kontrollér PostgreSQL fra Mac'ens loopback med libpq via psycopg."""
import os, sys, psycopg
port,cert,mode,hostname=sys.argv[1:]
try:
    with psycopg.connect(host=hostname,hostaddr='127.0.0.1',port=port,dbname='appdb',user='admin',
                         sslmode=mode,sslrootcert=cert,connect_timeout=4) as conn:
        print(*conn.execute('SELECT ssl,version,inet_client_addr() FROM pg_stat_ssl WHERE pid=pg_backend_pid()').fetchone(),sep='|')
except psycopg.Error as e:
    print(str(e))
    sys.exit(2)
