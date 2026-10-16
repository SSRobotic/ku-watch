const TELEMETRY_TOPIC = require('./mqtt_topic.cjs').topic;
// Read actual telemetry; store readiness and timing, never wearer coordinates.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {performance}=require('node:perf_hooks');
const mqtt=require(path.join(process.env.APPDATA,'npm/node_modules/node-red/node_modules/mqtt'));
const root=path.join(__dirname,'..'),cfg=JSON.parse(fs.readFileSync(path.join(root,'config/cloud.local.json')));
const seconds=65,output=process.argv[2]||'output/requirements_audit_20261009/sensors_65s.json',keys=['env_live','pulse_live','acc_live','mag_live','battery_valid','ina226_detected','iaq_valid','spo2_valid','finger','current_valid','gps_fix'];
if(fs.existsSync(path.join(root,output)))throw Error('Preserve earlier sensor evidence; choose a new path');
const report={boundary:'Real MQTT readiness over 65 seconds; does not measure optical accuracy or conversion cadence',duration_s:seconds,live:0,malformed:0,disconnects:0,sessions:[],versions:[],readiness:Object.fromEntries(keys.map(k=>[k,{true:0,false:0,missing:0}])),bsec_errors:0,invalid_env:0,samples:[]};
let started=0,timer,done=false;const seen=new Set();
const client=mqtt.connect('mqtts://'+cfg.host+':8883',{username:cfg.reader_user,password:cfg.reader_password,clientId:'ku-sensor-audit-'+crypto.randomBytes(6).toString('hex'),rejectUnauthorized:true,reconnectPeriod:0});
function finish(error){if(done)return;done=true;clearTimeout(timer);clearTimeout(deadline);
 report.observed_s=started?(performance.now()-started)/1000:0;report.completed_utc=new Date().toISOString();report.timing_clock='monotonic performance.now';
 const intervals=report.samples.slice(1).map((s,i)=>s.received_ms-report.samples[i].received_ms);
 report.mean_interval_ms=intervals.length?intervals.reduce((a,b)=>a+b,0)/intervals.length:null;
 report.max_interval_ms=intervals.length?Math.max(...intervals):null;
 report.transport_pass=!error&&report.observed_s>=seconds&&report.live>=60&&!report.disconnects&&!report.malformed;
 report.required_sensors_live=keys.slice(0,6).every(k=>report.readiness[k].true>0);
 if(error)report.error=error;
 fs.writeFileSync(path.join(root,output),JSON.stringify(report,null,2),{flag:'wx'});
 console.log(JSON.stringify({...report,samples:undefined}));client.end(true);process.exitCode=error?1:0;}
const deadline=setTimeout(()=>finish('MQTT unavailable'),80000);
client.on('connect',()=>client.subscribe(TELEMETRY_TOPIC,{qos:1},err=>{if(err)return finish('Subscription rejected');started=performance.now();report.started_utc=new Date().toISOString();timer=setTimeout(()=>finish(),seconds*1000);console.log('65-second actual sensor audit started.');}));
client.on('error',()=>finish('MQTT connection failed'));
client.on('offline',()=>{++report.disconnects;});
client.on('message',(_,raw,packet)=>{if(!started||packet.retain)return;let p;try{p=JSON.parse(raw.toString());}catch{++report.malformed;return;}
 if(p.backfill||seen.has(p.sample_id))return;if(!/^[a-f0-9]{8}-[a-f0-9]{8}$/i.test(p.sample_id||'')){++report.malformed;return;}
 seen.add(p.sample_id);++report.live;
 for(const k of keys)++report.readiness[k][p[k]===true?'true':p[k]===false?'false':'missing'];
 if(Number(p.bsec_status)<0)++report.bsec_errors;
 if(p.env_live&&![p.temp,p.humidity,p.pressure].every(Number.isFinite))++report.invalid_env;
 for(const [list,value] of [[report.sessions,p.sample_id.split('-')[0]],[report.versions,p.firmware]])if(!list.includes(value))list.push(value);
 report.samples.push({received_ms:performance.now()-started,uptime_ms:p.uptime_ms,id:p.sample_id});
});
