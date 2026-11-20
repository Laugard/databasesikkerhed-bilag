"""Styr en vedvarende psql-session via dens standardindgang."""
import queue, shlex, subprocess, threading, time, uuid
class Session:
    def __init__(self,lab,name):
        self.lab=lab
        self.name=name
        self.lines=queue.Queue()
        args=['docker','exec','-i','-e','PGAPPNAME='+name,'-e','PGOPTIONS=-c statement_timeout=30000 -c idle_in_transaction_session_timeout=45000',lab.cid,
              'psql','-XAt','-v','ON_ERROR_STOP=1','-v','VERBOSITY=verbose','-U','studie','-d','studiebase']
        lab.note('Åbner '+name+' / '+shlex.join(args))
        self.p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        def collect():
            for s in self.p.stdout:self.lines.put(s.rstrip('\n'))
            self.lines.put(None)
        threading.Thread(target=collect,daemon=True).start()
    def send(self,sql):
        self.lab.note(self.name+' > '+sql)
        self.marker=uuid.uuid4().hex
        self.p.stdin.write(sql+'\n\\echo '+self.marker+'\n')
        self.p.stdin.flush()
    def read(self,expected_error=False):
        buf=[]
        end=time.monotonic()+40
        while True:
            line=self.lines.get(timeout=max(.1,end-time.monotonic()))
            if line is None or line==self.marker:break
            buf.append(line)
        out='\n'.join(buf)
        self.lab.note(self.name+' < '+out)
        if line is None and not expected_error:raise RuntimeError('Sessionen sluttede uventet')
        return out
    def q(self,sql):
        self.send(sql)
        return self.read()
    def close(self):
        if self.p.poll() is None:
            self.p.stdin.close()
        rc=self.p.wait(timeout=5)
        self.lab.note(self.name+' exit '+str(rc))
        return rc
