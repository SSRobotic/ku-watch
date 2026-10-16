"""Final real-board window replay, clock and portal audit; no fake sensor data."""
from pathlib import Path
import base64,json,re,sys,time,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from activity_export import Watch
def main():
    w=Watch('COM15');result={};log=[]
    def read(seconds):
        end=time.monotonic()+seconds;lines=[]
        while time.monotonic()<end:
            s=w.serial.readline().decode(errors='replace').strip()
            if s.startswith(('CLOCK ','NETWORK ','QUEUE ','POWER ','LINK ','OTA ','SETTINGS ','SCREEN ','LCD ','REBOOT ')):
                lines.append(s);log.append({'at':time.time(),'line':s})
        return lines
    def command(text,seconds=1):w.send(text);return read(seconds)
    try:
        result['before_clock']=command('CLOCKINFO');result['before_power']=command('POWERINFO');result['link']=command('LINKINFO')
        command('SETUP',2);w.send('SETUPAUTH');end=time.monotonic()+2;credential=None
        while time.monotonic()<end:
            s=w.serial.readline().decode(errors='replace').strip()
            if s.startswith('SETUPAUTH '):credential=s.split()[1:];break
        if not credential:raise RuntimeError('Portal unavailable')
        ip,password=credential;url='http://'+ip+'/'
        def probe(path,username='ADMIN',data=None,auth=True):
            headers={}
            if auth:headers['Authorization']='Basic '+base64.b64encode((username+':'+password).encode()).decode()
            req=urllib.request.Request(url+path,data=data,headers=headers)
            try:
                with urllib.request.urlopen(req,timeout=5) as response:return response.status,response.read()
            except urllib.error.HTTPError as e:return e.code,e.read()
        code,html=probe('');text=html.decode()
        result['portal']={'uppercase_login':code,'renderable_key':password.isupper(),'clock_button_present':'Date.now()' in text,'magcal_present':'/magcal' in text,
            'unauthenticated':probe('',auth=False)[0],'bad_activity':probe('activity?id=../')[0],
            'rejected_delete_token':probe('delete',data=b'token=invalid&id=3')[0],
            'rejected_clock_token':probe('clock',data=b'token=invalid&utc=1791474000')[0]}
        assert code==200 and all(result['portal'][v] for v in ['renderable_key','clock_button_present','magcal_present'])
        assert [result['portal'][v] for v in ['unauthenticated','bad_activity','rejected_delete_token','rejected_clock_token']]==[401,400,403,403]
        command('SETUP',2)
        result['pause_started']=time.time();command('NETPAUSE 90');read(44)
        result['mid_pause_clock']=command('CLOCKINFO');result['mid_pause_queue']=command('NETINFO');read(44)
        result['pause_ended']=time.time();result['end_pause_queue']=command('NETINFO')
        # Bounded catch-up wait. New captures continue throughout the test.
        for n in range(8):
            read(4);lines=command('NETINFO');result['catchup']=lines
            if any(re.search(r'QUEUE ready=1 pending=[01] acked=\d+ dropped=0 errors=0',s) for s in lines):break
        else:raise RuntimeError('Backlog did not drain within 40 seconds')
        result['drained_at']=time.time();result['clock']=command('CLOCKINFO');result['power']=command('POWERINFO')
        command('HOME');command('WAKE');result['screen']=command('SCREENINFO');result['ota']=command('OTAINFO')
        with urllib.request.urlopen('http://127.0.0.1:8871/status',timeout=5) as r:result['spool']=json.load(r)
    finally:
        w.close();(ROOT/'output/small_finish_validation/final_audit.json').write_text(json.dumps(result,indent=2))
        (ROOT/'output/small_finish_validation/final_audit_serial.json').write_text(json.dumps(log))
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
