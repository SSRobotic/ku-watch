const fs=require('fs'),path=require('path'),crypto=require('crypto');
const mqtt=require(path.join(process.env.APPDATA,'npm/node_modules/node-red/node_modules/mqtt'));
const root=path.resolve(__dirname,'..'),cfg=JSON.parse(fs.readFileSync(path.join(root,'config/cloud.local.json')));
const old=cfg.topic||'ku_watch/live',out=path.join(root,'output/final_acceptance_20261016/topic_plan.json');
const c=mqtt.connect('mqtts://'+cfg.host+':8883',{username:cfg.reader_user,password:cfg.reader_password,clientId:'ku-topic-plan-'+crypto.randomBytes(5).toString('hex'),rejectUnauthorized:true,reconnectPeriod:0});
let done=false;const timer=setTimeout(()=>end({error:'No actual device identity received'}),20000);
function end(v){if(done)return;done=true;clearTimeout(timer);fs.writeFileSync(out,JSON.stringify(v,null,2));console.log(JSON.stringify(v));c.end(true);}
c.on('connect',()=>c.subscribe(old,{qos:1}));c.on('error',()=>end({error:'Reader connection unavailable'}));
c.on('message',(_,raw,packet)=>{if(done||packet.retain)return;let p;try{p=JSON.parse(raw)}catch{return;}if(p.backfill||!/^ku-watch-[a-f0-9]+$/i.test(p.device||''))return;
const topic='ku/iot/ku_watch/'+p.device+'/env';c.subscribe([topic,topic+'/status'],{qos:1},(e,g)=>end({old_topic:old,new_topic:topic,device:p.device,firmware:p.firmware,reader_subscription_allowed:!e&&g.every(x=>x.qos===1),group_reason:'Existing project name ku_watch; device ID comes from actual watch telemetry.'}));});
