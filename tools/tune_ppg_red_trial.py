"""Record a reversible red LED trial, independently of estimate acceptance."""
from pathlib import Path
from datetime import datetime,timezone
import json,re,time
from activity_export import Watch

ROOT=Path(__file__).resolve().parents[1]
device=Watch('COM15');responses=[]
def command(text,seconds=.9):
    device.send(text);until=time.monotonic()+seconds;result=[]
    while time.monotonic()<until:
        line=device.serial.readline().decode('ascii','replace').strip()
        if line.startswith(('MAX30102 REG','MAXRED OK','MAXRED ERROR')):result.append(line)
    responses.extend(result);return result
def registers(lines):
    line=next(x for x in lines if x.startswith('MAX30102 REG'))
    return {reg:int(value,16) for reg,value in re.findall(r'([A-F0-9]{2})=([A-F0-9]{2})',line)}
started=datetime.now(timezone.utc)
try:
    before=registers(command('MAXINFO'))
    if before.get('0C')!=63 or before.get('0D')!=63:
        raise RuntimeError('Unexpected LED settings; leave device unchanged')
    acknowledgement=command('MAXRED 95')
    after=registers(command('MAXINFO'))
    verified=('MAXRED OK level=95' in acknowledgement and after.get('0C')==95 and
              all(before.get(reg)==after.get(reg) for reg in ['08','09','0A','0D']))
    report={'started_utc':started.isoformat(),'completed_utc':datetime.now(timezone.utc).isoformat(),
        'purpose':'Test whether stronger red-channel illumination improves real optical signal. No estimate, quality threshold or reference value is changed.',
        'reference':'https://www.analog.com/media/en/technical-documentation/data-sheets/max30102.pdf',
        'red_led_before':63,'red_led_after':after.get('0C'),'ir_led_unchanged':after.get('0D'),
        'configuration_write_verified':verified,'intentionally_persisted_setting':'red',
        'revert_command':'MAXRED 63','acceptance_result':'Not measured; requires a new real-contact test',
        'responses':responses}
    target=ROOT/'output/fr_completion_20261016'/('ppg_red_trial_'+started.strftime('%Y%m%dT%H%M%SZ')+'.json')
    target.write_text(json.dumps(report,indent=2),'utf8')
    print(json.dumps({'result':str(target),**report}),flush=True)
    if not verified:raise RuntimeError('LED trial not verified')
finally:device.close()
