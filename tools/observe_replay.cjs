const TELEMETRY_TOPIC = require('./mqtt_topic.cjs').topic;
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const mqtt=require(path.join(process.env.APPDATA,'npm/node_modules/node-red/node_modules/mqtt'));
const local=JSON.parse(fs.readFileSync('config/cloud.local.json','utf8'));
const result={samples:[],statuses:[],started:Date.now()};
const out=process.argv[2]||'output/small_finish_validation/replay_observer.json';
const c=mqtt.connect('mqtts://'+local.host+':8883',{username:local.reader_user,password:local.reader_password,
  clientId:'ku-batch-observer-'+crypto.randomBytes(6).toString('hex'),rejectUnauthorized:true,reconnectPeriod:2000,connectTimeout:10000});
function save(){fs.writeFileSync(out,JSON.stringify(result));}
c.on('connect',()=>c.subscribe([TELEMETRY_TOPIC,TELEMETRY_TOPIC+'/status'],{qos:1},()=>{console.log('Replay reader connected');save();}));
c.on('message',(topic,raw,packet)=>{
  const p=JSON.parse(raw);
  if(topic.endsWith('/status'))result.statuses.push({at:Date.now(),online:p.online,version:p.version,qos:packet.qos});
  else result.samples.push({at:Date.now(),id:p.sample_id,timestamp:p.timestamp,uptime_ms:p.uptime_ms,backfill:p.backfill,qos:packet.qos});
  save();
});
c.on('error',e=>console.log('Observer transport error',e.code));
setTimeout(()=>{save();console.log('Observed real samples:',result.samples.length);c.end(true);},Number(process.argv[3]||800000));
