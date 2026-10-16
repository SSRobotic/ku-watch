// Actual read-only comparison. The primary receiver disables Nagle for PUBACKs.
// Every mode retains the earlier 5-minute duration, count and <3 s receive-gap checks.
const fs=require('fs'),path=require('path'),crypto=require('crypto'),{performance}=require('node:perf_hooks');
const mqtt=require(path.join(process.env.APPDATA,'npm/node_modules/node-red/node_modules/mqtt'));
const root=path.resolve(__dirname,'..'),cfg=JSON.parse(fs.readFileSync(path.join(root,'config/cloud.local.json'))),topic=require('./mqtt_topic.cjs').topic;
const duration=300000,created=new Date().toISOString(),dir=path.join(root,'output/fr_completion_20261016/mqtt_transport_runs',created.replace(/[:.]/g,'-'));
fs.mkdirSync(dir,{recursive:true});
const plan={started_utc:created,primary_mode:'qos1_no_delay',duration_s:300,max_receive_gap_must_be_less_than_ms:3000,
  boundary:'Actual MQTT only, no publications or injected values. QoS0 is a diagnostic control and cannot accept FR-03. Each receiver has an independent TLS socket on the same PC and network.',
  modes:[{name:'qos1_no_delay',qos:1,no_delay:true},{name:'qos1_nagle_control',qos:1,no_delay:false},{name:'qos0_diagnostic',qos:0,no_delay:true}]};
fs.writeFileSync(path.join(dir,'plan.json'),JSON.stringify(plan,null,2),{flag:'wx'});
const reports={},arrivals=new Map(),clients=[];let completed=0;
const lwtFile=path.join(root,'output/final_acceptance_20261016/offline_10min/result.json');
const lwt=JSON.parse(fs.readFileSync(lwtFile));
function completeAll(){
 if(completed!==plan.modes.length)return;
 clearInterval(progress);
 const matched=[];
 for(const [id,times] of arrivals)if(plan.modes.every(m=>times[m.name]!==undefined))
   matched.push({id,qos1_control_minus_primary_ms:times.qos1_nagle_control-times.qos1_no_delay,
     qos0_minus_primary_ms:times.qos0_diagnostic-times.qos1_no_delay});
 const output={...plan,completed_utc:new Date().toISOString(),modes:reports,matched_arrivals:matched,
   primary_full_requirement_pass:reports.qos1_no_delay.full_requirement_pass};
 fs.writeFileSync(path.join(dir,'comparison.json'),JSON.stringify(output,null,2),{flag:'wx'});
 console.log(JSON.stringify({finished:true,result:path.join(dir,'comparison.json'),primary_pass:output.primary_full_requirement_pass,
   modes:Object.fromEntries(Object.entries(reports).map(([k,v])=>[k,{live:v.live,gaps:v.sequence_gaps,max_receive_gap_ms:v.max_receive_gap_ms,full_requirement_pass:v.full_requirement_pass}]))}));
}
for(const mode of plan.modes){
 const report={...mode,topic,started_utc:null,live:0,duplicates:0,malformed:0,disconnects:0,sequence_gaps:0,sessions:0,status_versions:[],samples:[]};
 reports[mode.name]=report;let started=0,done=false,timer;const seen=new Set(),last=new Map();
 const client=mqtt.connect('mqtts://'+cfg.host+':8883',{username:cfg.reader_user,password:cfg.reader_password,
   clientId:'ku-transport-'+crypto.randomBytes(6).toString('hex'),rejectUnauthorized:true,reconnectPeriod:1000,connectTimeout:10000,protocolVersion:4});clients.push(client);
 function finish(error){
   if(done)return;done=true;clearTimeout(timer);
   report.observed_s=started?(performance.now()-started)/1000:0;if(error)report.error=error;
   const gaps=report.samples.slice(1).map((s,i)=>s.receive_ms-report.samples[i].receive_ms);
   report.max_receive_gap_ms=gaps.length?Math.max(...gaps):null;
   report.mean_receive_interval_ms=gaps.length?gaps.reduce((a,b)=>a+b,0)/gaps.length:null;
   report.timing_clock='monotonic performance.now';
   report.transport_pass=Boolean(!error&&report.observed_s>=300&&report.live>=295&&!report.sequence_gaps&&!report.malformed&&!report.disconnects&&report.max_receive_gap_ms<3000);
   report.qos1_observed=report.samples.length>0&&report.samples.every(s=>s.qos===1);
   report.count_matches_1hz=report.live>=299&&report.live<=301;
   report.topic_matches_original_requirement=/^ku\/iot\/[^/]+\/[^/]+\/env$/.test(topic);
   report.lwt_offline_verified=lwt.lwt_offline_observed===true;
   report.lwt_evidence_sha256=crypto.createHash('sha256').update(fs.readFileSync(lwtFile)).digest('hex');
   report.full_requirement_pass=Boolean(mode.qos===1&&report.transport_pass&&report.qos1_observed&&report.count_matches_1hz&&report.topic_matches_original_requirement&&report.lwt_offline_verified);
   report.completed_utc=new Date().toISOString();++completed;client.end(true);completeAll();
 }
 client.on('connect',()=>{
   client.stream.setNoDelay(mode.no_delay);report.no_delay_applied=mode.no_delay;
   client.subscribe([topic,topic+'/status'],{qos:mode.qos},(error,grants)=>{
     if(error||grants.some(g=>g.qos===128))return finish('Subscription rejected');
     if(!started){started=performance.now();report.started_utc=new Date().toISOString();timer=setTimeout(()=>finish(),duration+30);}
   });
 });
 client.on('message',(actual,raw,packet)=>{
   if(done)return;let p;try{p=JSON.parse(raw);}catch{++report.malformed;return;}
   if(actual.endsWith('/status')){if(p.version&&!report.status_versions.includes(p.version))report.status_versions.push(p.version);return;}
   if(!started||packet.retain||p.backfill)return;
   if(!/^[a-f0-9]{8}-[a-f0-9]{8}$/i.test(p.sample_id||'')||!Number.isFinite(p.uptime_ms)){++report.malformed;return;}
   if(seen.has(p.sample_id)){++report.duplicates;return;}seen.add(p.sample_id);
   const [session,sequence]=p.sample_id.split('-'),n=parseInt(sequence,16),previous=last.get(session);
   if(previous===undefined)++report.sessions;else if(n>previous+1)report.sequence_gaps+=n-previous-1;
   last.set(session,Math.max(previous||0,n));++report.live;
   const now=performance.now();report.samples.push({id:p.sample_id,receive_ms:now-started,uptime_ms:p.uptime_ms,qos:packet.qos,firmware:p.firmware});
   if(!arrivals.has(p.sample_id))arrivals.set(p.sample_id,{});arrivals.get(p.sample_id)[mode.name]=now;
 });
 client.on('offline',()=>{if(started&&!done)++report.disconnects;});
 client.on('error',()=>{});
 setTimeout(()=>{if(!started&&!done)finish('No real subscription established');},20000).unref();
}
const progress=setInterval(()=>console.log(JSON.stringify({elapsed_s:Math.round((Date.now()-Date.parse(created))/1000),
  modes:Object.fromEntries(Object.entries(reports).map(([k,v])=>[k,{live:v.live,gaps:v.sequence_gaps,disconnects:v.disconnects}]))})),30000);
console.log(JSON.stringify({started:true,plan:path.join(dir,'plan.json'),primary:'qos1_no_delay'}));
