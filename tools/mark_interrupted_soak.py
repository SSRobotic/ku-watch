"""Mark a stale audit interrupted only after verifying its observer is gone."""
from pathlib import Path
import argparse,ctypes,json,time
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--reason',default='observer process absent when checked after restart, no 24-hour result established');a=p.parse_args()
file=ROOT/'output/soak_audit/status.json';report=json.loads(file.read_text())
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.OpenProcess.restype=ctypes.c_void_p
handle=kernel.OpenProcess(0x1000,False,report['pid'])
if handle:
    kernel.CloseHandle.argtypes=[ctypes.c_void_p];kernel.CloseHandle(handle)
    raise RuntimeError('Existing PID is present; inspect its process before marking interrupted')
if report.get('status')=='running':
    report['status']='interrupted';report['continuity_pass']=False
    report['boundary']+='; '+a.reason
    report['interruption_checked_utc']=time.time()
    file.write_text(json.dumps(report,indent=2))
print(json.dumps({k:report[k] for k in ['status','samples','observed_hours','continuity_pass']}))
