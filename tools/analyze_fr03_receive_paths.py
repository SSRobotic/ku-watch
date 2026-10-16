"""Compare actual source and receive intervals; never reinterpret an audit pass."""
from pathlib import Path
from datetime import datetime, timezone
import json

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'output/fr_completion_20261016'
results=[]
for name in ['mqtt_2.0.11_5min.json','mqtt_2.0.12_5min_monotonic.json','mqtt_2.0.12_normal_5min.json']:
    p=json.loads((RUN/name).read_text())
    rows=p['samples']
    gaps=[rows[i]['receive_ms']-rows[i-1]['receive_ms'] for i in range(1,len(rows))]
    source=[rows[i]['uptime_ms']-rows[i-1]['uptime_ms'] for i in range(1,len(rows))]
    index=max(range(len(gaps)),key=gaps.__getitem__)+1
    results.append({'evidence_file':name,'audit_result_unchanged':p['full_requirement_pass'],
                    'unique_live':p['live'],'sequence_gaps':p['sequence_gaps'],
                    'duplicates':p['duplicates'],'disconnects':p['disconnects'],
                    'mean_source_interval_ms':sum(source)/len(source),
                    'max_source_interval_ms':max(source),
                    'worst_receive_interval':{
                        'receive_gap_ms':gaps[index-1],
                        'source_gap_ms':source[index-1],
                        'before_id':rows[index-1]['id'],'after_id':rows[index]['id'],
                        'following_receive_intervals_ms':gaps[index:index+8]}})
report={'created_utc':datetime.now(timezone.utc).isoformat(),
        'method':'Read-only analysis of immutable observations. No new pass criteria.',
        'observations':results,
        'network_path_test':{'attempted_pc_profile':'previous_saved_home_profile',
            'result':'Profile was not available, including after a fresh scan. PC remained connected to SS.',
            'watch_network_changed':False,'receive_path_changed':False},
        'interpretation':'A receive interval longer than the corresponding source interval shows post-capture delay. These counters alone do not distinguish device queue, LTE, broker and PC receive scheduling.'}
(RUN/'mqtt_path_diagnostics.public.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
