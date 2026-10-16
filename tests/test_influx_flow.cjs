// Validate actual Node-RED function body without sending any synthetic data.
const fs=require('fs'),assert=require('assert');
const source=fs.readFileSync('integration/node-red/to_influx.js','utf8');
const run=new Function('msg','env','node','flow',source);
const env={get:k=>({KU_INFLUX_TOKEN:'TEST_ONLY',KU_INFLUX_URL:'http://127.0.0.1:8181',KU_INFLUX_DATABASE:'iot'})[k]};
const call=p=>run({payload:p},env,{status:()=>{}},{get:()=>0});
assert.equal(call(null),null);
assert.equal(call({temp:null,bpm:null}),null);
assert.equal(call({temp:'31.0',bpm:'',acc_x:NaN}),null);
let result=call({temp:30.25,bpm:null,gps_fix:false,latitude:13.1,longitude:100.2,recording:true,timestamp:1790123456});
assert.equal(result.payload,'ku_watch,device=ku-watch temp=30.25,gps_fix=false,recording=true 1790123456');
assert(!result.payload.includes('latitude'));
assert.equal(result.url,'http://127.0.0.1:8871/enqueue');
assert(result.headers['X-KU-Write-Url'].endsWith('/api/v3/write_lp?db=iot&precision=second'));
assert.equal(result.headers.Authorization,undefined);
result=call({bpm:78,gps_fix:true,latitude:0,longitude:0,altitude:2.7,speed_kmh:0,device:'watch_1',timestamp:null});
assert(result.payload.includes('latitude=0,longitude=0,altitude=2.7,speed_kmh=0'));
assert(result.payload.endsWith('gps_fix=true'));
assert(!call({gps_fix:true,latitude:91,longitude:100}).payload.includes('latitude'));
assert(!call({gps_fix:false,latitude:0,longitude:0}).payload.includes('latitude'));
assert(!call({temp:Infinity,gps_fix:false}).payload.includes('temp='));
assert(call({temp:2,device:'bad,tag=hi'}).payload.startsWith('ku_watch,device=ku-watch '));
assert.equal(run({payload:{temp:20}},{get:()=>''},{status:()=>{}},{get:()=>0}),null);
assert(run({payload:{temp:20}},env,{status:()=>{}},{get:()=>Date.now()+30000}).payload.includes('temp=20'));
result=call({ir:145632,red:85234,finger:true,pulse_live:true,env_live:true,acc_live:false,mag_live:true,gps_data:true,gps_fix:false,gps_hdop:99,gps_chars:12345,gps_age_s:null,wifi_rssi:-58,heap_free:94000,storage_free:700000,record_samples:12,mqtt_sent:500});
for(const field of ['ir=145632','red=85234','finger=true','acc_live=false','gps_data=true','wifi_rssi=-58','record_samples=12','mqtt_sent=500']) assert(result.payload.includes(field));
assert(!result.payload.includes('gps_hdop'));
assert(!result.payload.includes('gps_age_s'));
assert(call({gps_fix:true,latitude:0,longitude:0,gps_hdop:1.2}).payload.includes('gps_hdop=1.2'));
assert.equal(call({ir:null,red:Infinity,wifi_rssi:'-40',finger:'true'}),null);
result=call({spo2:98,spo2_valid:true,pulse_live:true,finger:true,spo2_quality:.97,spo2_status:3,
    env_live:true,gas_ohms:85000,iaq:42,iaq_valid:true,iaq_stable:true,iaq_run_in:true,iaq_accuracy:2,
    battery_voltage:3.8,battery_percent:50,battery_valid:true,ina226_detected:true});
for(const field of ['spo2=98','gas_ohms=85000','iaq=42','battery_voltage=3.8','battery_percent=50','iaq_valid=true']) assert(result.payload.includes(field));
result=call({spo2:98,spo2_valid:false,pulse_live:true,finger:true,iaq:42,iaq_valid:false,
    battery_voltage:3.8,battery_percent:50,battery_valid:false,ina226_detected:true});
