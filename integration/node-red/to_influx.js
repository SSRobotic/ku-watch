// Node-RED Function body. Only actual, finite observations are written.
const p = msg.payload;
if (!p || typeof p !== 'object' || Array.isArray(p)) return null;
// Capture identity is part of the point's tag set. Two captures in the same
// second remain separate; replay of the same capture retains the same key.
const hasId=Object.prototype.hasOwnProperty.call(p,'sample_id');
if(hasId && (typeof p.sample_id!=='string' || !/^[a-f0-9]{8}-[a-f0-9]{8}$/i.test(p.sample_id)))return null;
const sampleId=hasId?p.sample_id.toLowerCase():null;
const trustedTime=Number.isSafeInteger(p.timestamp) && p.timestamp>=1704067200 && p.timestamp<=4102444799;
// An old capture without a trusted clock must not be assigned today's time.
if(p.backfill===true && !trustedTime) {
    node.status({fill:'yellow',shape:'ring',text:'Historical sample has no capture time'});return null;
}
const fields = [];
const numeric = ['temp','humidity','pressure','bpm','acc_x','acc_y','acc_z',
    'mag_x','mag_y','mag_z','satellites','satellites_view','gps_signal',
    'elapsed_s','distance_m','activity_id','uptime_ms','ir','red',
    'gps_age_s','gps_chars','gps_checksum_errors','wifi_rssi','heap_free',
    'storage_free','record_samples','mqtt_sent','spo2_status','spo2_quality',
    'iaq_accuracy','bsec_status'];
for (const key of numeric) {
    if (typeof p[key] === 'number' && Number.isFinite(p[key])) fields.push(key+'='+p[key]);
}
// Alert states originate in firmware after three distinct sensor readings.
// Preserve WAITING (0), including IAQ run-in; never infer normal from null.
for(const key of ['alert_temp_state','alert_iaq_state']) {
    if(Number.isInteger(p[key]) && p[key]>=0 && p[key]<=2)fields.push(key+'='+p[key]);
}
if(Number.isInteger(p.alert_mask) && p.alert_mask>=0 && p.alert_mask<=3)fields.push('alert_mask='+p.alert_mask);
if(typeof p.alert_temp_limit==='number' && Number.isFinite(p.alert_temp_limit) && p.alert_temp_limit>=-20 && p.alert_temp_limit<=80)
    fields.push('alert_temp_limit='+p.alert_temp_limit);
if(typeof p.alert_iaq_limit==='number' && Number.isFinite(p.alert_iaq_limit) && p.alert_iaq_limit>=10 && p.alert_iaq_limit<=500)
    fields.push('alert_iaq_limit='+p.alert_iaq_limit);
// New estimates are only persisted with their readiness flags and valid ranges.
// Missing/invalid readings stay null in queries, never substituted with zero.
const finiteRange = (key, lo, hi) => typeof p[key] === 'number'
    && Number.isFinite(p[key]) && p[key]>=lo && p[key]<=hi;
if (p.spo2_valid === true && p.pulse_live === true && p.finger === true
    && finiteRange('spo2',70,100)) fields.push('spo2='+p.spo2);
if (p.env_live === true && finiteRange('gas_ohms',1,1e9)) fields.push('gas_ohms='+p.gas_ohms);
if (p.iaq_valid === true && p.env_live === true && p.iaq_stable === true && p.iaq_run_in === true
    && finiteRange('iaq_accuracy',1,3) && finiteRange('iaq',0,500)) fields.push('iaq='+p.iaq);
if (p.battery_valid === true && p.ina226_detected === true
    && finiteRange('battery_voltage',2.5,4.25) && finiteRange('battery_percent',0,100)) {
    fields.push('battery_voltage='+p.battery_voltage,'battery_percent='+p.battery_percent);
    // Firmware owns hysteresis. Only persist a ready state with a valid reading.
    if(p.alert_battery_state===1 || p.alert_battery_state===2)
        fields.push('alert_battery_state='+p.alert_battery_state,'battery_low='+(p.alert_battery_state===2));
}
if(p.alert_battery_state===0)fields.push('alert_battery_state=0');
if(typeof p.firmware==='string' && /^\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(p.firmware))
    fields.push('firmware="'+p.firmware+'"');
if(p.current_valid===true && finiteRange('battery_current_ma',-100000,100000) && finiteRange('battery_power_mw',-500000,500000))
    fields.push('battery_current_ma='+p.battery_current_ma,'battery_power_mw='+p.battery_power_mw);
if(finiteRange('heading',0,360))fields.push('heading='+p.heading);
if (p.gps_fix === true && typeof p.latitude === 'number' && typeof p.longitude === 'number'
    && Number.isFinite(p.latitude) && Number.isFinite(p.longitude)
    && Math.abs(p.latitude)<=90 && Math.abs(p.longitude)<=180) {
    for (const key of ['latitude','longitude','altitude','speed_kmh','gps_hdop']) {
        if (typeof p[key] === 'number' && Number.isFinite(p[key])) fields.push(key+'='+p[key]);
    }
}
for (const key of ['gps_fix','recording','finger','pulse_live','env_live','acc_live','mag_live','gps_data',
    'spo2_valid','iaq_valid','iaq_stable','iaq_run_in','battery_valid','ina226_detected']) {
    if (typeof p[key] === 'boolean') fields.push(key+'='+p[key]);
}
if (!fields.length) return null;
const token = env.get('KU_INFLUX_TOKEN');
if (!token) { node.status({fill:'yellow',shape:'ring',text:'Set Influx token'}); return null; }
const device = typeof p.device==='string' && /^[a-zA-Z0-9_-]{1,64}$/.test(p.device) ? p.device : 'ku-watch';
let line = 'ku_watch,device='+device+(sampleId?',sample_id='+sampleId:'')+' '+fields.join(',');
// When the watch has no trusted clock, let InfluxDB timestamp reception.
if (trustedTime) line+=' '+p.timestamp;
return {payload:line, url:'http://127.0.0.1:8871/enqueue',
    headers:{'X-KU-Write-Url':env.get('KU_INFLUX_URL')+'/api/v3/write_lp?db='+encodeURIComponent(env.get('KU_INFLUX_DATABASE')||'iot')+'&precision=second',
        'Content-Type':'text/plain'}};
