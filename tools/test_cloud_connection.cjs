const TELEMETRY_TOPIC = require('./mqtt_topic.cjs').topic;
// Uses installed Node-RED MQTT client. Never prints credentials or sensor payloads.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const mqtt=require(path.join(process.env.APPDATA,'npm/node_modules/node-red/node_modules/mqtt'));
const local=JSON.parse(fs.readFileSync(path.join(__dirname,'../config/cloud.local.json'),'utf8'));
const topic=TELEMETRY_TOPIC;
function connection(user,password) {
  return new Promise((resolve,reject)=>{
    const client=mqtt.connect('mqtts://'+local.host+':8883',{username:user,password,
      clientId:'ku-validation-'+crypto.randomBytes(6).toString('hex'),rejectUnauthorized:true,
      reconnectPeriod:0,connectTimeout:10000,protocolVersion:4});
    client.once('connect',()=>resolve(client));
    client.once('error',err=>{client.end(true);reject(new Error('MQTT authentication/connection failed: '+err.code));});
  });
}
(async()=>{
  const writer=await connection(local.watch_user,local.watch_password);
  console.log('Board account: TLS and authentication OK');writer.end(true);
  const reader=await connection(local.reader_user,local.reader_password);
  await new Promise((resolve,reject)=>reader.subscribe(topic,{qos:0},(err,grants)=>{
    if(err || !grants.length || grants[0].qos===128) reject(new Error('Reader lacks subscribe permission'));
    else resolve();
  }));
  console.log('Node-RED account: TLS, authentication and topic subscription OK');
  if(process.argv.includes('--auth-only')) { reader.end(true); return; }
  const timeout=setTimeout(()=>{console.log('No live board sample received in 12 seconds');reader.end(true);},12000);
  reader.once('message',(_,raw)=>{
    clearTimeout(timeout);const p=JSON.parse(raw.toString());
    console.log('Real board packet received; fields='+Object.keys(p).length+'; recording='+p.recording+'; gps_fix='+p.gps_fix);
    reader.end(true);
  });
})().catch(err=>{console.error(err.message);process.exitCode=1;});
