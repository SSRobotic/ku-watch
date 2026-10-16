"""Summarize one bounded real optical capture in memory; never persist raw PPG."""
from pathlib import Path
from datetime import datetime, timezone
import json, time, re
import numpy as np
from activity_export import Watch

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/fr_completion_20261016'
started=datetime.now(timezone.utc)
device=Watch('COM15')
samples=[];lines=[];complete=False
try:
    device.send('PULSETRACE')
    deadline=time.monotonic()+42
    while time.monotonic()<deadline:
        line=device.serial.readline().decode('ascii','replace').strip()
        if line.startswith('PULSETRACE START '):lines.append(line)
    device.send('PULSEGET')
    deadline=time.monotonic()+12
    while time.monotonic()<deadline:
        line=device.serial.readline().decode('ascii','replace').strip()
        match=re.fullmatch(r'PPG (\d+) (\d+) (\d+)',line)
        if match:samples.append(tuple(map(int,match.groups())))
        elif line.startswith('PULSETRACE DATA '):lines.append(line)
        elif line=='PULSETRACE END':complete=True;break
finally:device.close()

report={'started_utc':started.isoformat(),'completed_utc':datetime.now(timezone.utc).isoformat(),
        'boundary':'Actual 25 Hz FIFO trace summarized in process memory only. No raw optical waveform persisted or sent to a service. Serial dump occurs after the capture and may itself pause acquisition; it is not an acceptance window.',
        'actual_records':len(samples),'trace_headers':lines,'complete':complete,
        'raw_waveform_saved':False,'segments':[],'period_windows':[]}
if samples:
    data=np.asarray(samples,dtype=float)
    report['indices_sequential']=bool(np.array_equal(data[:,0],np.arange(len(data))))
    report['ir_below_contact_threshold']=int(np.count_nonzero(data[:,1]<10000))
    report['clipped_records']=int(np.count_nonzero((data[:,1]>=260000)|(data[:,2]>=260000)))
    for start in range(0,len(data)-99,25):
        x=data[start:start+100,1:3]
        centered=np.stack([x[:,i]-np.convolve(np.pad(x[:,i],(12,12),mode='edge'),np.ones(25)/25,mode='valid') for i in range(2)],axis=1)
        scores={}
        for lag in range(6,41):
            scores[lag]=[float(np.dot(centered[:-lag,i],centered[lag:,i])/max(1e-12,np.linalg.norm(centered[:-lag,i])*np.linalg.norm(centered[lag:,i]))) for i in range(2)]
        peaks=[lag for lag in range(7,40) if scores[lag][0]>=.85 and scores[lag][1]>=.75 and scores[lag][0]>scores[lag-1][0] and scores[lag][0]>=scores[lag+1][0]]
        lag=peaks[0] if peaks else None
        report['period_windows'].append({'start_s':start/25,'duration_s':4,'ir_red_detrended_correlation':float(np.corrcoef(centered.T)[0,1]),'fundamental_lag':lag,'period_bpm':1500/lag if lag else None,'autocorrelation_ir':scores[lag][0] if lag else None,'autocorrelation_red':scores[lag][1] if lag else None})
    for start in range(0,len(data)-124,125):
        ir=data[start:start+125,1];red=data[start:start+125,2]
        def spectral(x):
            detrended=x-np.convolve(np.pad(x,(12,12),mode='edge'),np.ones(25)/25,mode='valid')
            powers=np.abs(np.fft.rfft(detrended*np.hanning(len(x)),n=4096))**2
            frequency=np.fft.rfftfreq(4096,1/25)
            chosen=(frequency>=.65)&(frequency<=3.35)
            index=np.where(chosen)[0][int(np.argmax(powers[chosen]))]
            return float(frequency[index]*60),float(np.std(detrended))
        ih,ia=spectral(ir);rh,ra=spectral(red)
        report['segments'].append({'start_s':start/25,'duration_s':5,
            'ir_mean':float(np.mean(ir)),'red_mean':float(np.mean(red)),
            'perfusion_ir':float(np.std(ir)/np.mean(ir)),
            'perfusion_red':float(np.std(red)/np.mean(red)),
            'ir_red_correlation':float(np.corrcoef(ir,red)[0,1]),
            'ir_spectral_peak_bpm':ih,'red_spectral_peak_bpm':rh,
            'ir_detrended_rms':ia,'red_detrended_rms':ra})
target=OUT/('ppg_summary_'+started.strftime('%Y%m%dT%H%M%SZ')+'.json')
target.write_text(json.dumps(report,indent=2),encoding='utf8')
samples.clear()
print(json.dumps({'report':str(target),**report}),flush=True)
