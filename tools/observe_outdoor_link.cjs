const TELEMETRY_TOPIC = require('./mqtt_topic.cjs').topic;
// Bounded read-only diagnostics. No publishing, location, raw PPG or credentials in output.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const mqtt=require(path.join(process.env.APPDATA,'npm/node_modules/node-red/node_modules/mqtt'));
const root=path.resolve(__dirname,'..'),cfg=JSON.parse(fs.readFileSync(path.join(root,'config/cloud.local.json')));
const start=Date.now(),stamp=new Date().toISOString().replace(/[-:.]/g,'');
const out=path.join(root,'output/deadline_20261018/outdoor_link_'+stamp+'.json');
const report={started_utc:new Date(start).toISOString(),boundary:'Read-only MQTT observation, retained status distinguished from new telemetry; no physical test pass implied',connected:false,subscriptions:[],live:0,backfill:0,retained_telemetry:0,malformed:0,status_messages:[],samples:[]};
let done=false;
const client=mqtt.connect('mqtts://'+cfg.host+':8883',{username:cfg.reader_user,password:cfg.reader_password,clientId:'ku-outdoor-read-'+crypto.randomBytes(6).toString('hex'),rejectUnauthorized:true,reconnectPeriod:0,connectTimeout:10000});
function finish(error){if(done)return;done=true;clearTimeout(timer);report.finished_utc=new Date().toISOString();report.observed_s=(Date.now()-start)/1000;if(error)report.error=error;fs.writeFileSync(out,JSON.stringify(report,null,2));console.log(JSON.stringify({...report,samples:report.samples.slice(-3),output:path.relative(root,out)}));client.end(true);}
client.on('connect',()=>{report.connected=true;client.subscribe([TELEMETRY_TOPIC,TELEMETRY_TOPIC+'/status'],{qos:1},(err,grants)=>{if(err)return finish('Subscription failed');report.subscriptions=grants;});});
client.on('error',()=>finish('MQTT connection failed'));
client.on('message',(topic,raw,packet)=>{let p;try{p=JSON.parse(raw);}catch{report.malformed++;return;}
 const received_utc=new Date().toISOString();
 if(topic.endsWith('/status')){const safe={received_utc,retained:packet.retain};for(const k of ['online','status','version','firmware','connected','uptime_ms'])if(typeof p[k]==='boolean'||typeof p[k]==='number'||(typeof p[k]==='string'&&p[k].length<48))safe[k]=p[k];report.status_messages.push(safe);return;}
 if(packet.retain){report.retained_telemetry++;return;}
 if(p.backfill)report.backfill++;else report.live++;
 const row={received_utc,sample_id:p.sample_id,backfill:!!p.backfill,capture_timestamp:p.timestamp,uptime_ms:p.uptime_ms};
 for(const k of ['wifi','mqtt','gps_fix','env_live','battery_valid','firmware','clock_source'])if(['string','number','boolean'].includes(typeof p[k]))row[k]=p[k];
 report.samples.push(row);
});
const timer=setTimeout(()=>finish(),30000);
