"""Probe saved setup without modifying settings, firmware, clock or activities."""
from pathlib import Path
import base64,html,json,re,urllib.request,urllib.error,urllib.parse
ROOT=Path(__file__).resolve().parents[1]
def main():
    saved=json.loads((ROOT/'config/watch-access.local.json').read_text())
    url=saved['url'].rstrip('/')+'/'
    auth='Basic '+base64.b64encode((saved['username']+':'+saved['password']).encode()).decode()
    def request(route,data=None,authorize=True,content_type=None):
        headers={'Authorization':auth} if authorize else {}
        if content_type:headers['Content-Type']=content_type
        req=urllib.request.Request(url+route,data=data,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=8) as r:return r.status,r.read()
        except urllib.error.HTTPError as e:return e.code,e.read()
    report={}
    try:
        status,body=request('');text=body.decode();report['authenticated']=status
        status,body=request('status');report['status_before']=json.loads(body) if status==200 else None
        fields={k:html.unescape(v) for k,v in re.findall(r"name='([^']+)'[^>]*value=\"([^\"]*)\"",text)}
        fields['token']=saved['password'];fields['idle']='1' # rejected; never stored
        report['invalid_settings']=request('save',urllib.parse.urlencode(fields).encode())[0]
        report['unauthenticated']=request('',authorize=False)[0]
        report['invalid_csv']=request('csv?slot=../../')[0]
        report['invalid_activity']=request('activity?id=../')[0]
        report['invalid_clock_token']=request('clock',b'token=invalid&utc=1791474000')[0]
        report['invalid_delete_token']=request('delete',b'token=invalid&id=3')[0]
        boundary='KuRejectedUploadProbe'
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="firmware"; filename="invalid.bin"\r\nContent-Type: application/octet-stream\r\n\r\nREJECTED\r\n--{boundary}--\r\n').encode()
        report['invalid_ota_token']=request('update?token=invalid',body,content_type='multipart/form-data; boundary='+boundary)[0]
        report['empty_ota']=request('update?token=invalid',b'')[0]
        report['raw_ota']=request('update?token=invalid',b'{}',content_type='application/json')[0]
        report['invalid_close_token']=request('close',b'token=invalid')[0]
        status,after=request('');after=after.decode()
        # Keep only a boolean. The form contains credentials/capability URLs.
        report['settings_unchanged']=text==after
        status,body=request('status');report['status_after']=json.loads(body) if status==200 else None
        report['no_reboot']=bool(report['status_before'] and report['status_after'] and report['status_after']['uptime_ms']>=report['status_before']['uptime_ms'])
        report['passed']=report['authenticated']==200 and report['invalid_settings']==400 and report['unauthenticated']==401 and report['invalid_csv']==400 and report['invalid_activity']==400 and report['invalid_clock_token']==403 and report['invalid_delete_token']==403 and report['invalid_ota_token']==400 and report['empty_ota']==400 and report['raw_ota']==400 and report['invalid_close_token']==403 and report['settings_unchanged'] and report['no_reboot']
    except Exception as e:report['error']=type(e).__name__;report['passed']=False
    (ROOT/'output/requirements_audit_20261009/portal_acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
    return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
