import importlib.util
import pathlib
import struct
import sys
import unittest
import zlib
import xml.etree.ElementTree as ET
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import activity_export as app

class ExportTests(unittest.TestCase):
    def test_fragmented_usb_lines_survive_timeouts_and_generator_restart(self):
        class Stream:
            def __init__(self):self.chunks=[b'REC DA',b'',b'TA 3 0 1234',b'5678\nREC ',b'END 3 4 00000000\n']
            @property
            def in_waiting(self):return 0
            def read(self,unused):return self.chunks.pop(0) if self.chunks else b''
        watch=app.Watch.__new__(app.Watch);watch.serial=Stream();watch.pending=bytearray()
        self.assertEqual(next(watch.lines()),'\x52\x45\x43\x20\x44\x41\x54\x41\x20\x33\x20\x30\x20\x31\x32\x33\x34\x35\x36\x37\x38')
        self.assertEqual(next(watch.lines()),'REC END 3 4 00000000')
    @classmethod
    def setUpClass(cls):
        cls.raw=(ROOT/'output/activity_format_fixture.kua').read_bytes()
    def test_firmware_binary_and_missing_sensors(self):
        a=app.decode(self.raw)
        self.assertEqual(a['utc'],1790166919)
        self.assertEqual(a['duration_ms'],4100)
        self.assertEqual(a['distance_cm'],111)
        self.assertEqual(len(a['records']),4)
        self.assertFalse(a['recovered'])
        xml=ET.fromstring(app.tcx_bytes(a));ns={'t':app.NS}
        self.assertEqual(len(xml.findall('.//t:Position',ns)),2)
        self.assertEqual(len(xml.findall('.//t:HeartRateBpm',ns)),3)
        self.assertEqual(len(xml.findall('.//t:Track',ns)),2)
        self.assertEqual(xml.find('.//t:Id',ns).text,'2026-09-23T12:35:19.000Z')
        self.assertEqual(xml.find('.//t:Calories',ns).text,'0')
    def test_official_tcx_schema(self):
        from lxml import etree
        schema=etree.XMLSchema(etree.parse(str(ROOT/'tests/fixtures/TrainingCenterDatabasev2.xsd')))
        schema.assertValid(etree.fromstring(app.tcx_bytes(app.decode(self.raw))))
    def test_power_loss_recovers_complete_records(self):
        a=app.decode(self.raw[:-32]+b'partial')
        self.assertTrue(a['recovered']);self.assertEqual(len(a['records']),4)
        self.assertEqual(a['duration_ms'],3000)
        self.assertIn(b'Recovered',app.tcx_bytes(a))
    def test_corruption_rejected(self):
        for index in (1,20,40,100):
            b=bytearray(self.raw);b[index]^=1
            with self.assertRaises(ValueError):app.decode(bytes(b))
    def test_out_of_order_rejected(self):
        b=bytearray(self.raw);struct.pack_into('<I',b,96,500)
        struct.pack_into('<I',b,124,zlib.crc32(b[96:124]))
        with self.assertRaises(ValueError):app.decode(bytes(b))
    def test_no_fake_positions_or_heart_rate(self):
        a=app.decode(self.raw)
        for r in a['records']:r['flags']=0;r['distance']=0
        a['distance_cm']=0
        xml=app.tcx_bytes(a)
        self.assertNotIn(b'<Position>',xml);self.assertNotIn(b'<HeartRateBpm>',xml)
        self.assertIn(b'<Time>',xml)
    def test_stationary_zero_coordinates_are_valid(self):
        a=app.decode(self.raw);a['records'][0]['lat']=a['records'][0]['lon']=0
        self.assertIn(b'<LatitudeDegrees>0.0000000</LatitudeDegrees>',app.tcx_bytes(a))
    def test_download_checks_offset_and_crc(self):
        class FakeWatch(app.Watch):
            def __init__(self,lines):self.feed=iter(lines)
            def send(self,c):pass
            def lines(self,timeout=15):
                for line in self.feed:yield line
                raise TimeoutError()
        raw=self.raw
        lines=[f'REC BEGIN 1 {len(raw)}','unrelated sensor output',f'REC DATA 1 0 {raw.hex()}',f'REC END 1 {len(raw)} {zlib.crc32(raw):08x}']
        self.assertEqual(FakeWatch(lines).download(1),raw)
        bad=lines.copy();bad[2]=f'REC DATA 1 32 {raw.hex()}'
        with self.assertRaises(ValueError):FakeWatch(bad).download(1)
        bad=lines.copy();bad[-1]=f'REC END 1 {len(raw)} 00000000'
        with self.assertRaises(ValueError):FakeWatch(bad).download(1)
    def test_gui_constructs(self):
        import tkinter
        def short_loop(root):root.update_idletasks();root.destroy()
        with patch.object(tkinter.Tk,'mainloop',short_loop):app.gui()

if __name__=='__main__':unittest.main()