for(const field of ['spo2=','iaq=','battery_voltage=','battery_percent=']) assert(!result.payload.includes(field));
for(const value of [null,NaN,Infinity,101,69,'98']) {
    assert(!call({spo2:value,spo2_valid:true,pulse_live:true,finger:true}).payload.includes('spo2='));
}
assert(!call({spo2:98,spo2_valid:true,pulse_live:true,finger:false}).payload.includes('spo2='));
assert(!call({iaq:25,iaq_valid:true,env_live:true,iaq_stable:true,iaq_run_in:false,iaq_accuracy:2}).payload.includes('iaq='));
assert(!call({iaq:25,iaq_valid:true,env_live:true,iaq_stable:true,iaq_run_in:true,iaq_accuracy:0}).payload.includes('iaq='));
assert(!call({iaq:501,iaq_valid:true,env_live:true,iaq_stable:true,iaq_run_in:true,iaq_accuracy:3}).payload.includes('iaq='));
assert(call({iaq:0,iaq_valid:true,env_live:true,iaq_stable:true,iaq_run_in:true,iaq_accuracy:3}).payload.includes('iaq=0,'));
assert(!call({battery_voltage:5,battery_percent:100,battery_valid:true,ina226_detected:true}).payload.includes('battery_voltage='));
assert(!call({battery_voltage:3.8,battery_percent:50,battery_valid:true,ina226_detected:false}).payload.includes('battery_percent='));
assert(call({battery_voltage:3.3,battery_percent:0,battery_valid:true,ina226_detected:true}).payload.includes('battery_percent=0,'));
console.log('Influx flow validation passed, including SpO2/IAQ/battery readiness and invalid values; no data transmitted.');
const route=new Function('msg',fs.readFileSync('integration/node-red/route_telemetry.js','utf8'));
let capture={payload:{temp:31,timestamp:1790123456,backfill:true}};
assert.deepEqual(route(capture),[capture,null]);
assert(call(capture.payload).payload.endsWith(' 1790123456'));
assert.equal(call({temp:31,timestamp:null,backfill:true}),null);
assert.equal(call({temp:31,timestamp:'1790123456',backfill:true}),null);
assert.deepEqual(route({payload:{temp:31,backfill:false}}),[{payload:{temp:31,backfill:false}},{payload:{temp:31,backfill:false}}]);
assert.equal(route({payload:null}),null);
console.log('Backfill capture time preserved; historical samples excluded from live gauges; unclocked history rejected.');
result=call({alert_temp_state:2,alert_iaq_state:0,alert_mask:1,alert_temp_limit:35,alert_iaq_limit:150,timestamp:1790123456});
for(const field of ['alert_temp_state=2','alert_iaq_state=0','alert_mask=1','alert_temp_limit=35','alert_iaq_limit=150'])assert(result.payload.includes(field));
for(const bad of [null,NaN,Infinity,-1,3,2.1,'2'])assert.equal(call({alert_temp_state:bad}),null);
assert.equal(call({alert_mask:4,alert_temp_limit:81,alert_iaq_limit:501}),null);
console.log('Environmental alert states/limits validated; no synthetic data transmitted.');
assert(call({firmware:'2.0.1'}).payload.includes('firmware="2.0.1"'));
for(const firmware of ['2.0.1"\\bad','bad',null])assert.equal(call({firmware}),null);
assert.equal(call({alert_battery_state:2}),null); // no valid observation
let battery={battery_voltage:3.6,battery_percent:20,battery_valid:true,ina226_detected:true};
assert(call({...battery,alert_battery_state:2}).payload.includes('battery_low=true'));
assert(call({...battery,alert_battery_state:1}).payload.includes('battery_low=false'));
assert(!call({...battery,alert_battery_state:3}).payload.includes('alert_battery_state='));
assert(call({alert_battery_state:0}).payload.includes('alert_battery_state=0'));
console.log('Battery readiness/hysteresis state and safe firmware fields validated.');
const observation={temp:30,timestamp:1790123456,device:'watch_1'};
const first=call({...observation,sample_id:'ABCD1234-00000001'});
const second=call({...observation,sample_id:'abcd1234-00000002'});
const nextBoot=call({...observation,sample_id:'abcd5678-00000001'});
const replay=call({...observation,sample_id:'abcd1234-00000001',backfill:true});
assert(first.payload.includes(',sample_id=abcd1234-00000001 '));
assert.equal(first.payload,replay.payload);
assert.notEqual(first.payload,second.payload);
assert.notEqual(first.payload,nextBoot.payload);
for(const id of [null,1,'bad,tag=value','13579bdf-00000001\n','13579bdf-000000001'])
    assert.equal(call({...observation,sample_id:id}),null);
console.log('Same-second captures and boots have separate keys; replay is idempotent and invalid identities are rejected.');
