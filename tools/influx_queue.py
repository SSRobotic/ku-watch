"""Local durable SQLite spool between Node-RED and InfluxDB (loopback only)."""
from __future__ import annotations
import argparse,json,re,sqlite3,threading,time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import URLError,HTTPError
ROOT=Path(__file__).resolve().parents[1]

class Spool:
    def __init__(self,path:Path):
        self.path=path;path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS queue(id INTEGER PRIMARY KEY,line TEXT NOT NULL,url TEXT NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS totals(name TEXT PRIMARY KEY,value INTEGER NOT NULL)')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=15)
        try:
            c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA synchronous=FULL')
            with c:yield c
        finally:c.close()
    def append(self,line,url):
        if not isinstance(line,str) or not line.startswith('ku_watch,') or '\n' in line or len(line)>8192:return False
        if not url.startswith('http://127.0.0.1:8181/api/v3/write_lp?') or len(url)>300:return False
        with self.connect() as c:
            if c.execute('SELECT COUNT(*) FROM queue').fetchone()[0]>=200000:return False
            c.execute('INSERT INTO queue(line,url) VALUES(?,?)',(line,url));return True
    def first(self):
        with self.connect() as c:return c.execute('SELECT id,line,url FROM queue ORDER BY id LIMIT 1').fetchone()
    def batch(self,limit=100):
        with self.connect() as c:rows=c.execute('SELECT id,line,url FROM queue ORDER BY id LIMIT ?', (min(100,max(1,limit)),)).fetchall()
        # A target change must not mix databases or precision in one write.
        result=[]
        for row in rows:
            if row[2]!=rows[0][2]:break
            result.append(row)
        return result
    def ack(self,row):
        self.ack_many([row])
    def ack_many(self,rows):
        if not rows:return
        with self.connect() as c:
            count=0
            for row in rows:count+=c.execute('DELETE FROM queue WHERE id=?',(row,)).rowcount
            c.execute("INSERT INTO totals VALUES('written',?) ON CONFLICT(name) DO UPDATE SET value=value+excluded.value",(count,))
    def status(self):
        with self.connect() as c:
            n=c.execute('SELECT COUNT(*) FROM queue').fetchone()[0]
            r=c.execute("SELECT value FROM totals WHERE name='written'").fetchone()
            return {'pending':n,'written':r[0] if r else 0}

def token():
    s=(ROOT/'include/config.h').read_text(encoding='utf-8-sig')
    m=re.search(r'INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"',s)
    return m[1] if m else ''

def serve(path=ROOT/'output/influx_spool/queue.sqlite',port=8871):
    spool=Spool(path);access=token()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            if self.path!='/status':self.send_error(404);return
            body=json.dumps(spool.status()).encode();self.send_response(200);self.end_headers();self.wfile.write(body)
        def do_POST(self):
            if self.path!='/enqueue':self.send_error(404);return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 1<=size<=8192:raise ValueError()
                line=self.rfile.read(size).decode('utf-8')
                ok=spool.append(line,self.headers.get('X-KU-Write-Url',''))
            except (ValueError,UnicodeError,sqlite3.Error):ok=False
            self.send_response(202 if ok else 503);self.end_headers();self.wfile.write(b'Queued' if ok else b'Queue unavailable')
    def writer():
        delay=1
        while True:
            rows=spool.batch()
            if not rows:time.sleep(.2);continue
            try:
                if not access:raise ValueError('Influx token not configured')
                req=Request(rows[0][2],data='\n'.join(row[1] for row in rows).encode(),method='POST',headers={'Authorization':'Bearer '+access,'Content-Type':'text/plain'})
                with urlopen(req,timeout=5) as r:
                    if not 200<=r.status<300:raise ValueError()
                    r.read()
                spool.ack_many([row[0] for row in rows]);delay=1
            except (URLError,HTTPError,ValueError,sqlite3.Error):time.sleep(delay);delay=min(delay*2,60)
    threading.Thread(target=writer,daemon=True).start()
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8871);a=p.parse_args();serve(port=a.port)
