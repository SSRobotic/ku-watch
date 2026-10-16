"""Exercise all real pages over authenticated ESP-NOW, restore original page."""
import json,re,time,sys
from pathlib import Path
import serial
ROOT=Path(__file__).resolve().parents[1]
def main():
    target=ROOT/(sys.argv[1] if len(sys.argv)>1 else 'output/requirements_audit_20261009/hub_all_pages.json')
    if target.exists():raise FileExistsError('Preserve prior evidence; choose a new output file')
    target.parent.mkdir(parents=True,exist_ok=True)
    port=serial.Serial();port.port='COM8';port.baudrate=115200;port.timeout=.1;port.dtr=False;port.rts=False;port.open()
    report={'boundary':'USB command -> authenticated watch ACK and matching page telemetry; not physical touch latency','pages':[]}
    def query(command,seconds=2.5):
        port.write((command+'\n').encode());lines=[];end=time.monotonic()+seconds
        while time.monotonic()<end:
            line=port.readline().decode('utf8','replace').strip()
            if line.startswith(('HUBINFO ','HUB ACK ','HUB INPUT ','HUB PERFORMANCE ','HUB COMMAND ')):lines.append(line)
        return lines
    def status(lines):
        values=[dict(re.findall(r'(\w+)=([^ ]+)',s)) for s in lines if s.startswith('HUBINFO ')]
        return values[-1] if values else {}
    original=0
    try:
        time.sleep(.5);before=status(query('HUBINFO',1.5));report['before']=before
        if before.get('receiver')!='1' or before.get('recording')!='0':raise RuntimeError('Live idle watch required')
        original=int(before['page'])
        for page in range(11):
            lines=query('PAGE '+str(page),2.5);lines+=query('HUBINFO',.6);s=status(lines)
            report['pages'].append({'page':page,'matched':s.get('page')==str(page) and s.get('watchpage')==str(page),'status':s,'ack_ok':any('HUB ACK result=0' in v for v in lines)})
            print('Page',page,'matched:',report['pages'][-1]['matched'])
        report['all_pages_matched']=all(p['matched'] for p in report['pages'])
    except Exception as e:report['error']=type(e).__name__
    finally:
        report['restored']=status(query('PAGE '+str(original),2.5)+query('HUBINFO',.6));port.close()
        target.write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps({'all_pages_matched':report.get('all_pages_matched',False),'restored_page':report['restored'].get('page'),'error':report.get('error')}))
if __name__=='__main__':main()
