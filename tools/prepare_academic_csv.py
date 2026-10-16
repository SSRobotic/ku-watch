from pathlib import Path
import csv,json
ROOT=Path(__file__).resolve().parents[1];source=ROOT/'output/presentation_media_20261016/current_sd_export/env_1792135219_2f3b6084.csv'
with source.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);rows=list(reader);columns=reader.fieldnames
print(json.dumps({'columns':columns,'rows':len(rows),'first':rows[0]},ensure_ascii=False))
selected=[x for x in ['rtc_utc','temperature_c','humidity_pct','pressure_hpa','bpm_estimate','iaq','battery_v'] if x in columns]
if len(selected)<5:selected=columns[:7]
out=ROOT/'output/ppt_academic_20261016/build/csv_excerpt.json';out.write_text(json.dumps({'source':str(source.relative_to(ROOT)),'columns':selected,'rows':[[r[c] for c in selected] for r in rows[:8]],'total_rows':len(rows),'total_columns':len(columns)},ensure_ascii=False,indent=2),encoding='utf8')
