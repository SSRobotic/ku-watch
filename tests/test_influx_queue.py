import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from influx_queue import Spool
class TestSpool(unittest.TestCase):
    def test_batch_target_boundaries_and_atomic_ack(self):
        with tempfile.TemporaryDirectory() as d:
            s=Spool(Path(d)/'queue.sqlite')
            url='http://127.0.0.1:8181/api/v3/write_lp?db=iot&precision=second'
            other=url.replace('iot','other')
            for n in range(4):self.assertTrue(s.append('ku_watch,device=board temp=25 '+str(1790123456+n),url if n<3 else other))
            rows=s.batch();self.assertEqual(len(rows),3)
            # Reading/sending a batch does not remove rows. A failed HTTP write
            # or process restart replays the whole unacknowledged batch.
            restarted=Spool(s.path);self.assertEqual(restarted.batch(),rows)
            s.ack_many([r[0] for r in rows]);self.assertEqual(s.status(),{'pending':1,'written':3})
            s.ack_many([r[0] for r in rows]);self.assertEqual(s.status()['written'],3)
            self.assertEqual(s.batch()[0][2],other)
    def test_durable_recovery_ack_and_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'queue.sqlite';s=Spool(p)
            url='http://127.0.0.1:8181/api/v3/write_lp?db=iot&precision=second'
            self.assertTrue(s.append('ku_watch,device=board temp=25 1790123456',url))
            self.assertTrue(s.append('ku_watch,device=board temp=26 1790123457',url))
            restarted=Spool(p);self.assertEqual(restarted.status()['pending'],2)
            first=restarted.first();self.assertIn('1790123456',first[1]);restarted.ack(first[0])
            self.assertEqual(restarted.status(),{'pending':1,'written':1})
            self.assertFalse(s.append('ku_watch,device=board temp=25\nother x=1',url))
            self.assertFalse(s.append('ku_watch,device=board temp=25','http://example.com/'))
            self.assertFalse(s.append('not_a_watch,device=board temp=25',url))
            self.assertEqual(s.status()['pending'],1)
if __name__=='__main__':unittest.main()
