"""Read-only board audit + local portal probes. Never print or log credentials."""
from pathlib import Path
import hashlib,json,re,sys,time,urllib.request,urllib.parse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from activity_export import Watch

def main():
    out=ROOT/'output/small_finish_validation';out.mkdir(exist_ok=True)
    watch=Watch('COM15');report={'firmware':'2.0.0','activities':{}}
    def command(text,seconds=2):
        watch.send(text);lines=[];end=time.monotonic()+seconds
        while time.monotonic()<end:
            line=watch.serial.readline().decode('utf-8',errors='replace').strip()
            if line and not line.startswith(('MAX30102','GPS DATA','I2C ACK')):lines.append(line)
        return lines
    try:
        for cmd in ['INFO','SETTINGSINFO','LINKINFO','OTAINFO','MAPINFO','NETINFO','SENSORINFO']:
            report[cmd]=command(cmd)
        expected=json.loads((ROOT/'output/alert_activity_preservation_20261008.json').read_text())
        for identity,_ in watch.list():
            raw=watch.download(identity);digest=hashlib.sha256(raw).hexdigest()
            report['activities'][str(identity)]={'sha256':digest,'unchanged':expected.get(str(identity))==digest}
        command('SETUP',2)
        auth=command('SETUPAUTH',1)
        # Credentials stay inside this process and are not included in the report.
        values=next((line.split() for line in auth if line.startswith('SETUPAUTH ')),None)
        if values and len(values)==3:
            ip,password=values[1:];report['portal_ip']=ip
            manager=urllib.request.HTTPPasswordMgrWithDefaultRealm();url='http://'+ip+'/'
            manager.add_password(None,url,'admin',password)
            opener=urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(manager))
            try:
                with opener.open(url,timeout=5) as r:html=r.read().decode()
                report['portal_authenticated']=r.status==200
                report['portal_sections_present']=all(v in html for v in ['/save','/update','/csv','temperature_limit','iaq_limit'])
                with opener.open(url+'csv?slot=0',timeout=5) as r:csv=r.read()
                report['csv_downloaded']=csv.startswith(b'timestamp,uptime_ms,')
                (out/'sensors.csv').write_bytes(csv)
            except Exception as e:report['portal_probe_error']=type(e).__name__
        report['close_setup']=command('SETUP',2)
        report['final_map']=command('MAPINFO')
    finally:watch.close()
    (out/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
