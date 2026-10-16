"""One command for offline regressions. Does not flash or publish telemetry."""
from pathlib import Path
import argparse,json,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--compiler',type=Path,default=ROOT/'output/host_test_tools/ziglang/zig.exe');p.add_argument('--node',default=shutil.which('node'));a=p.parse_args()
    if not a.compiler.is_file():p.error('Provide --compiler pointing to a Zig executable (zig c++).')
    if not a.node:p.error('Node.js is required for dashboard checks.')
    out=ROOT/'output/acceptance';out.mkdir(parents=True,exist_ok=True);results=[]
    def run(name,command):
        began=time.monotonic();r=subprocess.run([str(v) for v in command],cwd=ROOT,capture_output=True,text=True)
        (out/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf8')
        results.append({'name':name,'passed':r.returncode==0,'seconds':round(time.monotonic()-began,2)})
        print(name, 'PASS' if r.returncode==0 else 'FAIL',flush=True)
        return r.returncode==0
    standard=['alerts','alert_acceptance','battery_alert','clock','hub','hub_csv','map_selection','robot','telemetry','telemetry_window','watch_extensions','maps']
    for name in standard+['hub_rtc','telemetry_store','environment','sensors']:
        exe=out/(name+'.exe');flags=['-std=c++17','-O1','-Iinclude'];extra=[]
        if name=='hub_rtc':flags+=['-Itests/host/rtc_fake']
        if name=='telemetry_store':flags+=['-Itests/host/fake_flash']
        if name=='environment':flags+=['-Itests/host','-I.pio/libdeps/display_first/bsec2/src']
        if name=='sensors':
            tiny=ROOT/'.pio/libdeps/display_first/TinyGPSPlus/src'
            pulse=ROOT/'.pio/libdeps/display_first/SparkFun MAX3010x Pulse and Proximity Sensor Library/src'
            flags+=['-DARDUINO=10819','-Itests/host','-I'+str(tiny),'-I'+str(pulse)]
            extra=[tiny/'TinyGPS++.cpp',pulse/'spo2_algorithm.cpp']
        if run(name+'_build',[a.compiler,'c++',*flags,ROOT/'tests/host'/(name+'.cpp'),*extra,'-o',exe]):run(name,[exe])
    run('python',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py'])
    for name in ['test_influx_flow','test_alert_dashboard','test_grafana_frame_match','test_telemetry_audit_coverage']:run(name,[a.node,ROOT/'tests'/(name+'.cjs')])
    report={'boundary':'Offline production-code regressions; fixtures never published to devices or databases','results':results,'passed':all(r['passed'] for r in results)}
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('All checks passed:',report['passed']);return 0 if report['passed'] else 1
if __name__=='__main__':sys.exit(main())
