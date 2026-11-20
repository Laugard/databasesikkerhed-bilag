from session import Session
L.prepare()
L.start()
L.sql('SELECT count(*) FROM store_data;',expect='^500000$')
L.sql("""CREATE VIEW aktivitet_overvaagning AS SELECT pid,usename,application_name,client_addr,state,
 clock_timestamp()-query_start AS varighed,clock_timestamp()-state_change AS tilstandsvarighed,
 query,backend_start,xact_start,backend_type FROM pg_stat_activity WHERE state<>'idle';""")
slow=Session(L,'lab_lang')
idle=Session(L,'lab_inaktiv')
s_pid=int(slow.q('SELECT pg_backend_pid();'))
i_pid=int(idle.q('SELECT pg_backend_pid();'))
slow.send('SELECT pg_sleep(60);')
idle.q('BEGIN;\nSELECT id FROM store_data WHERE id=1 FOR UPDATE;')
time.sleep(5.3)
L.sql("SELECT pid,usename,application_name,client_addr,state,varighed,query,xact_start FROM aktivitet_overvaagning WHERE application_name IN ('lab_lang','lab_inaktiv') ORDER BY 3;",expect='idle in transaction.*active')
L.sql("SELECT pid,query FROM aktivitet_overvaagning WHERE application_name='lab_lang' AND varighed>interval '5 seconds';",expect='pg_sleep')
L.sql(f"SELECT pg_cancel_backend(pid) FROM pg_stat_activity WHERE pid={s_pid} AND application_name='lab_lang' AND datname=current_database();",expect='^t$')
check('57014' in slow.read(expected_error=True) and slow.close()!=0,'Annullering')
L.sql(f"SELECT locktype,mode,granted FROM pg_locks WHERE pid={i_pid};",expect='RowShareLock')
L.sql(f"SELECT pg_terminate_backend(pid,3000) FROM pg_stat_activity WHERE pid={i_pid} AND application_name='lab_inaktiv' AND state='idle in transaction';",expect='^t$')
# psql konstaterer den lukkede forbindelse ved næste forespørgsel.
idle.send('SELECT 1;')
check('57P01' in idle.read(expected_error=True) and idle.close()!=0,'Afsluttet session')
L.sql(f"SELECT count(*) FROM pg_stat_activity WHERE pid IN ({i_pid},{s_pid});",expect='^0$')
a=Session(L,'lab_holder')
b=Session(L,'lab_venter')
for query in ('SELECT id FROM store_data WHERE id=1 FOR UPDATE;', 'UPDATE store_data SET numero=numero+2 WHERE id=1;'):
    a.q('BEGIN;\n'+('SELECT id FROM store_data WHERE id=1 FOR UPDATE;' if query.startswith('SELECT') else 'UPDATE store_data SET numero=numero+1 WHERE id=1;'))
    b.send(query)
    for _ in range(30):
        blockers=L.sql("""SELECT a.pid,b.pid,a.wait_event_type,a.query,b.state FROM pg_stat_activity a
 JOIN pg_stat_activity b ON b.pid=ANY(pg_blocking_pids(a.pid))
 WHERE a.application_name='lab_venter' AND b.application_name='lab_holder';""")
        if '|Lock|' in blockers:break
        time.sleep(.1)
    check('|Lock|' in blockers,'Låsekonflikt')
    a.q('ROLLBACK;')
    check(b.read() in ['1','UPDATE 1'],'Låsen blev frigivet')
check(a.close()==0 and b.close()==0,'Afslutning')
L.sql("SELECT numero FROM store_data WHERE id=1;",expect='^3$')
