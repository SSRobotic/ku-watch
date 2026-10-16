"""Local release fixtures only: no firmware is flashed or served."""
import contextlib,hashlib,importlib.util,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ota_release',ROOT/'tools/ota_release.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)

class Release(unittest.TestCase):
    def setUp(self):
        location=ROOT/'output/ota_release_tests';location.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=location)
        self.root=Path(self.temp.name).resolve()
        assert self.root.is_relative_to(ROOT.resolve())
        (self.root/'include').mkdir()
        (self.root/'include/watch_extensions.h').write_text('constexpr const char* VERSION="2.0.8";')
        self.image=self.root/'fixture.bin';self.image.write_bytes(b'\xe9LOCAL FIXTURE 2.0.8\0 NEVER FLASHED')
        self.root_patch=patch.object(release,'ROOT',self.root);self.root_patch.start()
    def tearDown(self):self.root_patch.stop();self.temp.cleanup()
    def run_release(self,*args):
        with patch('sys.argv',['ota_release','--firmware',str(self.image),*args]),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            release.main()
    def test_template_keeps_manifest_unconfigured(self):
        self.run_release('--version','2.0.8','--template')
        folder=self.root/'output/ota_release/2.0.8'
        manifest=json.loads((folder/'manifest.template.json').read_text())
        self.assertEqual(manifest['url'],'HTTPS_FIRMWARE_URL')
        self.assertFalse((folder/'manifest.json').exists())
        self.assertEqual(manifest['sha256'],hashlib.sha256(self.image.read_bytes()).hexdigest())
        self.assertEqual((folder/'firmware.bin').read_bytes(),self.image.read_bytes())
    def test_rejects_mismatch_and_traversal_before_writing(self):
        for version in ['2.0.9','../../outside']:
            with self.subTest(version=version),self.assertRaises(SystemExit):
                self.run_release('--version',version,'--template')
        self.assertFalse((self.root/'output').exists())
    def test_rejects_credentials_and_non_https(self):
        for url in ['http://example.com/firmware.bin','https:///missing','https://user:secret@example.com/firmware.bin']:
            with self.subTest(url=url),self.assertRaises(SystemExit):
                self.run_release('--version','2.0.8','--url',url)
        self.assertFalse((self.root/'output').exists())
    def test_rejects_non_esp_fixture(self):
        self.image.write_bytes(b'INVALID 2.0.8\0')
        with self.assertRaises(SystemExit):self.run_release('--version','2.0.8','--template')
        self.assertFalse((self.root/'output').exists())

if __name__=='__main__':unittest.main()
