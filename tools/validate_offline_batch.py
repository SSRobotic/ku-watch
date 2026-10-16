"""Ten-minute real Wi-Fi pause; no fabricated sensor packets or activity edits."""
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from activity_export import Watch
def main():
    watch=Watch('COM15');rows=[];report={'offline_seconds_requested':600}
    def read(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            line=watch.serial.readline().decode(errors='replace').strip()
            if line and not line.startswith('SETUPAUTH'):rows.append(line)
    def status():
        watch.send('NETINFO');read(1)
        for line in rows[-30:]:
            if line.startswith(('QUEUE','NETWORK wifi','NETWORK cloud')):print(line,flush=True)
    try:
        watch.send('SETTINGSINFO');watch.send('OTAINFO');watch.send('LINKINFO');read(2)
        status();report['started_utc']=time.time();watch.send('NETPAUSE 600');read(1)
        for minute in range(10):read(59);status();print('Offline test minute',minute+1,flush=True)
        report['pause_window_end_utc']=time.time();
        for attempt in range(12):
            read(10);status()
            recent=[r for r in rows[-40:] if r.startswith('QUEUE ready=')]
            if recent and 'pending=0 ' in recent[-1]:break
        watch.send('WAKE');watch.send('HOME');watch.send('MAPINFO');watch.send('INFO');read(2)
        report['completed_utc']=time.time();report['last_queue']=[r for r in rows if r.startswith('QUEUE ready=')][-1]
    finally:
        watch.close();(ROOT/'output/small_finish_validation/offline_serial.log').write_text('\n'.join(rows)+'\n',encoding='utf-8')
        (ROOT/'output/small_finish_validation/offline.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
