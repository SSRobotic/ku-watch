const TELEMETRY_TOPIC = require('./mqtt_topic.cjs').topic;
// Long-running read-only telemetry audit. Never saves raw GPS or pulse readings.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {performance}=require('node:perf_hooks');
const {Coverage,continuityPass}=require('./telemetry_audit_coverage.cjs');
const mqtt=require(path.join(process.env.APPDATA,'npm/node_modules/node-red/node_modules/mqtt'));
const root=path.join(__dirname,'..'),arg=process.argv.slice(2),hours=Number(arg[arg.indexOf('--hours')+1]||24);
const stopOnFailure=arg.includes('--stop-on-failure');
if(!Number.isFinite(hours)||hours<=0||hours>48)throw Error('Hours must be >0 and <=48');
const out=path.join(root,'output/soak_audit');fs.mkdirSync(out,{recursive:true});
const lock=path.join(out,'active.json');
if(fs.existsSync(lock)){const previous=JSON.parse(fs.readFileSync(lock));try{process.kill(previous.pid,0);throw Error('An audit is already running');}catch(e){if(e.code!=='ESRCH')throw e;}}
const began=Date.now(),cfg=JSON.parse(fs.readFileSync(path.join(root,'config/cloud.local.json')));
const report={boundary:'Read-only real MQTT telemetry; computer and device must remain powered; not a full-charge battery test',pid:process.pid,status:'running',started_utc:new Date(began).toISOString(),target_hours:hours,samples:0,malformed:0,duplicates:0,gaps:0,missing_sequences:0,sessions:0,connections:0,disconnects:0,max_receive_gap_ms:0,battery_start:null,battery_latest:null,battery_min:null,low_battery_seen:false,versions:[],sensor_ready_counts:{env_live:0,pulse_live:0,acc_live:0,mag_live:0,iaq_valid:0,battery_valid:0},first_sample_utc:null,last_sample_utc:null};
const monotonicStart=performance.now(),coverage=new Coverage();
report.timing_basis='Monotonic elapsed time; maximum gap includes leading/trailing silence';
report.continuity_pass=false;report.stop_on_failure=stopOnFailure;
// Keep bounded delivery metadata for diagnosing a failed run. Do not retain
// raw wearer GPS, pulse readings or credentials in the audit report.
report.backfill_samples=0;report.last_backfill=null;
report.last_live_sample_id=null;report.gap_details=[];
let lastSession='',lastSequence=0,done=false;
function write(){const elapsed=performance.now()-monotonicStart;report.observed_hours=elapsed/3600000;
 Object.assign(report,coverage.snapshot(elapsed));fs.writeFileSync(path.join(out,'status.tmp'),JSON.stringify(report,null,2));fs.renameSync(path.join(out,'status.tmp'),path.join(out,'status.json'));}
fs.writeFileSync(lock,JSON.stringify({pid:process.pid,started_utc:report.started_utc}));
const client=mqtt.connect('mqtts://'+cfg.host+':8883',{username:cfg.reader_user,password:cfg.reader_password,clientId:'ku-soak-'+crypto.randomBytes(6).toString('hex'),rejectUnauthorized:true,reconnectPeriod:5000});
client.on('connect',()=>{report.connections++;client.subscribe(TELEMETRY_TOPIC,{qos:1});});
client.on('offline',()=>report.disconnects++);client.on('error',()=>{});
client.on('message',(_,raw,packet)=>{if(packet.retain)return;let p;try{p=JSON.parse(raw);}catch{report.malformed++;return;}
 if(p.backfill){report.backfill_samples++;
  if(/^[a-f0-9]{8}-[a-f0-9]{8}$/i.test(p.sample_id||''))report.last_backfill={id:p.sample_id,
    timestamp:Number.isSafeInteger(p.timestamp)?p.timestamp:null,received_utc:new Date().toISOString()};
  return;
 }if(!/^[a-f0-9]{8}-[a-f0-9]{8}$/i.test(p.sample_id||'')){report.malformed++;return;}
 const [session,seqText]=p.sample_id.split('-'),seq=parseInt(seqText,16),now=Date.now();
 if(session===lastSession&&seq<=lastSequence){report.duplicates++;return;}
 if(session!==lastSession){report.sessions++;lastSession=session;}
 else if(seq!==lastSequence+1){report.gaps++;report.missing_sequences+=seq-lastSequence-1;
  if(report.gap_details.length<16)report.gap_details.push({before:report.last_live_sample_id,after:p.sample_id,
    missing_sequences:seq-lastSequence-1,received_utc:new Date(now).toISOString()});
 }
 report.last_live_sample_id=p.sample_id;
 lastSequence=seq;coverage.receive(performance.now()-monotonicStart);
 report.samples++;if(!report.first_sample_utc)report.first_sample_utc=new Date(now).toISOString();report.last_sample_utc=new Date(now).toISOString();
 if(typeof p.firmware==='string'&&!report.versions.includes(p.firmware))report.versions.push(p.firmware);
 for(const key of Object.keys(report.sensor_ready_counts))if(p[key]===true)report.sensor_ready_counts[key]++;
 if(p.battery_valid===true&&Number.isFinite(p.battery_percent)){
  if(report.battery_start===null)report.battery_start=p.battery_percent;report.battery_latest=p.battery_percent;
  report.battery_min=report.battery_min===null?p.battery_percent:Math.min(report.battery_min,p.battery_percent);
  if(p.alert_battery_state===2)report.low_battery_seen=true;
 }
});
function finish(status){if(done)return;done=true;clearInterval(interval);clearTimeout(deadline);report.status=status;
 report.completed_utc=new Date().toISOString();report.observed_hours=(performance.now()-monotonicStart)/3600000;
 Object.assign(report,coverage.snapshot(performance.now()-monotonicStart));report.continuity_pass=continuityPass(report);
 write();client.end(true);fs.unlinkSync(lock);}
const interval=setInterval(()=>{write();
 if(stopOnFailure&&(report.sessions>1||report.gaps>0||report.malformed>0||report.disconnects>0||report.max_receive_gap_ms>10000)){
  report.failure_reason='Continuity criterion exceeded; stopped early and retained evidence';finish('failed');
 }
},10000),deadline=setTimeout(()=>finish('completed'),hours*3600000);write();
process.on('SIGINT',()=>finish('stopped'));process.on('SIGTERM',()=>finish('stopped'));
console.log('Read-only audit started; status is output/soak_audit/status.json');
