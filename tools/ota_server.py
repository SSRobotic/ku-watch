"""Private firmware download gateway, forwarded through the existing tunnel tool.
Only a random 256-bit capability can read release files; no admin/write routes.
"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import hashlib,hmac,json,re,time
import argparse,ipaddress,ssl
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'config/ota.local.json'
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def serve(self):
        try:
            c=json.loads(CONFIG.read_text());path=urlsplit(self.path)
            parts=path.path.split('/')
            permitted=(not path.query and len(parts)==4 and parts[1]=='r' and
                re.fullmatch(r'[a-f0-9]{64}',c['capability']) and hmac.compare_digest(parts[2],c['capability']) and
                parts[3] in ('manifest.json','firmware.bin') and re.fullmatch(r'\d+\.\d+\.\d+',c['version']))
            if not permitted:self.send_error(404);return
            folder=ROOT/'output/ota_release'/c['version'];file=folder/parts[3]
            if not file.exists():self.send_error(503);return
            if parts[3]=='manifest.json':
                manifest=json.loads(file.read_text());image=folder/'firmware.bin'
                if manifest['version']!=c['version'] or hashlib.sha256(image.read_bytes()).hexdigest()!=manifest['sha256']:
                    self.send_error(503);return
            self.send_response(200);self.send_header('Content-Type','application/json' if parts[3].endswith('.json') else 'application/octet-stream')
            self.send_header('Content-Length',str(file.stat().st_size));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
            if self.command=='GET':
                with file.open('rb') as stream:
                    while chunk:=stream.read(16384):self.wfile.write(chunk)
                # No capability, source IP or URL is written to the diagnostic log.
                print(json.dumps({'served':parts[3],'version':c['version'],'utc':int(time.time())}),flush=True)
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception:self.send_error(503)
    do_GET=do_HEAD=serve
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--bind',default='127.0.0.1');parser.add_argument('--port',type=int,default=8872)
    parser.add_argument('--tls-cert',type=Path);parser.add_argument('--tls-key',type=Path)
    parser.add_argument('--config',type=Path,default=CONFIG)
    args=parser.parse_args();address=ipaddress.ip_address(args.bind)
    if not address.is_loopback and (not address.is_private or not args.tls_cert or not args.tls_key):parser.error('LAN binding requires a private address and TLS certificate/key')
    if bool(args.tls_cert)!=bool(args.tls_key):parser.error('Both TLS certificate and key are required')
    CONFIG=args.config.resolve()
    config=json.loads(CONFIG.read_text())
    if not re.fullmatch(r'[a-f0-9]{64}',config.get('capability','')):parser.error('A 256-bit capability is required')
    server=ThreadingHTTPServer((args.bind,args.port),Handler);server.daemon_threads=True
    if args.tls_cert:
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(args.tls_cert,args.tls_key)
        server.socket=context.wrap_socket(server.socket,server_side=True)
    print(json.dumps({'service':'KU Watch read-only OTA','bind':args.bind,'port':args.port,'tls':bool(args.tls_cert),'capability_logged':False}),flush=True)
    server.serve_forever()
