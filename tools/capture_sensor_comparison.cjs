const TELEMETRY_TOPIC = require('./mqtt_topic.cjs').topic;
// Read-only actual estimates for comparison with a separately observed device.
// No raw PPG, GPS, credentials or invented reference readings are recorded.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const mqtt=require(path.join(process.env.APPDATA,'npm/node_modules/node-red/node_modules/mqtt'));
const root=path.join(__dirname,'..'),cfg=JSON.parse(fs.readFileSync(path.join(root,'config/cloud.local.json')));
const output=path.resolve(root,process.argv[2]||'output/deadline_20261018/sensor_comparison_capture.json');
const seconds=Number(process.argv[3]||90);
if(fs.existsSync(output))throw Error('Refusing to overwrite an existing comparison capture');
if(!Number.isFinite(seconds)||seconds<10||seconds>300)throw Error('Capture duration must be 10..300 seconds');
const report={boundary:'Actual MQTT-derived estimates and readiness only. Garmin reference has not been supplied or verified. This capture alone is not an accuracy/calibration pass.',started_utc:null,duration_s:seconds,reference:null,malformed:0,disconnects:0,samples:[]};
let timer,started=0,done=false;const seen=new Set();
const client=mqtt.connect('mqtts://'+cfg.host+':8883',{username:cfg.reader_user,password:cfg.reader_password,clientId:'ku-reference-'+crypto.randomBytes(5).toString('hex'),rejectUnauthorized:true,reconnectPeriod:0});
function finish(error){if(done)return;done=true;clearTimeout(timer);clearTimeout(deadline);report.completed_utc=new Date().toISOString();report.observed_s=started?(Date.now()-started)/1000:0;if(error)report.error=error;
  report.valid_bpm_samples=report.samples.filter(s=>s.bpm!==null).length;report.valid_spo2_samples=report.samples.filter(s=>s.spo2!==null).length;
  fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(report,null,2),{flag:'wx'});
  console.log(JSON.stringify({...report,samples:undefined}));client.end(true);process.exitCode=error?1:0;}
const deadline=setTimeout(()=>finish('MQTT subscription did not start in time'),(seconds+20)*1000);
client.on('connect',()=>client.subscribe(TELEMETRY_TOPIC,{qos:1},err=>{if(err)return finish('Subscription failed');started=Date.now();report.started_utc=new Date(started).toISOString();timer=setTimeout(()=>finish(),seconds*1000);console.log('Actual comparison capture started at '+report.started_utc);}));
client.on('error',()=>finish('MQTT connection error'));client.on('offline',()=>++report.disconnects);
client.on('message',(_,raw,packet)=>{
  if(!started||packet.retain)return;let p;try{p=JSON.parse(raw);}catch{++report.malformed;return;}
  if(p.backfill||seen.has(p.sample_id))return;if(!/^[a-f0-9]{8}-[a-f0-9]{8}$/i.test(p.sample_id||'')){++report.malformed;return;}seen.add(p.sample_id);
  report.samples.push({received_utc:new Date().toISOString(),source_timestamp:p.timestamp??null,sample_id:p.sample_id,uptime_ms:p.uptime_ms,firmware:p.firmware,
    bpm:p.pulse_live===true && p.finger===true && Number.isFinite(p.bpm) && p.bpm>0?p.bpm:null,
    spo2:p.spo2_valid===true && Number.isFinite(p.spo2)?p.spo2:null,
    pulse_live:p.pulse_live===true,spo2_valid:p.spo2_valid===true,finger:p.finger===true,
    temperature_c:p.env_live===true && Number.isFinite(p.temp)?p.temp:null,
    battery_v:p.battery_valid===true && Number.isFinite(p.battery_voltage)?p.battery_voltage:null});
});
