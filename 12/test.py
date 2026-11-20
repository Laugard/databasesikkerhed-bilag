L.prepare()
L.start()
L.exe('chown','postgres:postgres','/backup','/archive')
L.exe('chmod','700','/backup','/archive')
L.sql('SHOW wal_level;\nSHOW archive_mode;\nSHOW archive_command;\nCHECKPOINT;\nSELECT pg_switch_wal();',expect='replica.*on')
def archive(wal=None):
    for _ in range(40):
        r=L.sql("SELECT archived_count,last_archived_wal,failed_count FROM pg_stat_archiver;")
        if int(r.split('|')[0]) and (not wal or (L.tmp/'archive'/wal).is_file()):break
        time.sleep(.4)
    check(int(r.split('|')[0])>0 and (not wal or (L.tmp/'archive'/wal).is_file()),'Manglende WAL-segment')
    L.exe('ls','-lh','/archive')
archive()
fingerprint="SELECT count(*),md5(string_agg(row(id,tekst,oprettet)::text,',' ORDER BY id)) FROM vigtige_data;"
before=L.sql(fingerprint)
check(before.startswith('100|'),'Udgangspunkt')
L.exe('pg_dump','-U','studie','-Fc','-f','/backup/logisk.dump','studiebase')
L.sql("DROP TABLE vigtige_data;\nSELECT to_regclass('public.vigtige_data') IS NULL;",expect=r'\nt$')
L.exe('createdb','-U','studie','gendannelse')
L.exe('pg_restore','-U','studie','--exit-on-error','--no-owner','-d','gendannelse','/backup/logisk.dump')
check(L.sql(fingerprint,db='gendannelse')==before,'Logisk restore')
L.exe('pg_restore','-U','studie','--exit-on-error','--no-owner','-d','studiebase','/backup/logisk.dump')
L.sql('DROP DATABASE gendannelse;')
L.sql("INSERT INTO vigtige_data(tekst) VALUES('MARKØR før katastrofe');\nCHECKPOINT;\nSELECT clock_timestamp(),pg_current_wal_lsn();")
L.exe('pg_basebackup','-U','studie','-D','/backup/fysisk','-Ft','-z','-X','stream','-c','fast','-P',timeout=180)
L.exe('ls','-lh','/backup/fysisk','/backup/logisk.dump')
L.sql("UPDATE vigtige_data SET tekst='MARKØR efter basebackup' WHERE tekst='MARKØR før katastrofe';",expect='UPDATE 1')
target=L.sql('SELECT clock_timestamp();')
L.sql("SELECT pg_current_wal_lsn(),count(*),count(*) FILTER(WHERE tekst='MARKØR efter basebackup') FROM vigtige_data;",expect=r'\|101\|1')
L.sql("INSERT INTO vigtige_data(tekst) SELECT 'EFTER katastrofe '||i FROM generate_series(1,50) i;\nSELECT count(*) FROM vigtige_data;",expect=r'\n151$')
L.sql("DROP TABLE vigtige_data;\nCHECKPOINT;\nSELECT to_regclass('public.vigtige_data') IS NULL;",expect=r'\nt$')
wal=L.sql('SELECT pg_walfile_name(pg_current_wal_insert_lsn());')
L.sql('SELECT pg_switch_wal();')
archive(wal)
L.cfg['volumes']['recovery']={}
unpack="""set -eu
d=/var/lib/postgresql/18/docker
install -d -m 700 -o postgres -g postgres "$d"
tar xzf /backup/fysisk/base.tar.gz -C "$d"
install -d -m 700 "$d/pg_wal"
tar xzf /backup/fysisk/pg_wal.tar.gz -C "$d/pg_wal"
touch "$d/recovery.signal"
chown -R postgres:postgres "$d"
exec docker-entrypoint.sh postgres -c archive_mode=off -c "restore_command=cp /archive/%f %p" -c "recovery_target_time=$1" -c recovery_target_action=promote"""
L.cfg['services']['gendannet']={'image':'postgres:18','mem_limit':'768m','cpus':1,'volumes':['recovery:/var/lib/postgresql','./backup:/backup:ro','./archive:/archive:ro'],
                              'entrypoint':['bash','-ec',unpack,'gendan',target]}
# Compose fortolker selv dollarsymboler. Escap shellvariabler til den indre bash.
L.cfg['services']['gendannet']['entrypoint'][2]=unpack.replace('$','$$')
L.start()
cid=L.run(L.compose+['ps','-q','gendannet'])
L.wait(cid,'studie','studiebase')
for _ in range(30):
    if L.sql('SELECT pg_is_in_recovery();',cid=cid)=='f':break
    time.sleep(.4)
L.sql("SELECT count(*),count(*) FILTER(WHERE tekst LIKE 'EFTER%'),count(*) FILTER(WHERE tekst='MARKØR efter basebackup'),pg_is_in_recovery() FROM vigtige_data;",cid=cid,expect=r'^101\|0\|1\|f$')
out=L.run(['docker','logs','--timestamps',cid])
check('recovery stopping before commit' in out and 'archive recovery complete' in out,'WAL replay og promotion')
