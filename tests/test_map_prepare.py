import importlib.util
from pathlib import Path
import struct
import unittest
import zlib

spec=importlib.util.spec_from_file_location("map_prepare",Path(__file__).resolve().parents[1]/"tools"/"map_prepare.py")
maps=importlib.util.module_from_spec(spec);spec.loader.exec_module(maps)

class MapTests(unittest.TestCase):
    def test_clipped_road_and_crc(self):
        source={"elements":[{"id":1,"tags":{"highway":"primary"},"geometry":[{"lat":13,"lon":99},{"lat":13,"lon":101}]}]}
        data,meta=maps.prepare(source,13,100,1200,"TEST")
        h=maps.HEADER.unpack(data[:64])
        self.assertEqual(h[5:7],(1,2))
        self.assertEqual(h[7],zlib.crc32(data[64:]))
        self.assertEqual(h[-1],zlib.crc32(data[:60]))
        points=[maps.POINT.unpack_from(data,70+8*i) for i in range(2)]
        self.assertTrue(all(abs(p[1]/1e7-100)<.02 for p in points))
        self.assertEqual(meta["roads"],1)
    def test_polygon_clip(self):
        p=maps.clip_polygon([(-200,-200),(200,-200),(200,200),(-200,200),(-200,-200)],100)
        self.assertEqual(len(p),5)
        self.assertTrue(all(abs(x)<=100 and abs(y)<=100 for x,y in p))
        self.assertEqual(p[0],p[-1])
    def test_disconnected_segments(self):
        result=maps.clip_line([(-50,0),(0,0),(200,200),(200,-200),(0,0)],100)
        self.assertEqual(len(result),2)
    def test_invalid_input(self):
        for lat,lon,radius,name in [(90,100,1000,"X"),(13,200,1000,"X"),(13,100,0,"X"),(13,100,1000,"X"*24)]:
            with self.assertRaises(ValueError): maps.prepare({},lat,lon,radius,name)
        with self.assertRaises(ValueError): maps.prepare({},13,100,1000,"EMPTY")

if __name__=="__main__":unittest.main()
