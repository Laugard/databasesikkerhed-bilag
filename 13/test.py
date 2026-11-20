import copy, ipaddress, shutil
root=L.tmp
(root/'secrets').mkdir()
app_pw=L.new_secret('secrets/app_password.txt')
# Setup bevarer den genererede app-hemmelighed og genererer admin-kode og certifikat.
L.run(['bash',str(L.src/'scripts/setup.sh')])
admin=(root/'secrets/db_password.txt').read_text().strip()
L.secret.append(admin)
L.run(['openssl','x509','-in','certs/server.crt','-noout','-subject','-issuer','-dates','-ext','subjectAltName'])
L.run(['openssl','verify','-CAfile','certs/server.crt','certs/server.crt'])
ignored=L.run(['git','-C',str(L.src),'check-ignore','certs/server.key','secrets/db_password.txt','secrets/app_password.txt'])
check(len(ignored.splitlines())==3,'Git ignore')
nets=json.loads(L.run(['docker','network','inspect',*sp.check_output(['docker','network','ls','-q'],text=True).split()],show=False))
occupied=[ipaddress.ip_network(c['Subnet']) for n in nets for c in n['IPAM'].get('Config') or [] if 'Subnet' in c]
ranges=[ipaddress.ip_network(f'172.{i}.0.0/24') for i in [28,29,26,27,24,25,23,22,21,20]]
appnet,other=[r for r in ranges if all(not r.overlaps(o) for o in occupied if o.version==4)][:2]
apple,remote=str(appnet[10]),str(other[10])
def save(name,contents):
    (root/name).write_text(contents)
    (root/name).chmod(0o644)
def hba(extra=''):
    return f"""local all admin peer map=lokaladmin
local all all peer
hostssl appdb app_user,test_user {appnet} scram-sha-256
hostssl appdb admin {appnet} scram-sha-256
{extra}
host all all 0.0.0.0/0 reject
host all all ::/0 reject
"""
save('hba.conf',hba())
save('ident.conf','lokaladmin postgres admin\nlokaladmin root admin\n')
seed=(L.src/'scripts/init.sql').read_text()
seed=re.sub(r"LOGIN PASSWORD '[^']+'",'LOGIN',seed)
seed=seed.replace('ALTER TABLE app_data OWNER TO app_user;','-- admin ejer tabellen')
save('main.sql',seed)
volumes=['main:/var/lib/postgresql','./main.sql:/docker-entrypoint-initdb.d/01.sql:ro','./certs:/bootstrap-certs:ro',
         './hba.conf:/etc/postgresql/pg_hba.conf:ro','./ident.conf:/etc/postgresql/pg_ident.conf:ro']
entry="""set -eu
install -d -o postgres -g postgres -m 0700 /run/labtls
install -o postgres -g postgres -m 0600 /bootstrap-certs/server.key /run/labtls/server.key
install -o postgres -g postgres -m 0644 /bootstrap-certs/server.crt /run/labtls/server.crt
exec docker-entrypoint.sh "$@" """
opts=['ssl=on','ssl_cert_file=/run/labtls/server.crt','ssl_key_file=/run/labtls/server.key',
      'hba_file=/etc/postgresql/pg_hba.conf','ident_file=/etc/postgresql/pg_ident.conf','listen_addresses=*',
      'password_encryption=scram-sha-256','log_connections=on','log_disconnections=on','log_statement=ddl']
def command(settings):
    return ['postgres']+[x for opt in settings for x in ['-c',opt]]
db={'image':'postgres:18','mem_limit':'512m','cpus':1,'environment':{'POSTGRES_USER':'admin','POSTGRES_DB':'appdb','POSTGRES_PASSWORD_FILE':'/run/secrets/dbpass'},
    'secrets':['dbpass'],'volumes':volumes,'entrypoint':['bash','-ec',entry.replace('$','$$'),'start'],
    'command':command(opts),'ports':['127.0.0.1::5432'],'networks':{'appnet':{'ipv4_address':apple},'andet':{'ipv4_address':remote}}}
def client(net,ip):
    return {'image':'postgres:18','mem_limit':'128m','cpus':.5,'command':['sleep','infinity'],'networks':{net:{'ipv4_address':str(ip)}}}
