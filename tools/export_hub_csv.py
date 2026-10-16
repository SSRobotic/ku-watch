"""Copy a fixed prefix of the actual MicroSD CSV through read-only USB commands."""
import argparse, csv, hashlib, io, json, re, time
from datetime import datetime, timezone
from pathlib import Path
import serial

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',default='COM8');parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    conn=serial.Serial();conn.port=a.port;conn.baudrate=115200;conn.timeout=.2;conn.dtr=False;conn.rts=False;conn.open()
    def request(command,pattern):
        for attempt in range(3):
            conn.write((command+'\n').encode());until=time.monotonic()+4
            while time.monotonic()<until:
                line=conn.readline().decode('ascii','replace').strip()
                match=re.search(pattern,line)
                if match:return match
        raise RuntimeError('No response to '+command)
    try:
        time.sleep(.4)
        match=request('SDINFO',r'^HUB SD ready=1 .*?rows=(\d+) bytes=(\d+) .*?file=(\S+)$')
        rows,size,card_file=int(match[1]),int(match[2]),match[3]
        if not rows:raise RuntimeError('No recorded rows yet')
        data=bytearray()
        while len(data)<size:
            at=len(data);m=request('SDREAD '+str(at),rf'^HUB SDCHUNK offset={at} size=(\d+) hex=([a-f0-9]*)$')
            block=bytes.fromhex(m[2]);n=int(m[1]);assert len(block)==n and n>0
            data.extend(block[:size-at])
    finally:conn.close()
    name=Path(card_file).name;csv_path=a.output/name
    if csv_path.exists():raise RuntimeError('Refusing to overwrite an existing evidence export')
    csv_path.write_bytes(data)
    records=list(csv.DictReader(io.StringIO(data.decode('ascii'))))
    if len(records)!=rows:raise RuntimeError('Row count changed across file close / metadata; retain export and review')
    utc=[int(row['rtc_utc']) for row in records];intervals=[b-a for a,b in zip(utc,utc[1:])]
    report={'captured_utc':datetime.now(timezone.utc).isoformat(),'boundary':'Bytes read from the real hub MicroSD, fixed prefix at SDINFO; no generated or patched rows. This is a short CSV logging check, not a 24-hour or battery pass.',
            'port':a.port,'card_file':card_file,'export_file':name,'rows':len(records),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
            'first_rtc_utc':utc[0],'last_rtc_utc':utc[-1],'duration_s':utc[-1]-utc[0], 'intervals_s':intervals,
            'five_second_cadence':bool(intervals) and all(4<=i<=6 for i in intervals),
            'rtc_watch_max_difference_s':max(abs(int(r['rtc_utc'])-int(r['watch_utc'])) for r in records),
            'watch_boots':sorted(set(r['watch_boot'] for r in records)),
            'versions':sorted(set((r['watch_fw'],r['hub_fw']) for r in records)),
            'all_columns_valid':all(None not in r and all(v is not None for v in r.values()) for r in records)}
    report_path=a.output/(name+'.audit.json');report_path.write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
