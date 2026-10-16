"""Summarize actual live MQTT captures separately from historical backfill."""
import argparse,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args()
observed=json.loads((root/a.input).read_text())
live=[];seen=set()
for row in observed['samples']:
    if row.get('backfill') or row['id'] in seen:continue
    seen.add(row['id']);live.append(row)
gaps=[];intervals=[];sessions=set()
for i,row in enumerate(live):
    session,sequence=row['id'].split('-');sessions.add(session)
    if not i:continue
    previous=live[i-1];prior_session,prior_sequence=previous['id'].split('-')
    intervals.append(row['at']-previous['at'])
    if session==prior_session and int(sequence,16)!=int(prior_sequence,16)+1:
        gaps.append({'before':previous['id'],'after':row['id']})
duration=(live[-1]['at']-live[0]['at'])/1000 if len(live)>1 else 0
result={'boundary':'Actual received live captures only; not Grafana DOM paint or a 24-hour result',
        'live':len(live),'observed_s':duration,'sessions':len(sessions),'sequence_gaps':gaps,
        'max_receive_gap_ms':max(intervals,default=0),'mean_receive_gap_ms':sum(intervals)/len(intervals) if intervals else None,
        'short_live_pass':duration>=60 and len(sessions)==1 and not gaps and max(intervals,default=0)<=5000}
(root/a.output).write_text(json.dumps(result,indent=2));print(json.dumps(result))
