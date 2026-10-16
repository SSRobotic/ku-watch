"""Trim actual dashboard recording; preserve source and honest observation boundary."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/(sys.argv[1] if len(sys.argv)>1 else 'output/outdoor_capture/20261016T082235185Z');OUT=ROOT/(sys.argv[2] if len(sys.argv)>2 else 'output/final_acceptance_20261016/recovery_clip');OUT.mkdir(exist_ok=True)
raw=SRC/'NodeRED_actual_outdoor.webm';dest=OUT/'NodeRED_หลังกลับออนไลน์_16ตุลา2569_60วินาที.mp4'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(p)],text=True))
assert float(probe(raw)['format']['duration'])>=65
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-n','-ss','5','-i',str(raw),'-t','60','-an','-c:v','libx264','-preset','fast','-crf','24','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],check=True)
duration=float(probe(dest)['format']['duration']);assert abs(duration-60)<.1
for offset in [0,30,59]:subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-n','-ss',str(offset),'-i',str(dest),'-frames:v','1',str(OUT/f'frame_{offset}.png')],check=True)
meta={'source':str(raw.relative_to(ROOT)),'source_sha256':digest(raw),'source_started_utc':json.loads((SRC/'status.json').read_text())['started_utc'],'source_start_s':5,'duration_s':duration,'playback_speed':1,'file':dest.name,'sha256':digest(dest),'boundary':'Actual Node-RED recording after automatic recovery and backlog drain; does not show the 10-minute outage itself or mirror the physical LCD. Detailed outage acceptance is in offline_10min/result.json. No generated values or speed change.','visual_review':'pending'}
(OUT/'manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({'video':str(dest),'duration':duration},ensure_ascii=False))
