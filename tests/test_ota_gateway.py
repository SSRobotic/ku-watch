import hashlib,http.client,importlib.util,json,tempfile,threading,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ota_gateway',ROOT/'tools/ota_server.py')
gateway=importlib.util.module_from_spec(spec);spec.loader.exec_module(gateway)
class Gateway(unittest.TestCase):
    def setUp(self):
        location=ROOT/'output/ota_gateway_tests';location.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=location);base=Path(self.temp.name).resolve()
        assert base.is_relative_to(ROOT.resolve())
        self.base=base;self.cap='a'*64;self.image=b'LOCAL TEST IMAGE - NEVER FLASHED'
        folder=base/'output/ota_release/2.0.3';folder.mkdir(parents=True)
        (folder/'firmware.bin').write_bytes(self.image)
        (folder/'manifest.json').write_text(json.dumps({'version':'2.0.3','sha256':hashlib.sha256(self.image).hexdigest()}))
        (base/'config.json').write_text(json.dumps({'capability':self.cap,'version':'2.0.3'}))
        gateway.ROOT=base;gateway.CONFIG=base/'config.json'
        self.server=gateway.ThreadingHTTPServer(('127.0.0.1',0),gateway.Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def request(self,route,method='GET'):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        c.request(method,route);r=c.getresponse();status=r.status;data=r.read();c.close();return status,data
    def test_scope_and_read_only(self):
        for p in ['/','/admin','/r/'+('b'*64)+'/firmware.bin','/r/'+self.cap+'/../firmware.bin','/r/'+self.cap+'/config.json']:
            self.assertEqual(self.request(p)[0],404)
        p='/r/'+self.cap+'/firmware.bin'
        self.assertEqual(self.request(p),(200,self.image));self.assertEqual(self.request(p,'HEAD'),(200,b''))
        self.assertEqual(self.request(p,'POST')[0],501)
    def test_manifest_hash_and_version(self):
        p='/r/'+self.cap+'/manifest.json';self.assertEqual(self.request(p)[0],200)
        (self.base/'output/ota_release/2.0.3/firmware.bin').write_bytes(b'CHANGED')
        self.assertEqual(self.request(p)[0],503)
if __name__=='__main__':unittest.main()
