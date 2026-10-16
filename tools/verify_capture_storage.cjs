const TELEMETRY_TOPIC = require('./mqtt_topic.cjs').topic;
// Read real telemetry and replay exactly one actual observation to the DB queue.
// No synthesized readings, coordinates or device identities are published.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const mqtt=require(path.join(process.env.APPDATA,'npm/node_modules/node-red/node_modules/mqtt'));
const root=path.join(__dirname,'..'),cfg=JSON.parse(fs.readFileSync(path.join(root,'config/cloud.local.json')));
const source=fs.readFileSync(path.join(root,'include/config.h'),'utf8');
const token=source.match(/INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"/)[1];
const body=new Function('msg','env','node','flow',fs.readFileSync(path.join(root,'integration/node-red/to_influx.js'),'utf8'));
const env={get:k=>({KU_INFLUX_TOKEN:token,KU_INFLUX_URL:'http://127.0.0.1:8181',KU_INFLUX_DATABASE:'iot'})[k]};
const samples=new Map();let done=false;
const client=mqtt.connect('mqtts://'+cfg.host+':8883',{username:cfg.reader_user,password:cfg.reader_password,clientId:'ku-db-proof-'+crypto.randomBytes(6).toString('hex'),rejectUnauthorized:true,reconnectPeriod:0});
const timer=setTimeout(()=>finish({passed:false,error:'No trusted real samples'}),30000);
function finish(report){if(done)return;done=true;clearTimeout(timer);client.end(true);
 fs.writeFileSync(path.join(root,'output/requirements_audit_20261009/capture_storage.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));process.exitCode=report.passed?0:1;}
client.on('error',()=>finish({passed:false,error:'MQTT unavailable'}));
client.on('connect',()=>client.subscribe(TELEMETRY_TOPIC,{qos:1}));
client.on('message',async(_,raw,packet)=>{
 if(done||packet.retain||samples.size>=5)return;let p;try{p=JSON.parse(raw);}catch{return;}
 if(p.backfill||!Number.isSafeInteger(p.timestamp)||!p.sample_id)return;samples.set(p.sample_id,p);
 if(samples.size!==5)return;
 try{
  const replay=body({payload:samples.values().next().value},env,{status:()=>{}},{});
  const replayStatuses=[];
  for(let n=0;n<2;n++){const r=await fetch(replay.url,{method:'POST',headers:replay.headers,body:replay.payload,signal:AbortSignal.timeout(5000)});replayStatuses.push(r.status);}
  const ids=[...samples.keys()].map(id=>id.toLowerCase());let rows=[];
  for(let n=0;n<12;n++){
   const sql="SELECT sample_id, COUNT(*) AS rows FROM ku_watch WHERE sample_id IN ("+ids.map(id=>"'"+id+"'").join(',')+") GROUP BY sample_id";
   const r=await fetch('http://127.0.0.1:8181/api/v3/query_sql',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({db:'iot',q:sql,format:'json'}),signal:AbortSignal.timeout(5000)});
   if(!r.ok)throw Error('DB query rejected');rows=await r.json();if(rows.length===5)break;await new Promise(r=>setTimeout(r,1000));
  }
  finish({boundary:'Five real trusted captures; identical first capture re-enqueued twice; actual SQL distinct point counts',sample_count:5,replay_statuses:replayStatuses,rows,passed:rows.length===5&&rows.every(row=>row.rows===1)&&replayStatuses.every(s=>s===202)});
 }catch{finish({passed:false,error:'DB verification unavailable'});}
});
