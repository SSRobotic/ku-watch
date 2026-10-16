from pathlib import Path
root=Path(__file__).resolve().parents[1]
names=['accumulated_soak.cjs','capture_sensor_comparison.cjs','observe_outdoor_link.cjs','observe_replay.cjs','requirements_sensor_audit.cjs','soak_audit.cjs','requirements_grafana_latency.cjs','requirements_mqtt_audit.cjs','test_cloud_connection.cjs','verify_capture_storage.cjs']
changed=[]
for n in names:
 p=root/'tools'/n;s=p.read_text(encoding='utf8')
 if "'ku_watch/live'" not in s:continue
 s=s.replace("'ku_watch/live/status'","TELEMETRY_TOPIC+'/status'").replace("'ku_watch/live'",'TELEMETRY_TOPIC')
 p.write_text("const TELEMETRY_TOPIC = require('./mqtt_topic.cjs').topic;\n"+s,encoding='utf8');changed.append(n)
print({'observers_updated':changed})
