"""Read only real display/conversion counters; no raw optical or location samples."""
import json,sys,threading,time
from activity_export import Watch
stop=threading.Event();lock=threading.Lock()
def listen():
    for line in sys.stdin:
        if line.strip()=='STOP':stop.set();break
threading.Thread(target=listen,daemon=True).start()
def read(port,device):
    watch=Watch(port);due=0;last_second=-1
    try:
        start=time.monotonic()
        while not stop.is_set():
            elapsed=time.monotonic()-start
            if elapsed>=due:
                if device=='watch':
                    watch.send('RATEINFO')
                    if int(elapsed)!=last_second:
                        watch.send('SENSORINFO');watch.send('SCREENINFO');last_second=int(elapsed)
                else:watch.send('HUBINFO')
                due=elapsed+(.5 if device=='watch' else 1)
            line=watch.serial.readline().decode('ascii','replace').strip()
            permitted=('RATES ','PPGQUALITY ','SCREEN ') if device=='watch' else ('HUBINFO ',)
            if line.startswith(permitted):
                with lock:print(json.dumps({'device':device,'line':line}),flush=True)
    except Exception as error:
        with lock:print(json.dumps({'device':device,'error':type(error).__name__}),flush=True)
        stop.set()
    finally:watch.close()
threads=[threading.Thread(target=read,args=('COM15','watch')),threading.Thread(target=read,args=('COM8','hub'))]
for thread in threads:thread.start()
for thread in threads:thread.join()