app=client('appnet',appnet[20])
app['secrets']=['apppass']
app['volumes']=['./certs/server.crt:/ca.crt:ro']
otherclient=client('andet',other[20])
L.cfg={'services':{'db':db,'app':app,'anden':otherclient},'volumes':{'main':{}},
       'secrets':{'dbpass':{'file':'./secrets/db_password.txt'},'apppass':{'file':'./secrets/app_password.txt'}},
       'networks':{'appnet':{'ipam':{'config':[{'subnet':str(appnet)}]}},'andet':{'internal':True,'ipam':{'config':[{'subnet':str(other)}]}}}}
L.start('db')
def setpw(role,pw,cid=None):
    L.sql("SET log_statement='none';\nSET log_min_duration_statement=-1;\nALTER ROLE "+role+" PASSWORD '"+pw+"';",cid=cid)
setpw('app_user',app_pw)
L.sql("SHOW listen_addresses;\nSHOW hba_file;\nSHOW data_directory;\nSHOW password_encryption;\nSHOW ssl;\nSELECT rolname,rolcanlogin FROM pg_roles ORDER BY 1;\nSELECT rule_number,type,database,user_name,address,auth_method,error FROM pg_hba_file_rules ORDER BY rule_number;")
testpw=L.new_secret('trial.pass')
L.sql('CREATE ROLE test_user LOGIN;')
setpw('test_user',testpw)
L.sql("SELECT rolname,rolpassword LIKE 'SCRAM-SHA-256$%' FROM pg_authid WHERE rolname IN ('test_user','app_user') ORDER BY 1;",expect=r'app_user\|t\ntest_user\|t')
def connect(service,addr,pw,*,user='app_user',mode='require',query='SELECT 1;',fail=None,hostname=None):
    params=f'hostaddr={addr} host={hostname or addr} dbname=appdb user={user} sslmode={mode} connect_timeout=4'
    if mode=='verify-full':params+=' sslrootcert=/ca.crt'
    return L.run(L.compose+['exec','-T','-e','PGPASSWORD',service,'psql','-XAtw','-v','ON_ERROR_STOP=1','-v','VERBOSITY=verbose',params,'-c',query],env={'PGPASSWORD':pw},fail=fail)
wrong=L.new_secret('invalid.pass')
def matrix(a,b,pw):
    out=connect('app',a,pw,query='SELECT count(*) FROM app_data;')
    check(out in ['10','20'],'Tilladt læsning')
    connect('anden',b,pw,fail=r'pg_hba.conf rejects connection.*'+str(other[20]))
    connect('app',a,wrong,fail='password authentication failed')
    connect('app',a,pw,mode='disable',fail='pg_hba.conf rejects connection.*no encryption')
matrix(apple,remote,app_pw)
check(connect('app',apple,testpw,user='test_user')=='1','Testbruger')
connect('app',apple,wrong,user='test_user',fail='password authentication failed')
check(connect('app',apple,app_pw,mode='verify-full',hostname='oevelse13-db',query="SELECT ssl,version FROM pg_stat_ssl WHERE pid=pg_backend_pid();").startswith('t|TLS'),'Fuld validering')
connect('app',apple,app_pw,mode='verify-full',hostname='ukendt.invalid',fail='does not match host name')
def hosttest(mode,hostname,fail=None):
    port=L.run(L.compose+['port','db','5432']).rsplit(':',1)[1]
    py=ROOT/'kontrol/hostclient/bin/python'
    return L.run([str(py),str(A/'scripts/host_tls.py'),port,str(root/'certs/server.crt'),mode,hostname],env={'PGPASSWORD':admin},fail=fail)
# Docker Desktop kan source-NAT'e værtens loopback til en anden gateway.
# Kun den observerede peer for vores egen loopbackforbindelse føjes til som /32.
try:
    res=hosttest('require','localhost')
except AssertionError:
    recent=L.log.read_text().rsplit('host_tls.py',1)[-1]
    m=re.search(r'pg_hba.conf rejects connection for host "([0-9.]+)"',recent)
    if not m:raise
    gateway=ipaddress.IPv4Address(m[1])
    check(gateway.is_private and gateway not in other,'Uventet gateway')
    save('hba.conf',hba(f'hostssl appdb admin {gateway}/32 scram-sha-256'))
    L.sql('SELECT pg_reload_conf();')
    res=hosttest('require','localhost')
