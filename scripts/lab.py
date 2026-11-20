"""Lokal øvelseskørsel. Python 3, Docker Compose og underviserens kildekopi."""
import sys
sys.dont_write_bytecode = True
import argparse, datetime, json, os, re, secrets, shlex, shutil, subprocess as sp, tempfile, time, traceback
from pathlib import Path
from zoneinfo import ZoneInfo

A = Path(__file__).resolve().parents[1]
ROOT = A.parent
SRC = ROOT / 'kilde' / 'oevelser'
def now():
    return datetime.datetime.now(ZoneInfo('Europe/Copenhagen')).isoformat(timespec='seconds')
def check(ok, message):
    if not ok:
        raise AssertionError(message)
class Lab:
    def __init__(self, n, dest):
        self.n=n
        self.src=next(SRC.glob(n+'-*'))
        self.tmp=Path(tempfile.mkdtemp(prefix='dbsec'+n+'-',dir=ROOT/'kontrol'))
        self.project=self.tmp.name
        self.file=self.tmp/'compose.json'
        self.compose=['docker','compose','-p',self.project,'-f',str(self.file)]
        self.ev=dest/n
        self.ev.mkdir(parents=True,exist_ok=True)
        self.log=self.ev/(self.project+'.txt')
        self.secret=[]
        self.cfg={}
        self.owned=False
    def note(self,s):
        for v in self.secret:
            if v: s=s.replace(v,'[udeladt]')
        with self.log.open('a') as f: f.write(str(s)+'\n')
    def run(self,args,*,data=None,label=None,fail=None,timeout=120,env=None,show=True):
        self.note('\n'+now()+'  $ '+(label or shlex.join(map(str,args))))
        r=sp.run(args,input=data,stdout=sp.PIPE,stderr=sp.STDOUT,text=True,timeout=timeout,
                 env={**os.environ,**(env or {})},cwd=self.tmp)
        if show: self.note(r.stdout.rstrip())
        self.note('exit '+str(r.returncode))
        if fail:
            check(r.returncode != 0 and re.search(fail,r.stdout,re.I|re.S),'Afvisning matchede ikke '+fail)
            self.note('Bekræftet forventet afvisning / '+fail)
        else: check(r.returncode==0,'Kommando fejlede: '+(label or args[0]))
        return r.stdout.strip()
    def new_secret(self, name):
        value=secrets.token_hex(24)
        self.secret.append(value)
        p=self.tmp/name
        p.write_text(value+'\n')
        p.chmod(0o600)
        return value
    def prepare(self):
        pw=self.new_secret('db.pass')
        seed=(self.src/'scripts/init.sql').read_text()
        if self.n=='08':
            seed=re.sub(r" LOGIN PASSWORD '[^']*'",' LOGIN',seed)
        if self.n=='11':
            # Erstat undervisningens offentlige nøgle, testkoder og CPR-form med engangsværdier.
            self.key=self.new_secret('crypto.key')
            self.sample=self.new_secret('sample')
            self.userpw=self.new_secret('user.pass')
            seed=re.sub(r"pgp_sym_encrypt\(.*\),",f"pgp_sym_encrypt('{self.sample}' || i, '{self.key}'),",seed)
            seed=re.sub(r"\bcrypt\('[^']+' \|\| i",f"crypt('{self.userpw}' || i",seed)
        (self.tmp/'seed.sql').write_text(seed)
        (self.tmp/'seed.sql').chmod(0o644)
        conf=['shared_buffers=128MB','work_mem=4MB','effective_cache_size=512MB']
        if self.n=='01':conf=['shared_buffers=16MB','work_mem=64kB','effective_cache_size=32MB','maintenance_work_mem=16MB']
        if self.n=='07':conf+=['log_connections=on','log_statement=none','log_min_duration_statement=500']
        pg={'image':'postgres:18','mem_limit':'1536m','memswap_limit':'1536m','cpus':2,'shm_size':'192m',
            'environment':{'POSTGRES_PASSWORD_FILE':'/run/secrets/dbpass','POSTGRES_USER':'studie','POSTGRES_DB':'studiebase',
                           'POSTGRES_INITDB_ARGS':'--auth-host=scram-sha-256'},
            'secrets':['dbpass'],'volumes':['data:/var/lib/postgresql','./seed.sql:/docker-entrypoint-initdb.d/01-init.sql:ro']}
        self.cfg={'services':{'postgres':pg},'volumes':{'data':{}},'networks':{'default':{'internal':True}},
                  'secrets':{'dbpass':{'file':'./db.pass'}}}
        if self.n=='12':
            conf=['wal_level=replica','archive_mode=on','archive_command=test ! -f /archive/%f && cp %p /archive/%f']
            for path in ['archive','backup']:
                (self.tmp/path).mkdir(mode=0o700)
                pg['volumes'].append('./'+path+':/'+path)
        self.setconf(conf)
    def setconf(self,values):
        self.cfg['services']['postgres']['command']=['postgres']+[a for v in values for a in ['-c',v]]
    def start(self,service='postgres'):
        for service_config in self.cfg['services'].values():
            if service_config['image']=='postgres:18':
                service_config['image']=os.environ.get('DBSEC_IMAGE','postgres:18')
        self.file.write_text(json.dumps(self.cfg,indent=2))
        cfg=json.loads(self.run(self.compose+['config','--format','json']))
        check(cfg['name']==self.project and all(not v.get('external') for k in ['volumes','networks'] for v in cfg.get(k,{}).values()),'Ressourcekontrol')
        check(all(p.get('host_ip')=='127.0.0.1' for s in cfg['services'].values() for p in s.get('ports',[])),'Portbinding')
        if not self.owned:
            for kind in ('ps','volume','network'):
                args=['docker','ps','-aq'] if kind=='ps' else ['docker',kind,'ls','-q']
                existing=self.run(args+['--filter','label=com.docker.compose.project='+self.project])
                check(not existing,'Projektnavnet bruges allerede')
        self.owned=True
        self.run(self.compose+['up','-d'])
        self.cid=self.run(self.compose+['ps','-q',service])
        self.wait(self.cid,'admin' if self.n=='13' else 'studie','appdb' if self.n=='13' else 'studiebase')
    def wait(self,cid,user,db):
        args=['docker','exec',cid,'psql','-XAt','-U',user,'-d',db,'-c',"SELECT current_setting('server_version')"]
        for _ in range(160):
            # PID 1 er først postgres, når init-serveren er lukket ned.
            if sp.run(['docker','exec',cid,'sh','-c','test "$(cat /proc/1/comm)" = postgres'],capture_output=True).returncode==0:
                p=sp.run(args,capture_output=True,text=True)
                if p.returncode==0:
                    self.run(args)
                    return
            time.sleep(.5)
        raise RuntimeError('Databasen blev ikke klar')
    def exe(self,*args,**kw):return self.run(['docker','exec','-i',self.cid,*args],**kw)
    def sql(self,query,*,user=None,db=None,cid=None,fail=None,expect=None):
        user=user or ('admin' if self.n=='13' else 'studie')
        db=db or ('appdb' if self.n=='13' else 'studiebase')
        args=['docker','exec','-i','-e','PGOPTIONS=-c statement_timeout=90000 -c idle_in_transaction_session_timeout=60000',cid or self.cid,'psql','-XAt','-v','ON_ERROR_STOP=1','-v','VERBOSITY=verbose','-U',user,'-d',db]
        self.note('SQL\n'+query)
        out=self.run(args,data=query+'\n',fail=fail)
        if expect is not None:check(re.search(expect,out,re.M|re.S),f'Mangler resultat / {expect}')
        return out
    def finish(self):
        if self.owned:
            ids=self.run(self.compose+['ps','-a','-q']).split()
            for cid in ids:
                owner=self.run(['docker','inspect','-f','{{ index .Config.Labels "com.docker.compose.project" }}',cid])
                check(owner==self.project,'Forkert ejer')
            self.run(self.compose+['down','-v','--timeout','8'])
        # Bevar kun øvelse 12s egne backup- og WAL-filer i privat arbejdsområde.
        for p in self.tmp.iterdir():
            if self.n=='12' and p.name in ('backup','archive'):continue
            if p.is_dir():shutil.rmtree(p)
            else:p.unlink()
        if not any(self.tmp.iterdir()):self.tmp.rmdir()
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('numre',nargs='+',choices=[f'{i:02}' for i in range(1,14)])
    parser.add_argument('--dest',type=Path)
    opt=parser.parse_args()
    dest=opt.dest or Path(tempfile.mkdtemp(prefix='gentest-',dir=ROOT/'kontrol'))
    dest=dest.resolve()
    os.umask(0o077)
    failed=False
    for n in opt.numre:
        lab=Lab(n,dest)
        result='PARTIAL'
        try:
            code=(A/'loesninger'/n/'test.py').read_text()
            exec(compile(code,n+'/test.py','exec'),{'L':lab,'check':check,'re':re,'time':time,'sp':sp,'Path':Path,'json':json,'shlex':shlex,'secrets':secrets,'os':os,'ROOT':ROOT,'A':A})
            result='PASS'
        except Exception:
            lab.note(traceback.format_exc())
        finally:lab.finish()
        lab.note(now()+'  '+result)
        (lab.ev/'seneste.txt').write_text(lab.log.name+'\n'+result+'\n')
        if dest==A/'evidens':
            rows=[]
            for i in range(1,14):
                nn=f'{i:02}'
                f=dest/nn/'seneste.txt'
                parts=f.read_text().splitlines() if f.exists() else [None,'NOT RUN']
                link=f'[Kørselslog](evidens/{nn}/{parts[0]})' if parts[0] else '—'
                rows.append(f'| {nn} | {parts[1]} | {link} |')
            (A/'STATUS.md').write_text('# Status for de 13 øvelser\n\n| Øvelse | Resultat | Dokumentation |\n|---|---|---|\n'+'\n'.join(rows)+'\n')
        failed |= result != 'PASS'
        print(n,result,lab.log,flush=True)
    return int(failed)
if __name__=='__main__':sys.exit(main())
