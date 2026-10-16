"""Exercise saved settings, controller sleep and real Wi-Fi OTA on the watch."""
from pathlib import Path
import json,re,sys,time,urllib.request,urllib.parse,base64
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from activity_export import Watch
def main():
    watch=Watch('COM15');report={}
    def command(text,seconds=1):
        watch.send(text);lines=[];end=time.monotonic()+seconds
        while time.monotonic()<end:
            line=watch.serial.readline().decode(errors='replace').strip()
            if line and not line.startswith(('MAX30102','GPS WAIT','I2C ACK')):lines.append(line)
        return lines
    def portal():
        auth=command('SETUPAUTH')
        if not any(line.startswith('SETUPAUTH ') for line in auth):command('SETUP',2);auth=command('SETUPAUTH')
        _,ip,password=next(line.split() for line in auth if line.startswith('SETUPAUTH '))
        url='http://'+ip+'/';manager=urllib.request.HTTPPasswordMgrWithDefaultRealm();manager.add_password(None,url,'admin',password)
        opener=urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(manager))
        return url,password,opener
    try:
        url,password,opener=portal()
        with opener.open(url,timeout=5) as r:html=r.read().decode()
        fields=dict(re.findall(r"name='([^']+)'[^>]*value=\"([^\"]*)\"",html))
        # Only the settings form's token is needed; passwords stay unchanged.
        import html as html_module
        fields={k:html_module.unescape(v) for k,v in fields.items()};fields['token']=password
        fields['idle']='15'
        with opener.open(urllib.request.Request(url+'save',data=urllib.parse.urlencode(fields).encode()),timeout=5) as r:report['save_status']=r.status
        command('SETUP',2)
        time.sleep(18);report['sleep']=command('POWERINFO');report['wake']=command('WAKE');report['awake']=command('POWERINFO')
        report['reboot']=command('REBOOT',2);time.sleep(18)
        report['restored']=command('SETTINGSINFO');report['ota_before']=command('OTAINFO')
        url,password,opener=portal()
        # Return the default idle timeout so the user's watch keeps its intended behavior.
        with opener.open(url,timeout=5) as r:html=r.read().decode()
        fields={k:html_module.unescape(v) for k,v in re.findall(r"name='([^']+)'[^>]*value=\"([^\"]*)\"",html)}
        fields['token']=password;fields['idle']='60'
        with opener.open(urllib.request.Request(url+'save',data=urllib.parse.urlencode(fields).encode()),timeout=5) as r:report['restore_idle_status']=r.status
        time.sleep(6)
        firmware=(ROOT/'.pio/build/display_first/firmware.bin').read_bytes();boundary='KuWatchLocalValidation'
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="firmware"; filename="firmware.bin"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()+firmware+f'\r\n--{boundary}--\r\n'.encode()
        authorization='Basic '+base64.b64encode(('admin:'+password).encode()).decode()
        req=urllib.request.Request(url+'update?token='+password,data=body,headers={'Content-Type':'multipart/form-data; boundary='+boundary,'Authorization':authorization})
        with opener.open(req,timeout=60) as r:report['wifi_ota_status']=r.status;report['wifi_ota_response']=r.read().decode()
        time.sleep(20)
        # Discard the boot log to avoid copying any earlier credential command into output.
        watch.serial.reset_input_buffer()
        report['ota_after']=command('OTAINFO');report['settings_after']=command('SETTINGSINFO');report['map_after']=command('MAPINFO')
        report['network_after']=command('NETINFO')
    except Exception as e:
        report['error']=type(e).__name__
        if hasattr(e,'code'):report['http_error_code']=e.code
        raise
    finally:
        watch.close()
        (ROOT/'output/small_finish_validation/wireless.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
