const TELEMETRY_TOPIC = require('./mqtt_topic.cjs').topic;
// Read-only MQTT observation. Old failed audit and actual telemetry stay untouched.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {performance}=require('node:perf_hooks');
const {AccumulatedCoverage}=require('./accumulated_coverage.cjs');
const mqtt=require(path.join(process.env.APPDATA,'npm/node_modules/node-red/node_modules/mqtt'));
const root=path.resolve(__dirname,'..'),out=path.join(root,'output/accumulated_soak');fs.mkdirSync(out,{recursive:true});
const lock=path.join(out,'active.json'),status=path.join(out,'status.json');
if(fs.existsSync(lock)){
  const old=JSON.parse(fs.readFileSync(lock));
  try{process.kill(old.pid,0);throw Error('Accumulated monitor already running');}catch(e){if(e.code!=='ESRCH')throw e;}
}
const previous=fs.existsSync(status)?JSON.parse(fs.readFileSync(status)):{};
const priorPath=path.join(root,'output/soak_audit/status.json'),priorBytes=fs.readFileSync(priorPath),prior=JSON.parse(priorBytes);
const coverage=new AccumulatedCoverage(previous),start=performance.now(),runId=crypto.randomBytes(8).toString('hex');
const log=path.join(out,'captures_'+runId+'.jsonl');
const report={...previous,pid:process.pid,run_id:runId,status:'awaiting_live_data',run_started_utc:new Date().toISOString(),
 target_hours:24,prior_observation_hours:prior.observed_hours,prior_audit_status:prior.status,
 prior_audit_sha256:crypto.createHash('sha256').update(priorBytes).digest('hex'),
 boundary:'Cumulative successful live-reception intervals; gaps, backfill and time without messages earn no time. Prior failed observation is separate. This is not a battery runtime or full-system pass.',
 samples:previous.samples||0,backfill:previous.backfill||0,duplicates:previous.duplicates||0,malformed:previous.malformed||0,
 disconnects:previous.disconnects||0,reader_connected:false,last_live_utc:null};
const elapsed=()=>performance.now()-start;
function event(type,details={}){fs.appendFileSync(log,JSON.stringify({type,received_utc:new Date().toISOString(),elapsed_ms:elapsed(),...details})+'\n');}
function write(){Object.assign(report,coverage.snapshot(elapsed()));report.cumulative_hours=report.credited_ms/3600000;
 report.remaining_cumulative_hours=Math.max(0,24-report.cumulative_hours);
 report.longest_continuous_hours=report.longest_continuous_ms/3600000;
 report.cumulative_24h_reached=report.credited_ms>=86400000;
 report.continuous_reception_24h_reached=report.longest_continuous_ms>=86400000;
 report.updated_utc=new Date().toISOString();
 fs.writeFileSync(status+'.tmp',JSON.stringify(report,null,2));fs.renameSync(status+'.tmp',status);
}
fs.writeFileSync(lock,JSON.stringify({pid:process.pid,run_id:runId}));event('monitor_started');write();
const cfg=JSON.parse(fs.readFileSync(path.join(root,'config/cloud.local.json')));
const client=mqtt.connect('mqtts://'+cfg.host+':8883',{username:cfg.reader_user,password:cfg.reader_password,
 clientId:'ku-cumulative-'+runId,rejectUnauthorized:true,reconnectPeriod:5000});
client.on('connect',()=>{report.reader_connected=true;event('reader_connected');client.subscribe(TELEMETRY_TOPIC,{qos:1});write();});
client.on('offline',()=>{report.reader_connected=false;report.disconnects++;coverage.interrupt();event('reader_offline');write();});
client.on('error',()=>{});
client.on('message',(_,raw,packet)=>{
 if(packet.retain)return;let p;try{p=JSON.parse(raw);}catch{report.malformed++;return;}
 if(p.backfill){report.backfill++;return;}
 if(!/^[a-f0-9]{8}-[a-f0-9]{8}$/i.test(p.sample_id||'')){report.malformed++;coverage.interrupt();event('malformed_live');return;}
 const ms=elapsed();if(!coverage.receive(p.sample_id,ms)){report.duplicates++;return;}
 report.samples++;report.last_live_utc=new Date().toISOString();report.status='collecting';
 event('live_capture',{sample_id:p.sample_id,capture_timestamp:Number.isSafeInteger(p.timestamp)?p.timestamp:null});
});
let finishing=false;
const timer=setInterval(()=>{if(report.last_live_utc&&Date.now()-Date.parse(report.last_live_utc)>10000)report.status='waiting_for_live_data';write();if(report.continuous_reception_24h_reached||fs.existsSync(path.join(out,'STOP')))finish();},5000);
function finish(){if(finishing)return;finishing=true;clearInterval(timer);coverage.interrupt();report.status='stopped';event('monitor_stopped');write();client.end(true);if(fs.existsSync(lock)&&JSON.parse(fs.readFileSync(lock)).pid===process.pid)fs.unlinkSync(lock);}
process.on('SIGINT',finish);process.on('SIGTERM',finish);
console.log('Read-only cumulative monitor started. Status: output/accumulated_soak/status.json');
