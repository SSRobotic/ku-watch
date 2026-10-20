// Local presentation launcher. Real services and read-only observations only.
'use strict';
const fs=require('fs'),path=require('path'),os=require('os'),http=require('http'),net=require('net');
const {spawn,spawnSync}=require('child_process');
const arg=(name,fallback)=>{const i=process.argv.indexOf(name);return i>=0?process.argv[i+1]:fallback;};
const root=path.resolve(arg('--root',path.join(__dirname,'..')));
const runDir=path.resolve(arg('--run-dir',path.join(root,'output/demo_launcher',new Date().toISOString().replace(/[:.]/g,'-'))));
const home=os.homedir(),appdata=process.env.APPDATA||path.join(home,'AppData/Roaming');
const locations={
 influx:'D:/iot2026/influxdb/influxdb3.exe',influxData:path.join(home,'.influxdb'),
 grafanaHome:'D:/iot2026/Grafana/grafana',node:process.execPath,
 python:path.join(home,'.platformio/penv/Scripts/python.exe'),
 nodeRed:path.join(appdata,'npm/node_modules/node-red/red.js'),nodeRedHome:path.join(home,'.node-red'),
 settings:path.join(home,'.node-red/settings-ku-watch.js'),cloud:path.join(root,'config/cloud.local.json')
};
const urls={grafana:'http://127.0.0.1:3000/d/ku-watch-live/ku-watch-e280a2-live-and-walk?from=now-15m&to=now&timezone=Asia%2FBangkok&refresh=1s&kiosk',dashboard:'http://127.0.0.1:1880/dashboard/page1',editor:'http://127.0.0.1:1880/'};
const definitions=[
 {id:'influx',label:'InfluxDB',port:8181,url:'http://127.0.0.1:8181/health'},
 {id:'queue',label:'Storage queue',port:8871,url:'http://127.0.0.1:8871/status'},
 {id:'node_red',label:'Node-RED',port:1880,url:urls.dashboard},
 {id:'grafana',label:'Grafana',port:3000,url:'http://127.0.0.1:3000/api/health'}
];
function request(url,{data,headers={},timeout=2500}={}){return new Promise(resolve=>{
 let complete=false;const finish=v=>{if(!complete){complete=true;resolve(v);}};
 const req=http.request(url,{method:data?'POST':'GET',headers:{...headers,...(data?{'Content-Type':'application/json'}:{})},timeout},res=>{
  let text='';res.setEncoding('utf8');res.on('data',c=>{if(text.length<200000)text+=c;});
  res.on('end',()=>{let body;try{body=JSON.parse(text);}catch{}finish({code:res.statusCode,body,text});});res.on('error',()=>finish({code:0}));
 });req.on('timeout',()=>req.destroy());req.on('error',()=>finish({code:0}));if(data)req.write(JSON.stringify(data));req.end();
});}
function portOpen(port){return new Promise(resolve=>{const socket=net.connect({host:'127.0.0.1',port});let done=false;const end=v=>{if(!done){done=true;socket.destroy();resolve(v);}};socket.setTimeout(700,()=>end(false));socket.on('connect',()=>end(true));socket.on('error',()=>end(false));});}
function classify(id,r){
 if(id==='grafana')return r.code===200&&r.body?.database==='ok';
 if(id==='queue')return r.code===200&&Number.isInteger(r.body?.pending)&&Number.isInteger(r.body?.written);
 if(id==='influx')return r.code>=200&&r.code<300;
 return r.code===200&&/<!doctype|<html|dashboard/i.test(r.text||'');
}
function publicService(id,r){const ready=classify(id,r);return {ready,http:r.code,detail:ready?'Ready':r.code===401||r.code===403?'Sign-in required':r.code?'Not ready':'Not running'};}
function readInfluxToken(){
 if(!influxToken){try{influxToken=/INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"/.exec(fs.readFileSync(path.join(root,'include/config.h'),'utf8'))?.[1]||'';}catch{}}
 return influxToken;
}
function serviceRequest(d){const token=d.id==='influx'?readInfluxToken():'';return request(d.url,token?{headers:{Authorization:'Bearer '+token}}:{});}
function observeLive(p,retained,m,now=Date.now()){
 if(retained){m.retained++;return;}
 if(!p||p.backfill===true){if(p?.backfill===true)m.backfill++;return;}
 if(!/^[a-f0-9]{8}-[a-f0-9]{8}$/i.test(p.sample_id||'')){m.invalid++;return;}
 if(m.seen.has(p.sample_id))return;m.seen.add(p.sample_id);if(m.seen.size>20000)m.seen.delete(m.seen.values().next().value);
 m.live++;m.last_receive_ms=now;m.capture_timestamp=Number.isSafeInteger(p.timestamp)?p.timestamp:null;
}
function liveSummary(m,now=Date.now()){
 const age=m.last_receive_ms===null?null:(now-m.last_receive_ms)/1000;
 const captureAge=m.capture_timestamp===null?null:now/1000-m.capture_timestamp;
 const receiving=age!==null&&age>=0&&age<=10;
 return {connected:m.connected,live_count:m.live,backfill_count:m.backfill,last_receive_utc:m.last_receive_ms===null?null:new Date(m.last_receive_ms).toISOString(),receive_age_s:age,capture_age_s:captureAge,
  fresh:m.connected&&receiving&&captureAge!==null&&captureAge>=-10&&captureAge<=15,clock_warning:receiving&&(captureAge===null||captureAge< -10||captureAge>15),error:m.error};
}
function newObservation(){return {connected:false,live:0,backfill:0,retained:0,invalid:0,last_receive_ms:null,capture_timestamp:null,seen:new Set(),error:null};}
const exists=p=>fs.existsSync(p);
function preflight(){return {root,paths:{influx:exists(locations.influx),existing_influx_data:exists(locations.influxData),grafana:exists(path.join(locations.grafanaHome,'bin/grafana.exe')),node_red:exists(locations.nodeRed),existing_node_red_settings:exists(locations.settings),python:exists(locations.python),cloud_settings:exists(locations.cloud),demo_launcher:exists(path.join(root,'tools/demo_launcher.ps1'))},urls};}
function selfTest(){const assert=require('node:assert/strict'),now=1800000000000,m=newObservation();m.connected=true;
 const sample={sample_id:'1234abcd-00000001',timestamp:now/1000};
 observeLive(sample,true,m,now);assert.equal(m.live,0);observeLive({...sample,backfill:true},false,m,now);assert.equal(m.live,0);assert.equal(m.backfill,1);
 observeLive(sample,false,m,now);observeLive(sample,false,m,now+1);assert.equal(m.live,1);assert.equal(liveSummary(m,now+1000).fresh,true);assert.equal(liveSummary(m,now+11000).fresh,false);
 m.connected=false;assert.equal(liveSummary(m,now+1000).fresh,false);m.connected=true;
 const stale=newObservation();observeLive({...sample,timestamp:now/1000-3600},false,stale,now);assert.equal(liveSummary(stale,now).fresh,false);assert.equal(liveSummary(stale,now).clock_warning,true);
 const future=newObservation();observeLive({...sample,timestamp:now/1000+300},false,future,now);assert.equal(liveSummary(future,now).fresh,false);
 assert.equal(classify('grafana',{code:200,body:{database:'error'}}),false);assert.equal(classify('queue',{code:200,body:{}}),false);assert.equal(classify('node_red',{code:200,text:'Unrelated API'}),false);
 console.log(JSON.stringify({passed:true,checks:['retained_is_not_live','backfill_is_not_live','duplicate_is_not_new','fresh_and_stale_boundaries','disconnected_is_not_ready','device_clock_mismatch','service_identity_guards'],network_used:false}));
}
if(process.argv.includes('--self-test')){selfTest();return;}
if(process.argv.includes('--preflight')){console.log(JSON.stringify(preflight()));return;}
if(!process.argv.includes('--start')&&!process.argv.includes('--probe'))throw Error('Use --start, --probe, --preflight or --self-test');
const shouldStart=process.argv.includes('--start');
const base=path.join(root,'output/demo_launcher');
if(shouldStart&&(!runDir.startsWith(base+path.sep)||runDir===base))throw Error('Run folder must be a dedicated child of output/demo_launcher');
let state={version:1,started_utc:new Date().toISOString(),updated_utc:null,pid:process.pid,phase:shouldStart?'starting':'checking',backend_ready:false,demo_ready:false,services:{},mqtt:{fresh:false},database:{available:false},urls,events:[]};
const activeFile=path.join(base,'active.json');let ownsLock=false,client,pollTimer;const observation=newObservation();
function publish(){state.updated_utc=new Date().toISOString();state.mqtt=liveSummary(observation);state.backend_ready=definitions.every(d=>state.services[d.id]?.ready);state.demo_ready=state.backend_ready&&state.mqtt.fresh&&state.database.fresh===true;
 if(shouldStart){const p=path.join(runDir,'status.json');fs.writeFileSync(p+'.tmp',JSON.stringify(state,null,2));fs.renameSync(p+'.tmp',p);} }
function event(service,message){state.events.push({utc:new Date().toISOString(),service,message});state.events=state.events.slice(-30);publish();}
function launch(id,executable,args,cwd){
 const log=fs.openSync(path.join(runDir,id+'.stdout.log'),'a'),err=fs.openSync(path.join(runDir,id+'.stderr.log'),'a');
 try{const child=spawn(executable,args,{cwd,detached:true,windowsHide:true,stdio:['ignore',log,err]});child.on('error',e=>event(id,'Could not start ('+(e.code||'process error')+').'));child.unref();event(id,'Starting existing service.');}finally{fs.closeSync(log);fs.closeSync(err);}
}
async function ensureService(d){
 let r=await serviceRequest(d);state.services[d.id]=publicService(d.id,r);publish();
 if(classify(d.id,r)){event(d.id,'Reused existing healthy service.');return;}
 if(await portOpen(d.port)){event(d.id,'Port is already occupied; did not start a duplicate. Check the existing application or sign-in.');return;}
 if(d.id==='influx'){
  if(!exists(locations.influx)||!exists(locations.influxData)){event(d.id,'Existing database installation/data folder not found.');return;}
  launch(d.id,locations.influx,['serve','--node-id','SSFOCUS-node','--object-store','file','--data-dir',locations.influxData,'--http-bind','127.0.0.1:8181'],path.dirname(locations.influx));
 }else if(d.id==='queue'){
  if(!exists(locations.python)){event(d.id,'Python runtime not found.');return;}
  launch(d.id,locations.python,[path.join(root,'tools/influx_queue.py')],root);
 }else if(d.id==='node_red'){
  if(!exists(locations.nodeRed)||!exists(locations.settings)){event(d.id,'Existing Node-RED installation/settings not found.');return;}
  const repair=spawnSync(locations.python,[path.join(root,'tools/repoint_backend.py')],{cwd:root,windowsHide:true,timeout:10000,stdio:'pipe'});
  if(repair.status!==0){event(d.id,'Existing settings paths could not be verified.');return;}
  launch(d.id,locations.node,[locations.nodeRed,'--userDir',locations.nodeRedHome,'--settings',locations.settings],root);
 }else{
  const exe=path.join(locations.grafanaHome,'bin/grafana.exe'),database=path.join(locations.grafanaHome,'data/grafana.db');
  if(!exists(exe)||!exists(database)){event(d.id,'Existing Grafana installation/database not found.');return;}
  launch(d.id,exe,['server','--homepath',locations.grafanaHome,'--config',path.join(locations.grafanaHome,'conf/custom.ini')],locations.grafanaHome);
 }
 const deadline=Date.now()+22000;
 do{await new Promise(r=>setTimeout(r,750));r=await serviceRequest(d);state.services[d.id]=publicService(d.id,r);publish();if(classify(d.id,r)){event(d.id,'Service is ready.');return;}}while(Date.now()<deadline);
 event(d.id,'Startup is taking longer than expected; keep checking readiness.');
}
let influxToken='';
async function checkDatabase(){
 if(!state.services.influx?.ready){state.database={available:false,fresh:false};return;}
 readInfluxToken();
 if(!influxToken){state.database={available:false,fresh:false,detail:'Database access is not configured locally.'};return;}
 const r=await request('http://127.0.0.1:8181/api/v3/query_sql',{timeout:4000,headers:{Authorization:'Bearer '+influxToken},data:{db:'iot',format:'json',q:"SELECT COUNT(*) AS rows, MAX(time) AS latest FROM ku_watch WHERE time > now() - INTERVAL '5 minutes'"}});
 if(r.code!==200||!Array.isArray(r.body)){state.database={available:false,fresh:false,detail:'Cannot confirm the latest database capture.'};return;}
 const row=r.body[0]||{},latest=row.latest?Date.parse(/Z$|[+-]\d\d:\d\d$/.test(row.latest)?row.latest:row.latest+'Z'):NaN,age=Number.isFinite(latest)?(Date.now()-latest)/1000:null;
 state.database={available:true,recent_rows:Number(row.rows)||0,latest_capture_utc:Number.isFinite(latest)?new Date(latest).toISOString():null,capture_age_s:age,fresh:age!==null&&age>=-10&&age<=30};
}
function startMqtt(){try{
 const cfg=JSON.parse(fs.readFileSync(locations.cloud,'utf8'));
 const mqtt=require(path.join(appdata,'npm/node_modules/node-red/node_modules/mqtt'));
 const {topic}=require(path.join(root,'tools/mqtt_topic.cjs'));
 // Subscribe explicitly on each connection. Disabling the library's duplicate
 // automatic resubscribe avoids its cached subscribe(null, []) callback being
 // mistaken for a refused subscription after a successful reconnect.
 client=mqtt.connect('mqtts://'+cfg.host+':8883',{username:cfg.reader_user,password:cfg.reader_password,clientId:'ku-demo-'+process.pid+'-'+Date.now().toString(16),rejectUnauthorized:true,reconnectPeriod:5000,connectTimeout:10000,resubscribe:false});
 client.on('connect',()=>{observation.connected=true;observation.error=null;publish();client.subscribe(topic,{qos:1},(e,grants)=>{observation.error=!e&&grants?.some(x=>x.qos!==128)?null:'MQTT subscription could not be confirmed.';publish();});});
 client.on('message',(_,raw,packet)=>{let p;try{p=JSON.parse(raw);}catch{return;}observeLive(p,packet.retain,observation);publish();});
 client.on('offline',()=>{observation.connected=false;publish();});client.on('error',()=>{observation.error='MQTT is not connected. Check the computer internet connection and local account settings.';publish();});
 }catch{observation.error='MQTT reader is not configured on this computer.';publish();}}
let polling=false;
async function poll(){if(polling)return;polling=true;try{const rs=await Promise.all(definitions.map(d=>serviceRequest(d)));rs.forEach((r,i)=>{state.services[definitions[i].id]=publicService(definitions[i].id,r);});await checkDatabase();publish();}catch{event('monitor','Readiness check will retry.');}finally{polling=false;}}
function finish(){if(pollTimer)clearInterval(pollTimer);if(client)client.end(true);if(ownsLock&&exists(activeFile)){try{if(JSON.parse(fs.readFileSync(activeFile)).pid===process.pid)fs.unlinkSync(activeFile);}catch{}}process.exit(0);}
process.on('SIGINT',finish);process.on('SIGTERM',finish);
(async()=>{
 if(!shouldStart){await poll();console.log(JSON.stringify(state));return;}
 fs.mkdirSync(runDir,{recursive:true});
 if(exists(activeFile)){let old;try{old=JSON.parse(fs.readFileSync(activeFile));}catch{throw Error('Unreadable existing launcher lock.');}try{process.kill(old.pid,0);throw Error('A demo worker is already running.');}catch(e){if(e.code!=='ESRCH')throw e;}}
 fs.writeFileSync(activeFile,JSON.stringify({pid:process.pid,run_dir:runDir,started_utc:state.started_utc}));ownsLock=true;publish();
 startMqtt();pollTimer=setInterval(()=>{void poll();},5000);
 for(const d of definitions)await ensureService(d);
 state.phase='running';await poll();event('demo','Startup checks finished. Live readings are only marked ready after fresh MQTT and database observations.');
})().catch(()=>{state.phase='error';state.error='Demo startup could not complete. See this session log folder; existing services were left running.';try{publish();}catch{}if(!shouldStart)process.exitCode=1;else finish();});
