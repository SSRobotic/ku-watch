"""Drive only the explicit diagnostic-input command; stream timestamped proof."""
import json,sys,time
from datetime import datetime,timezone
from activity_export import Watch
identity=int(sys.argv[1]);channel=sys.argv[2]
assert identity>0 and channel in ('TEMP','IAQ')
watch=Watch('COM15')
try:
    watch.serial.reset_input_buffer()
    start=time.monotonic();sent_utc=datetime.now(timezone.utc).isoformat()
    watch.send(f'ALERTTEST START {identity} {channel}')
    print(json.dumps({'kind':'host_sent','test_id':identity,'channel':channel,'utc':sent_utc,'host_epoch_ms':time.time()*1000}),flush=True)
    while time.monotonic()-start<9:
        line=watch.serial.readline().decode('ascii','replace').strip()
        if line.startswith('ALERTTEST '):
            print(json.dumps({'kind':'serial','elapsed_ms':(time.monotonic()-start)*1000,'host_epoch_ms':time.time()*1000,'text':line}),flush=True)
    watch.send('ALERTTEST STOP')
finally:watch.close()
