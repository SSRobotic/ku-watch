"""Install a local reviewed image using the saved, private watch credentials."""
from pathlib import Path
import argparse,base64,hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);parser.add_argument('--firmware',type=Path,default=ROOT/'.pio/build/display_first/firmware.bin');args=parser.parse_args()
    s=json.loads((ROOT/'config/watch-access.local.json').read_text())
    url=s['url'].rstrip('/')+'/'
    if not url.startswith('http://'):raise ValueError('Local watch URL required')
    authorization='Basic '+base64.b64encode((s['username']+':'+s['password']).encode()).decode()
    request=lambda route:urllib.request.Request(url+route,headers={'Authorization':authorization})
    with urllib.request.urlopen(request('activities'),timeout=15) as r:activities=json.load(r)
    if activities['active']:raise RuntimeError('Stop active WALK before OTA')
    firmware=args.firmware.read_bytes()
    if not 1024<len(firmware)<=1572864:raise RuntimeError('Image does not fit the watch app slot')
    boundary='KuReviewedWifiImage'
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="firmware"; filename="firmware.bin"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()+firmware+f'\r\n--{boundary}--\r\n'.encode()
    # Watch independently enforces battery >=30%, auth and inactive app writing.
    req=urllib.request.Request(url+'update?token='+s['password'],data=body,headers={
        'Authorization':authorization,'Content-Type':'multipart/form-data; boundary='+boundary})
    with urllib.request.urlopen(req,timeout=60) as r:report={'status':r.status,'response':r.read().decode(),
        'bytes':len(firmware),'sha256':hashlib.sha256(firmware).hexdigest()}
    (ROOT/args.report).write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
if __name__=='__main__':
    try:main()
    except Exception as e:
        # URLs include CSRF tokens; never print exception URLs.
        print('Wi-Fi install failed:',type(e).__name__);raise SystemExit(1)
