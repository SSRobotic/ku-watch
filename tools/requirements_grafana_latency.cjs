const TELEMETRY_TOPIC = require('./mqtt_topic.cjs').topic;
// Measures capture time -> Grafana query availability, not browser paint latency.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {containsCapture}=require('./grafana_frame_match.cjs');
const mqtt=require(path.join(process.env.APPDATA,'npm/node_modules/node-red/node_modules/mqtt'));
const root=path.join(__dirname,'..'),local=JSON.parse(fs.readFileSync(path.join(root,'config/cloud.local.json')));
const sharing=JSON.parse(fs.readFileSync(path.join(root,'config/friend-share.local.json')));
if(!sharing.access_token){
 const {DatabaseSync}=require('node:sqlite');
 const db=new DatabaseSync('D:/iot2026/Grafana/grafana/data/grafana.db',{readOnly:true});
 const row=db.prepare("SELECT access_token FROM dashboard_public WHERE dashboard_uid='ku-watch-friends' AND is_enabled=1").get();
 db.close();sharing.access_token=row?.access_token;
}
if(!/^[a-f0-9]{32}$/i.test(sharing.access_token||''))throw new Error('Existing dashboard query access unavailable');
// Existing firmware panel selects all fields, including sample_id. No new
// public dashboard or persistent access token is created for this test.
const endpoint='http://127.0.0.1:3000/api/public/dashboards/'+sharing.access_token+'/panels/87/query';
const output=process.argv[2]||'output/requirements_audit_20261009/grafana_latency_10.json';
const reference=process.argv[3]?JSON.parse(fs.readFileSync(path.join(root,process.argv[3]))):null;
if(reference && (!reference.usable || !Number.isFinite(reference.offset_ms) || !Number.isFinite(reference.uncertainty_ms) || Math.abs(Date.now()-reference.measured_at_host_ms)>120000))throw Error('Fresh usable clock reference required');
const client=mqtt.connect('mqtts://'+local.host+':8883',{username:local.reader_user,password:local.reader_password,
  clientId:'ku-latency-'+crypto.randomBytes(6).toString('hex'),rejectUnauthorized:true,reconnectPeriod:0});
const results=[];let busy=false,finished=false;const used=new Set();
function finish(){if(finished)return;finished=true;clearTimeout(deadline);
 const success=results.filter(x=>Number.isFinite(x.query_available_delay_ms));
 const report={boundary:'telemetry capture UTC -> Grafana query response; browser refresh/paint not measured',
   identity_match:'Exact sample_id and capture UTC in the same Grafana response row',clock_resolution_ms:1000,samples:results,mean_ms:success.length?success.reduce((a,b)=>a+b.query_available_delay_ms,0)/success.length:null,
   reference_offset_ms:reference?.offset_ms??null,reference_uncertainty_ms:reference?.uncertainty_ms??null,
   corrected_mean_ms:reference&&success.length?success.reduce((a,b)=>a+b.reference_corrected_delay_ms,0)/success.length:null,
   measured:success.length,within_5s:!!reference&&success.length===10&&success.every(x=>x.reference_corrected_delay_ms>=0 && x.reference_corrected_delay_ms+reference.uncertainty_ms<=5000)};
 fs.writeFileSync(path.join(root,output),JSON.stringify(report,null,2));
 console.log(JSON.stringify({measured:report.measured,raw_mean_ms:report.mean_ms,corrected_mean_ms:report.corrected_mean_ms,within_5s:report.within_5s}));client.end(true);}
const deadline=setTimeout(finish,60000);
client.on('connect',()=>client.subscribe(TELEMETRY_TOPIC,{qos:1}));
client.on('error',()=>{console.log('MQTT query measurement connection unavailable');finish();});
client.on('message',async(_,raw)=>{
 if(busy||finished)return;let p;try{p=JSON.parse(raw.toString());}catch{return;}
 if(p.backfill||!Number.isSafeInteger(p.timestamp)||used.has(p.sample_id))return;
 busy=true;used.add(p.sample_id);let visible=null;const started=Date.now();
 try{while(Date.now()-started<6000 && !finished){
  const r=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({intervalMs:1000,maxDataPoints:20,timeRange:{from:new Date(p.timestamp*1000-3000).toISOString(),to:new Date(p.timestamp*1000+6000).toISOString(),timezone:'Asia/Bangkok'}}),signal:AbortSignal.timeout(5000)});
  const d=await r.json();if(r.ok && containsCapture(d,p))visible=Date.now()-p.timestamp*1000;
  if(visible!==null)break;await new Promise(resolve=>setTimeout(resolve,200));
 }
 }catch{/* Failure is retained as an unmeasured case, never treated as zero. */}
 results.push({sample_id:p.sample_id,mqtt_received_raw_delay_ms:started-p.timestamp*1000,
   query_available_delay_ms:visible,query_after_mqtt_ms:visible===null?null:visible-(started-p.timestamp*1000),
   reference_corrected_delay_ms:reference&&visible!==null?visible+reference.offset_ms:null});busy=false;
 if(results.length>=10)finish();
});
