const fs=require('fs'),path=require('path'),crypto=require('crypto');
const mqtt=require(path.join(process.env.APPDATA,'npm/node_modules/node-red/node_modules/mqtt'));
const root=path.resolve(__dirname,'..'),cfg=JSON.parse(fs.readFileSync(path.join(root,'config/cloud.local.json')));
const topic=cfg.topic||'ku_watch/live',target=path.resolve(root,process.argv[2]);
const r={topic,samples:[],online_status:false,firmware:null};
const c=mqtt.connect('mqtts://'+cfg.host+':8883',{username:cfg.reader_user,password:cfg.reader_password,clientId:'ku-topic-verify-'+crypto.randomBytes(5).toString('hex'),rejectUnauthorized:true,reconnectPeriod:0});
let done=false;const timer=setTimeout(()=>finish('No progressing real stream within 45 seconds'),45000);
function finish(error){if(done)return;done=true;clearTimeout(timer);r.passed=!error&&r.samples.length>=5&&r.samples.every(x=>x.qos===1);if(error)r.error=error;fs.writeFileSync(target,JSON.stringify(r,null,2));console.log(JSON.stringify(r));c.end(true);process.exitCode=r.passed?0:1;}
c.on('connect',()=>c.subscribe([topic,topic+'/status'],{qos:1}));c.on('error',()=>finish('Configured reader unavailable'));
c.on('message',(t,raw,pkt)=>{let p;try{p=JSON.parse(raw)}catch{return;}if(t.endsWith('/status')){r.online_status=p.online===true;r.firmware=p.version;return;}if(pkt.retain||p.backfill||!/^\w{8}-\w{8}$/.test(p.sample_id||''))return;if(!r.samples.some(x=>x.sample_id===p.sample_id))r.samples.push({sample_id:p.sample_id,capture_utc:p.timestamp,received_utc:new Date().toISOString(),qos:pkt.qos,device:p.device,firmware:p.firmware});if(r.samples.length>=5)finish();});
