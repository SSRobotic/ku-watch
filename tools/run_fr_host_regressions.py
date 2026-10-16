from pathlib import Path
import os
import subprocess,json,sys
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/fr_completion_20261016/host_regressions'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');OUT.mkdir(exist_ok=False,parents=True)
compiler=Path(os.environ.get('KU_ZIG',str(ROOT/'output/host_test_tools/ziglang/zig.exe')));results=[]
def run(name,args):
    p=subprocess.run([str(x) for x in args],cwd=ROOT,capture_output=True,text=True)
    (OUT/(name+'.log')).write_text(p.stdout+p.stderr,'utf8');results.append({'name':name,'passed':p.returncode==0});print(name,'PASS' if p.returncode==0 else 'FAIL',flush=True)
    if p.returncode:print((p.stdout+p.stderr)[-1400:])
    return not p.returncode
for name in ['frame_cache','alert_fixture','pulse_25hz','pulse_periodicity','alerts','watch_extensions','sensors','environment']:
    flags=['-std=c++17','-O1','-UNDEBUG','-Iinclude'];extra=[]
    if name in ['pulse_25hz','pulse_periodicity']:flags+=['-DARDUINO=10819','-Itests/host','-I.pio/libdeps/display_first/SparkFun MAX3010x Pulse and Proximity Sensor Library/src'];extra=[ROOT/'.pio/libdeps/display_first/SparkFun MAX3010x Pulse and Proximity Sensor Library/src/spo2_algorithm.cpp']
    if name=='environment':flags+=['-Itests/host','-I.pio/libdeps/display_first/bsec2/src']
    if name=='sensors':
        tiny=ROOT/'.pio/libdeps/display_first/TinyGPSPlus/src';pulse=ROOT/'.pio/libdeps/display_first/SparkFun MAX3010x Pulse and Proximity Sensor Library/src'
        flags+=['-DARDUINO=10819','-Itests/host','-I'+str(tiny),'-I'+str(pulse)];extra=[tiny/'TinyGPS++.cpp',pulse/'spo2_algorithm.cpp']
    exe=OUT/(name+'.exe')
    if run(name+'_build',[compiler,'c++',*flags,ROOT/'tests/host'/(name+'.cpp'),*extra,'-o',exe]):run(name,[exe])
run('ota_gateway',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_ota_gateway.py'])
report={'boundary':'Host-only regressions, never hardware acceptance or published telemetry','assertions_enabled':True,'compiler_flags_include':'-UNDEBUG','results':results,'passed':all(x['passed'] for x in results)}
(OUT/'report.json').write_text(json.dumps(report,indent=2),'utf8')
(OUT.parent/'latest.json').write_text(json.dumps({'report':str(OUT/'report.json'),'passed':report['passed'],'assertions_enabled':True},indent=2),'utf8')
print(json.dumps({'report':str(OUT/'report.json'),'passed':report['passed'],'assertions_enabled':True}),flush=True)
sys.exit(0 if report['passed'] else 1)