check('True|TLS' in res,'TLS fra vært')
check('True|TLS' in hosttest('verify-full','localhost'),'Certifikat fra vært')
hosttest('verify-full','forkert.invalid',fail='does not match host name')
digest="SELECT count(*),md5(string_agg(id||':'||note,',' ORDER BY id)) FROM app_data;"
before=connect('app',apple,app_pw,query=digest)
new=L.new_secret('rotation.pass')
setpw('app_user',new)
(root/'secrets/app_password.txt').write_text(new+'\n')
matrix(apple,remote,new)
connect('app',apple,app_pw,fail='password authentication failed')
check(connect('app',apple,new,query=digest)==before,'Rotation og data')
out=L.run(L.compose+['exec','-T','app','sh','-ec','export PGPASSWORD="$(cat /run/secrets/apppass)"; exec psql -XAtw -h '+apple+' -U app_user -d "dbname=appdb sslmode=require" -c "SELECT count(*) FROM app_data"'])
check(out=='20','Klientens monterede secret')
# Selvstændig challenge. Før-billedet startes kun med socket og uden netværk eller publiceret port.
save('challenge-seed.sql',re.sub(r"LOGIN PASSWORD '[^']+'",'LOGIN',(L.src/'challenge/init.sql').read_text()))
save('challenge-hba.conf',(L.src/'challenge/pg_hba.conf').read_text())
ch=copy.deepcopy(db)
ch.pop('ports')
ch.pop('networks')
ch['network_mode']='none'
ch['volumes']=['chdata:/var/lib/postgresql','./challenge-seed.sql:/docker-entrypoint-initdb.d/01.sql:ro','./challenge-hba.conf:/etc/postgresql/pg_hba.conf:ro']
ch.pop('entrypoint')
ch['command']=command(['ssl=off','log_connections=off','log_statement=none','hba_file=/etc/postgresql/pg_hba.conf'])
L.cfg['volumes']['chdata']={}
L.cfg['services']['challenge']=ch
L.start('db')
def challenge_id():
    cid=L.run(L.compose+['ps','-q','challenge'])
    L.wait(cid,'admin','appdb')
    return cid
chcid=challenge_id()
L.sql("SHOW ssl;\nSHOW log_connections;\nSELECT rolname,rolsuper FROM pg_roles WHERE rolname='app_user';\nSELECT type,address,auth_method FROM pg_hba_file_rules;\nSELECT count(*) FROM app_data;",cid=chcid,expect=r'app_user\|t.*trust.*10$')
chpw=L.new_secret('challenge.pass')
setpw('app_user',chpw,chcid)
fix=(A/'loesninger/13/rettigheder.sql').read_text()
L.sql(fix,cid=chcid)
save('challenge-hba.conf',hba().replace('app_user,test_user','app_user'))
ch.pop('network_mode')
ch['networks']={'appnet':{'ipv4_address':str(appnet[11])},'andet':{'ipv4_address':str(other[11])}}
ch['ports']=['127.0.0.1::5432']
ch['volumes']+=['./certs:/bootstrap-certs:ro','./ident.conf:/etc/postgresql/pg_ident.conf:ro']
ch['entrypoint']=db['entrypoint']
ch['command']=command(opts)
L.start('db')
chcid=challenge_id()
L.sql("SHOW ssl;\nSHOW log_connections;\nSHOW log_statement;\nSELECT rolname,rolsuper,rolbypassrls FROM pg_roles WHERE rolname='app_user';\nSELECT count(*) FROM app_data;\nSELECT type,address,auth_method FROM pg_hba_file_rules;",cid=chcid,expect=r'app_user\|f\|f.*10')
ca,cb=str(appnet[11]),str(other[11])
matrix(ca,cb,chpw)
connect('app',ca,chpw,query='SELECT count(*) FROM sensitive_data;',fail='42501.*permission denied')
connect('app',ca,chpw,query='DELETE FROM app_data WHERE id=1;',fail='42501.*permission denied')
check('UPDATE 1' in connect('app',ca,chpw,query="BEGIN; INSERT INTO app_data(note) VALUES ('lab'); UPDATE app_data SET note='rettet' WHERE id=1; ROLLBACK;"),'Begrænsede skriverettigheder')
check(connect('app',ca,chpw,query='SELECT count(*) FROM app_data;')=='10','Challenge beholdt rækker')
out=L.run(['docker','logs','--timestamps',chcid])
check('connection authorized' in out and 'permission denied for table sensitive_data' in out,'Challenge logning')
L.note('Challenge: kildekonfigurationens globale portbinding og faste koder blev kun inspiceret. Rollen, HBA, TLS og logging blev målt før og efter på samme datavolumen.')
