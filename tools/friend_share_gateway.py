"""Loopback gateway exposing only one Grafana external dashboard, never admin APIs."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.client import HTTPConnection
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
import re

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'config/friend-share.local.json'
STATIC=('/public/build/','/public/img/','/public/fonts/','/public/locales/','/public/plugins/')

def token():
    try:
        c=json.loads(CONFIG.read_text(encoding='utf-8'))
        t=c.get('access_token','')
        return t if c.get('enabled') and re.fullmatch(r'[a-fA-F0-9]{32}',t) else None
    except (OSError,ValueError): return None

def allowed(method,target,access):
    if not access or method not in ('GET','HEAD','POST'): return False
    parsed=urlsplit(target)
    if parsed.scheme or parsed.netloc: return False
    path=unquote(parsed.path)
    if path!=parsed.path or '\\' in path or '..' in path or '//' in path: return False
    base='/api/public/dashboards/'+access
    if method in ('GET','HEAD'):
        return path=='/public-dashboards/'+access or path in (base,base+'/annotations') or path.startswith(STATIC)
    return bool(re.fullmatch(re.escape(base)+r'/panels/[1-9][0-9]*/query',path))

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*args): pass # Never write capability links or sensor data to access logs.
    def local_response(self,status,body=b'Not available',ctype='text/plain; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Robots-Tag','noindex, nofollow, noarchive')
        self.send_header('Connection','close');self.end_headers()
        self.close_connection=True
        if self.command!='HEAD':self.wfile.write(body)
    def serve(self):
        if self.path=='/robots.txt' and self.command in ('GET','HEAD'):
            return self.local_response(200,b'User-agent: *\nDisallow: /\n')
        if not allowed(self.command,self.path,token()):return self.local_response(404)
        try:
            if self.headers.get('Transfer-Encoding'):return self.local_response(400)
            size=int(self.headers.get('Content-Length','0'))
            if not 0<=size<=8192:return self.local_response(413)
            body=self.rfile.read(size) if size else None
            if self.command=='POST':
                p=json.loads(body or b'{}')
                if not isinstance(p,dict):return self.local_response(400)
            connection=HTTPConnection('127.0.0.1',3000,timeout=20)
            # No cookies, authorization, user-supplied host or forwarded headers reach Grafana.
            headers={'Host':'127.0.0.1:3000','Accept-Encoding':'identity'}
            if body:headers['Content-Type']='application/json'
            connection.request(self.command,self.path,body,headers)
            response=connection.getresponse();data=response.read();connection.close()
            # Redirects are denied so no upstream login/admin URL can escape this gateway.
            if 300<=response.status<400:return self.local_response(404)
            self.send_response(response.status)
            for name in ('Content-Type','Content-Encoding','ETag','Last-Modified'):
                value=response.getheader(name)
                if value:self.send_header(name,value)
            self.send_header('Cache-Control','public, max-age=3600' if self.path.startswith(STATIC) else 'no-store')
            self.send_header('X-Robots-Tag','noindex, nofollow, noarchive')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Length',str(len(data)));self.end_headers()
            if self.command!='HEAD':self.wfile.write(data)
        except (ValueError,TypeError):self.local_response(400)
        except Exception:self.local_response(502,b'Grafana temporarily unavailable')
    do_GET=do_HEAD=do_POST=do_PUT=do_PATCH=do_DELETE=do_OPTIONS=serve

if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',8767),Handler)
    server.daemon_threads=True
    print('KU Watch view-only gateway: 127.0.0.1:8767',flush=True)
    server.serve_forever()
