"""Lower optical current for an ADC headroom trial; retain a reversible record."""
from pathlib import Path
from datetime import datetime,timezone
import json,re,time
from activity_export import Watch

ROOT=Path(__file__).resolve().parents[1]
device=Watch('COM15');responses=[]
def command(text,seconds=1):
    device.send(text);until=time.monotonic()+seconds;result=[]
    while time.monotonic()<until:
        line=device.serial.readline().decode('ascii','replace').strip()
        if line.startswith(('MAX30102 REG','MAXLED OK','MAXLED ERROR')):result.append(line)
    responses.extend(result);return result
def registers(lines):
    line=next(x for x in lines if x.startswith('MAX30102 REG'))
    return {reg:int(value,16) for reg,value in re.findall(r'([A-F0-9]{2})=([A-F0-9]{2})',line)}
started=datetime.now(timezone.utc)
try:
    before=registers(command('MAXINFO'))
    if before.get('0C')!=95 or before.get('0D')!=63:
        raise RuntimeError('Unexpected LED profile; leave device unchanged')
    acknowledgement=command('MAXLED 31')
    after=registers(command('MAXINFO'))
    verified=('MAXLED OK level=31' in acknowledgement and after.get('0C')==31 and after.get('0D')==31 and
              all(before.get(reg)==after.get(reg) for reg in ['08','09','0A']))
    report={'started_utc':started.isoformat(),'completed_utc':datetime.now(timezone.utc).isoformat(),
        'purpose':'Increase ADC headroom after red=95 trial produced finite BPM but no complete SpO2 window. Saturation is a hypothesis until actual optical levels are observed during renewed contact.',
        'red_before':95,'ir_before':63,'red_after':after.get('0C'),'ir_after':after.get('0D'),
        'configuration_write_verified':verified,'intentionally_persisted_settings':['led','red'],
        'baseline_restore_command':'MAXLED 63','acceptance_result':'Pending a new real-contact test',
        'raw_waveform_saved':False,'responses':responses}
    target=ROOT/'output/fr_completion_20261016'/('ppg_headroom_trial_'+started.strftime('%Y%m%dT%H%M%SZ')+'.json')
    target.write_text(json.dumps(report,indent=2),'utf8')
    print(json.dumps({'result':str(target),**report}),flush=True)
    if not verified:raise RuntimeError('Headroom trial not verified')
finally:device.close()
