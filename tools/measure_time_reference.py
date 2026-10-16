"""Read-only NTP clock comparison; never changes computer or device time.
RFC 5905 timestamps/offset; request/response origin and synchronized server checked.
"""
import argparse,json,socket,struct,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];EPOCH=2208988800
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
def encode(t):
    whole=int(t)+EPOCH
    return struct.pack('!II',whole,int((t-int(t))*2**32))
def decode(b):
    whole,fraction=struct.unpack('!II',b);return whole-EPOCH+fraction/2**32
rows=[]
for host in ['time.google.com','time.cloudflare.com','pool.ntp.org']:
    try:
        address=socket.gethostbyname(host)
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as client:
            client.settimeout(3);client.connect((address,123))
            request=bytearray(48);request[0]=0x23;t1=time.time();request[40:48]=encode(t1)
            client.send(request);response=client.recv(512);t4=time.time()
        if len(response)<48 or response[0]>>6==3 or response[0]&7!=4 or not 1<=response[1]<16 or response[24:32]!=request[40:48]:
            raise ValueError('Invalid NTP response')
        t2=decode(response[32:40]);t3=decode(response[40:48])
        if t2<1704067200 or t3<t2:raise ValueError('Invalid NTP timestamps')
        offset=((t2-t1)+(t3-t4))/2;delay=max(0,(t4-t1)-(t3-t2))
        root_delay=max(0,struct.unpack('!i',response[4:8])[0]/65536)
        dispersion=struct.unpack('!I',response[8:12])[0]/65536
        rows.append({'server':host,'offset_ms':offset*1000,'roundtrip_ms':delay*1000,
                     'uncertainty_ms':(delay/2+root_delay/2+dispersion)*1000,'stratum':response[1],'valid':True})
    except (OSError,ValueError):rows.append({'server':host,'valid':False})
valid=[r for r in rows if r['valid']];best=min(valid,key=lambda r:r['uncertainty_ms']) if valid else None
spread=max((r['offset_ms'] for r in valid),default=0)-min((r['offset_ms'] for r in valid),default=0)
report={'boundary':'NTP comparison only; no system clock change','measured_at_host_ms':time.time()*1000,'samples':rows,
        'offset_ms':best['offset_ms'] if best else None,'uncertainty_ms':best['uncertainty_ms'] if best else None,
        'agreement_ms':spread,'usable':len(valid)>=2 and spread<200 and best['uncertainty_ms']<200}
(ROOT/a.output).write_text(json.dumps(report,indent=2));print(json.dumps(report))
