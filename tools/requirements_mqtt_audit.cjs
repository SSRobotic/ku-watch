const TELEMETRY_TOPIC = require('./mqtt_topic.cjs').topic;
// FR-03 acceptance observation: subscribe to actual watch data for five minutes.
// No test measurements are published and credentials never enter the report.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {performance}=require('node:perf_hooks');
const mqtt=require(path.join(process.env.APPDATA,'npm/node_modules/node-red/node_modules/mqtt'));
const root=path.join(__dirname,'..');
const local=JSON.parse(fs.readFileSync(path.join(root,'config/cloud.local.json'),'utf8'));
const duration=Number(process.argv[2]||300)*1000;
const report={requirement:'FR-03',duration_s:duration/1000,topic:TELEMETRY_TOPIC,subscription_qos:1,
  connected:false,packets:0,live:0,backfill:0,duplicates:0,malformed:0,disconnects:0,
  sequence_gaps:0,sessions:0,status_versions:[],samples:[]};
const seen=new Set(),last=new Map();let start=0,finished=false,timer;
const target=path.resolve(root,process.argv[3]||'output/requirements_audit_20261009/mqtt_5min.json');
fs.mkdirSync(path.dirname(target),{recursive:true});
if(fs.existsSync(target))throw Error('Keep earlier audit unchanged; choose a new output path');
const client=mqtt.connect('mqtts://'+local.host+':8883',{username:local.reader_user,password:local.reader_password,
  clientId:'ku-req-audit-'+crypto.randomBytes(6).toString('hex'),rejectUnauthorized:true,
  reconnectPeriod:1000,connectTimeout:10000,protocolVersion:4});
function finish(error){
  if(finished)return;finished=true;clearTimeout(timer);clearInterval(progress);
  report.observed_s=start?(performance.now()-start)/1000:0;report.timing_clock='monotonic performance.now';if(error)report.error=error;
  const intervals=report.samples.slice(1).map((s,i)=>s.receive_ms-report.samples[i].receive_ms);
  report.max_receive_gap_ms=intervals.length?Math.max(...intervals):null;
  report.mean_receive_interval_ms=intervals.length?intervals.reduce((a,b)=>a+b,0)/intervals.length:null;
  report.full_duration=start && report.observed_s>=duration/1000;
  // Expected monotonic capture IDs catch missing packets independently of clock sync.
  // Approximate count prevents a silent watch producing a misleading gap-free pass.
  report.pass=Boolean(report.full_duration && report.live>=duration/1000-5 && !report.sequence_gaps &&
    !report.malformed && !report.disconnects && report.max_receive_gap_ms<3000);
  report.topic_matches_original_requirement=/^ku\/iot\/[^/]+\/[^/]+\/env$/.test(report.topic);
  report.transport_pass=report.pass;
  report.qos1_observed=report.samples.length>0&&report.samples.every(s=>s.qos===1);
  report.count_matches_1hz=report.live>=Math.floor(duration/1000)-1&&report.live<=Math.ceil(duration/1000)+1;
  const lwtFile=path.join(root,'output/final_acceptance_20261016/offline_10min/result.json');
  const lwt=fs.existsSync(lwtFile)?JSON.parse(fs.readFileSync(lwtFile)):{};
  report.lwt_offline_verified=lwt.lwt_offline_observed===true;
  if(report.lwt_offline_verified)report.lwt_evidence_sha256=crypto.createHash('sha256').update(fs.readFileSync(lwtFile)).digest('hex');
  report.full_requirement_pass=report.transport_pass&&report.topic_matches_original_requirement&&report.qos1_observed&&report.count_matches_1hz&&report.lwt_offline_verified;
  fs.writeFileSync(target,JSON.stringify(report,null,2));
  console.log(JSON.stringify({finished:true,live:report.live,gaps:report.sequence_gaps,duplicates:report.duplicates,
    disconnects:report.disconnects,observed_s:report.observed_s,pass:report.pass,error:report.error||null}));
  client.end(true);process.exitCode=error?1:0;
}
client.on('connect',()=>{
  report.connected=true;client.subscribe([TELEMETRY_TOPIC,TELEMETRY_TOPIC+'/status'],{qos:1},(err,grants)=>{
    if(err||grants.some(g=>g.qos===128))return finish('Subscription rejected');
    if(!start){start=performance.now();report.start_utc=new Date().toISOString();
      timer=setTimeout(()=>finish(),duration);console.log('FR-03 five-minute real MQTT observation started.');}
  });
});
client.on('message',(topic,raw,packet)=>{
  let p;try{p=JSON.parse(raw.toString());}catch{++report.malformed;return;}
  if(topic.endsWith('/status')){if(typeof p.version==='string'&&!report.status_versions.includes(p.version))report.status_versions.push(p.version);return;}
  if(!start||packet.retain)return;++report.packets;
  if(p.backfill===true){++report.backfill;return;}
  if(typeof p.sample_id!=='string'||!/^([a-f0-9]{8})-([a-f0-9]{8})$/i.test(p.sample_id)||!Number.isFinite(p.uptime_ms)){++report.malformed;return;}
  if(seen.has(p.sample_id)){++report.duplicates;return;}seen.add(p.sample_id);
  const [session,sequence]=p.sample_id.split('-'),n=parseInt(sequence,16),previous=last.get(session);
  if(previous===undefined)++report.sessions;
  else if(n>previous+1)report.sequence_gaps+=n-previous-1;
  last.set(session,Math.max(previous||0,n));++report.live;
  report.samples.push({id:p.sample_id,receive_ms:performance.now()-start,uptime_ms:p.uptime_ms,
    capture_utc:Number.isSafeInteger(p.timestamp)?p.timestamp:null,qos:packet.qos});
});
client.on('offline',()=>{if(start)++report.disconnects;});
client.on('error',()=>{if(!start)finish('MQTT connection or authentication failed');});
const progress=setInterval(()=>console.log(JSON.stringify({observed_s:start?Math.round((performance.now()-start)/1000):0,
  live:report.live,gaps:report.sequence_gaps,disconnects:report.disconnects})),30000);
setTimeout(()=>{if(!start)finish('No MQTT connection established');},15000).unref();
