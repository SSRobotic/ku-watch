"""Install the reviewed local image via Wi-Fi, then audit Wi-Fi activity export."""
from pathlib import Path
import base64,hashlib,json,sys,time,urllib.request
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from activity_export import Watch,save_activity
from activity_export_wifi import WifiWatch
def main():
    w=Watch('COM15');report={}
    def command(text,seconds=1):
        w.send(text);out=[];end=time.monotonic()+seconds
        while time.monotonic()<end:
            line=w.serial.readline().decode(errors='replace').strip()
            if line and not line.startswith(('MAX30102','GPS','I2C ACK','SETUPAUTH')):out.append(line)
        return out
    def credentials():
        for _ in range(3):
            w.send('SETUPAUTH');end=time.monotonic()+1
            while time.monotonic()<end:
                line=w.serial.readline().decode(errors='replace').strip()
                if line.startswith('SETUPAUTH '):return line.split()[1:]
            command('SETUP',2)
        raise RuntimeError('Setup portal unavailable')
    try:
        report['before']=command('OTAINFO');ip,password=credentials();url='http://'+ip+'/'
        auth='Basic '+base64.b64encode(('admin:'+password).encode()).decode()
        boundary='KuWatchReviewedBuild';firmware=(ROOT/'.pio/build/display_first/firmware.bin').read_bytes()
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="firmware"; filename="firmware.bin"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()+firmware+f'\r\n--{boundary}--\r\n'.encode()
        req=urllib.request.Request(url+'update?token='+password,data=body,headers={'Authorization':auth,'Content-Type':'multipart/form-data; boundary='+boundary})
        with urllib.request.urlopen(req,timeout=60) as r:report['status']=r.status;report['response']=r.read().decode()
        time.sleep(20);w.serial.reset_input_buffer();report['after']=command('OTAINFO');report['settings']=command('SETTINGSINFO')
        ip,password=credentials();wifi=WifiWatch('http://'+ip,password)
        # Private local handoff credential: later Wi-Fi maintenance does not need USB.
        (ROOT/'config/watch-access.local.json').write_text(json.dumps({'url':'http://'+ip,'username':'admin','password':password,'watch_mac':'D4:05:92:44:51:AC'},indent=2)+'\n')
        expected=json.loads((ROOT/'output/alert_activity_preservation_20261008.json').read_text())
        report['wifi_activities']={}
        for identity,size in wifi.list():
            raw=wifi.download(identity);digest=hashlib.sha256(raw).hexdigest()
            tcx,summary=save_activity(raw,identity,ROOT/'output/small_finish_validation/wifi_exports')
            report['wifi_activities'][str(identity)]={'bytes':len(raw),'unchanged':digest==expected.get(str(identity)),'tcx_created':tcx.exists()}
        report['clock_http_before']=wifi.status();wifi.set_time();report['clock_set_via_wifi']=True
        command('SETUP',2);report['final']=command('OTAINFO');report['map']=command('MAPINFO');report['queue']=command('NETINFO')
        report['installed_firmware_sha256']=hashlib.sha256(firmware).hexdigest()
    finally:w.close()
    (ROOT/'output/small_finish_validation/final_wireless.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
