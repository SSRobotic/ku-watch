"""Observe FR-01 at USB, separately from MQTT transport; no raw PPG is saved."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, json, math, re, threading, time
from activity_export import Watch

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--seconds',type=float,default=65)
parser.add_argument('--require-valid',action='store_true')
parser.add_argument('--expected-version',default='2.0.15')
args=parser.parse_args()
start_utc=datetime.now(timezone.utc)
OUT=ROOT/'output/fr_completion_20261016/fr01_local_runs'/start_utc.strftime('%Y%m%dT%H%M%SZ')
OUT.mkdir(parents=True,exist_ok=False)
plan={'started_utc':start_utc.isoformat(),'seconds':args.seconds,
      'expected_firmware':args.expected_version,
      'display_update_method':'Version 2.0.15 compares each eight-row strip byte-for-byte with the previously sent PSRAM image and sends changed strips. A completed update means all pixels match the current rendered model; unchanged strips need no SPI write. Reset/page change/test forces a full frame.',
      'frame_interval_proof':'For a faster display, several frames may finish between USB polls. The time between the bounding completed-frame timestamps is a conservative upper bound for every enclosed individual interval. Every such bound must remain <=1000 ms; the threshold is unchanged.',
      'rates_poll_s':.1,'quality_and_screen_poll_s':.4,
      'scope':'FR-01 display and sensor conversions measured at USB. MQTT receive latency is separately assessed under FR-03. No network behavior or acceptance thresholds are changed.',
      'mode':'one_minute_valid_estimates' if args.require_valid else 'cadence_only_while_user_rests',
      'full_acceptance_requires':'A continuous real 60 s window with finite BPM and displayed SpO2, quality status 3, no missed quality windows, matching healthy hub flags, no FIFO reset, pulse >=20 Hz, motion/display >=1 Hz and nominal BSEC 3 s conversions. No raw PPG persisted.'}
(OUT/'plan.json').write_text(json.dumps(plan,indent=2),'utf8')
rows=[];errors=[];lock=threading.Lock();stop=threading.Event();began=time.monotonic()
journal=(OUT/'observations.jsonl').open('x',encoding='utf8',buffering=1)
levels={'observations':0,'ir_min':None,'ir_max':None,'red_min':None,'red_max':None,
        'ir_clipped':0,'red_clipped':0,'raw_level_time_series_saved':False}

def parsed(line):
    out={}
    for k,v in re.findall(r'(\w+)=([^ ]+)',line):
        try:
            number=float(v);out[k]=int(number) if math.isfinite(number) and number.is_integer() else number if math.isfinite(number) else None
        except ValueError:out[k]=v
    return out

def reader(port,role):
    device=None
    try:
        device=Watch(port);due=net_due=rate_due=0;pending=bytearray()
        if role=='watch':device.send('MAXINFO');device.send('OTAINFO')
        while not stop.is_set():
            elapsed=time.monotonic()-began
            if role=='watch' and elapsed>=rate_due:
                device.send('RATEINFO');rate_due=elapsed+.1
            if elapsed>=due:
                for command in (['SENSORINFO','SCREENINFO'] if role=='watch' else ['HUBINFO']):device.send(command)
                due=elapsed+.4
                if role=='watch' and elapsed>=net_due:device.send('NETINFO');net_due=elapsed+5
            # Serial.readline may time out in the middle of a valid response.
            # Keep fragments until a newline; never parse a truncated RATES row.
            raw=device.serial.readline()
            if not raw:continue
            pending.extend(raw)
            if len(pending)>16384:raise RuntimeError('Serial response exceeded bounded line buffer')
            if not pending.endswith(b'\n'):continue
            line=pending.decode('ascii','replace').strip();pending.clear()
            if role=='watch' and line.startswith('MAX30102 LIVE '):
                level=re.search(r'IR=(\d+) RED=(\d+)',line)
                if level:
                    with lock:
                        levels['observations']+=1
                        for channel,value in zip(['ir','red'],map(int,level.groups())):
                            for bound,fn in [('min',min),('max',max)]:
                                key=channel+'_'+bound
                                levels[key]=value if levels[key] is None else fn(levels[key],value)
                            levels[channel+'_clipped']+=int(value>=260000)
                continue
            allowed=('RATES ','PPGQUALITY ','SENSORS ','SCREEN ','OTA ','MAX30102 REG','NETWORK ','QUEUE ') if role=='watch' else ('HUBINFO ','HUB CLOCK ')
            if line.startswith(allowed):
                row={'role':role,'host_s':time.monotonic()-began,'line':line,'values':parsed(line)}
                with lock:
                    rows.append(row)
                    journal.write(json.dumps(row,allow_nan=False)+'\n')
    except Exception as e:
        with lock:errors.append({'role':role,'error':type(e).__name__})
        stop.set()
    finally:
        if device:device.close()

threads=[threading.Thread(target=reader,args=('COM15','watch')),threading.Thread(target=reader,args=('COM8','hub'))]
for thread in threads:thread.start()
print(json.dumps({'started':True,'plan':str(OUT/'plan.json'),'requires_finger':args.require_valid}),flush=True)
while time.monotonic()-began<args.seconds and not stop.is_set():time.sleep(.1)
stop.set()
for thread in threads:thread.join()
journal.close()

rows.sort(key=lambda r:r['host_s'])
rates=[r for r in rows if r['line'].startswith('RATES ')]
qualities=[r for r in rows if r['line'].startswith('PPGQUALITY ')]
screens=[r for r in rows if r['line'].startswith('SCREEN page=')]
hubs=[r for r in rows if r['line'].startswith('HUBINFO ')]
def assess_cadence(observations):
    required={'uptime_ms','pulse_samples','pulse_dropped','env_sequence','motion_reads','frames','paint_ms'}
    malformed_rates=[r for r in observations if r['line'].startswith('RATES ') and not required<=r['values'].keys()]
    selected=[r for r in observations if r['line'].startswith('RATES ') and required<=r['values'].keys()]
    chosen_screens=[r for r in observations if r['line'].startswith('SCREEN page=')]
    chosen_hubs=[r for r in observations if r['line'].startswith('HUBINFO ')]
    if len(selected)<2:return {},False
    a,b=selected[0]['values'],selected[-1]['values'];span=(b['uptime_ms']-a['uptime_ms'])/1000
    if span<=0:return {},False
    observed_frames={r['values']['frames']:r['values']['paint_ms'] for r in selected}
    ordered=sorted(observed_frames.items())
    gaps=[ordered[i][1]-ordered[i-1][1] for i in range(1,len(ordered))]
    unknown_frames=sum(max(0,ordered[i][0]-ordered[i-1][0]-1) for i in range(1,len(ordered)))
    metrics={'source_span_s':span,'incomplete_rate_responses':len(malformed_rates),'pulse_sample_hz':(b['pulse_samples']-a['pulse_samples'])/span,
             'fifo_resets':b['pulse_dropped']-a['pulse_dropped'],
             'environment_conversions':b['env_sequence']-a['env_sequence'],
             'motion_read_hz':(b['motion_reads']-a['motion_reads'])/span,
             'watch_completed_frame_hz':(b['frames']-a['frames'])/span,
             'largest_observed_frame_interval_ms':max(gaps,default=0),
             'frames_not_individually_observed':unknown_frames,
             'all_watch_health_page':len(chosen_screens)>=60 and all(r['values']['page']==4 and r['values']['painted']==4 and r['values']['body_pixels']>0 for r in chosen_screens),
             'all_hub_health_page':len(chosen_hubs)>=60 and all(r['values']['page']==3 and r['values']['watchpage']==3 and r['values']['receiver']==1 and r['values']['ready']==1 for r in chosen_hubs),
             'bsec_errors':sum(1 for r in observations if r['line'].startswith('SENSORS ') and r['values'].get('bsec',0)<0)}
    cadence=bool(not errors and not malformed_rates and span>=60 and metrics['pulse_sample_hz']>=20 and metrics['fifo_resets']==0 and
                 metrics['environment_conversions']>=math.floor(span/3)-1 and metrics['motion_read_hz']>=1 and
                 metrics['watch_completed_frame_hz']>=1 and metrics['largest_observed_frame_interval_ms']<=1000 and
                 metrics['all_watch_health_page'] and metrics['all_hub_health_page'] and metrics['bsec_errors']==0)
    return metrics,cadence

metrics,cadence=assess_cadence(rows)

# Continuous estimate coverage is assessed without using MQTT packet arrival.
latest={};candidate_start=None;longest=0;missed_windows=0;last_window=None;start_index=None;best=None
for index,row in enumerate(rows):
    line=row['line'];v=row['values'];kind=None
    if line.startswith('PPGQUALITY '):kind='q'
    elif line.startswith('SENSORS '):kind='s'
    elif line.startswith('HUBINFO '):kind='h'
    if not kind:continue
    latest[kind]=row
    fresh=all(k in latest and row['host_s']-latest[k]['host_s']<=1.6 for k in ['q','s','h'])
    good=False
    if fresh:
        q,s,h=[latest[k]['values'] for k in ['q','s','h']]
        good=(q.get('good_status')==3 and q.get('signal')==1 and q.get('rhythm')==1 and q.get('oxygen_valid')==1 and
              q.get('bpm') is not None and s.get('spo2') is not None and s.get('status')==3 and
              s.get('iaq') is not None and s.get('bsec',-1)>=0 and
              h.get('page')==3 and h.get('watchpage')==3 and h.get('receiver')==1 and h.get('ready')==1 and (h.get('flags',0)&28)==28)
    if kind=='q':
        window=v.get('windows')
        if last_window is not None and window>last_window+1:
            missed_windows+=window-last_window-1;good=False
        last_window=window
    if not good:candidate_start=None;start_index=None;continue
    if candidate_start is None:candidate_start=row['host_s'];start_index=index
    duration=row['host_s']-candidate_start
    if duration>longest:longest=duration;best={'first_row':start_index,'last_row':index,'host_duration_s':duration}

valid_count=sum(1 for r in qualities if r['values'].get('good_status')==3 and r['values'].get('bpm') is not None)
report={**plan,'completed_utc':datetime.now(timezone.utc).isoformat(),'metrics':metrics,'cadence_pass':cadence,
        'quality_observations':len(qualities),'valid_quality_observations':valid_count,
        'longest_observed_valid_span_s':longest,'unobserved_quality_windows':missed_windows,
        'best_observed_valid_span':best,'fr01_full_pass':False,'errors':errors,
        'optical_dc_level_summary':levels,'observations':rows}
firmware_rows=[r for r in rows if r['line'].startswith('OTA version=')]
report['firmware_identity_verified']=bool(firmware_rows) and all(r['values'].get('version')==args.expected_version for r in firmware_rows)
if args.require_valid and best and longest>=61.5:
    window=rows[best['first_row']:best['last_row']+1]
    window_metrics,window_cadence=assess_cadence(window)
    q=[r for r in window if r['line'].startswith('PPGQUALITY ')]
    seen_windows=sorted(set(r['values']['windows'] for r in q))
    no_skipped_windows=bool(seen_windows) and all(b-a==1 for a,b in zip(seen_windows,seen_windows[1:]))
    all_estimates_valid=bool(q) and all(r['values'].get('good_status')==3 and r['values'].get('bpm') is not None for r in q)
    report['accepted_candidate_metrics']={**window_metrics,'host_valid_span_s':longest,
        'all_observed_estimates_valid':all_estimates_valid,'no_skipped_quality_windows':no_skipped_windows}
    report['fr01_full_pass']=bool(window_cadence and all_estimates_valid and no_skipped_windows and report['firmware_identity_verified'])
(OUT/'result.json').write_text(json.dumps(report,indent=2,allow_nan=False),'utf8')
(ROOT/'output/fr_completion_20261016/fr01_local_latest.json').write_text(json.dumps({
    'result':str(OUT/'result.json'),'completed_utc':report['completed_utc'],'mode':plan['mode'],
    'cadence_pass':cadence,'fr01_full_pass':report['fr01_full_pass'],
    'longest_observed_valid_span_s':longest},indent=2),'utf8')
print(json.dumps({'result':str(OUT/'result.json'),'metrics':metrics,'cadence_pass':cadence,
                  'longest_valid_s':longest,'fr01_full_pass':report['fr01_full_pass'],'errors':errors}),flush=True)
