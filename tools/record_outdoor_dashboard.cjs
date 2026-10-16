// A bounded recording of the actual local Node-RED dashboard, plus read-only SQL snapshots.
// No generated measurements, browser credentials, wearer coordinates, or raw PPG.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),base=path.join(root,'output/outdoor_capture');fs.mkdirSync(base,{recursive:true});
const lock=path.join(base,'active.json');
if(fs.existsSync(lock)){const old=JSON.parse(fs.readFileSync(lock));try{process.kill(old.pid,0);throw Error('Outdoor recording already running');}catch(e){if(e.code!=='ESRCH')throw e;}}
const started=new Date(),stamp=started.toISOString().replace(/[-:.]/g,''),out=path.join(base,stamp);fs.mkdirSync(out,{recursive:true});
const token=/INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"/.exec(fs.readFileSync(path.join(root,'include/config.h'),'utf8'))?.[1];
if(!token)throw Error('Database access not configured');
const requestedSeconds=Number(process.argv[2]||900);
if(!Number.isFinite(requestedSeconds)||requestedSeconds<60||requestedSeconds>1200)throw Error('Recording duration must be 60..1200 seconds');
const duration=requestedSeconds*1000,deadline=Date.now()+duration;
const report={pid:process.pid,started_utc:started.toISOString(),planned_duration_s:duration/1000,status:'starting',boundary:'Actual Node-RED Trends page video and screenshots; SQL values are read-only. Does not mirror the physical hub LCD and does not establish a full requirements pass. Watch Preview, if visible, is an older saved photo.',screenshots:[],snapshots:[]};
fs.writeFileSync(lock,JSON.stringify({pid:process.pid,folder:path.relative(root,out),deadline_utc:new Date(deadline).toISOString()}));
const save=()=>fs.writeFileSync(path.join(out,'status.json'),JSON.stringify({...report,updated_utc:new Date().toISOString()},null,2));
async function query(sql){const response=await fetch('http://127.0.0.1:8181/api/v3/query_sql',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({db:'iot',q:sql,format:'json'}),signal:AbortSignal.timeout(8000)});if(!response.ok)throw Error('Database HTTP '+response.status);return response.json();}
let stopping=false;process.on('SIGINT',()=>stopping=true);process.on('SIGTERM',()=>stopping=true);
async function main(){
 let browser,context,page,video;
 try{
  browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  context=await browser.newContext({viewport:{width:1600,height:1000},recordVideo:{dir:out,size:{width:1600,height:1000}}});
  page=await context.newPage();video=page.video();
  await page.goto('http://127.0.0.1:1880/dashboard/page1',{waitUntil:'domcontentloaded',timeout:20000});await page.waitForTimeout(4000);
  await page.getByText('Trends',{exact:true}).evaluate(el=>el.scrollIntoView({block:'start'}));
  report.status='recording';save();console.log(JSON.stringify({status:report.status,folder:path.relative(root,out),deadline_utc:new Date(deadline).toISOString()}));
  let index=0,nextCapture=0;
  while(Date.now()<deadline&&!stopping&&!fs.existsSync(path.join(out,'STOP'))){
   if(Date.now()>=nextCapture){
    const now=new Date(),prefix=String(index++).padStart(2,'0')+'_'+now.toISOString().replace(/[-:.]/g,'');
    const file=prefix+'.png';await page.screenshot({path:path.join(out,file),fullPage:false});
    report.screenshots.push({file,captured_utc:now.toISOString(),captured_thai:new Intl.DateTimeFormat('th-TH',{timeZone:'Asia/Bangkok',dateStyle:'long',timeStyle:'medium'}).format(now),url:page.url(),sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(out,file))).digest('hex'),visual_review:'pending'});
    try{const sql='SELECT time,sample_id,temp,humidity,pressure,iaq,battery_voltage,gps_fix,recording,elapsed_s,distance_m FROM ku_watch ORDER BY time DESC LIMIT 3';const rows=await query(sql);const jf=prefix+'.json';fs.writeFileSync(path.join(out,jf),JSON.stringify({queried_utc:new Date().toISOString(),sql,rows},null,2));report.snapshots.push({file:jf,last_data_utc:rows[0]?.time,recording:rows[0]?.recording,gps_fix:rows[0]?.gps_fix});}catch(e){report.last_query_error=e.message;}
    nextCapture=Date.now()+60000;
   }
   save();await page.waitForTimeout(5000);
  }
  report.status=stopping?'stopped':'completed';
 }catch(e){report.status='error';report.error=e.message;}
 finally{
  if(context)await context.close().catch(()=>{});
  if(video){const name='NodeRED_actual_outdoor.webm';await video.saveAs(path.join(out,name)).then(()=>report.video=name).catch(e=>report.video_error=e.message);}
  if(browser)await browser.close().catch(()=>{});
  report.finished_utc=new Date().toISOString();save();
  if(fs.existsSync(lock)&&JSON.parse(fs.readFileSync(lock)).pid===process.pid)fs.unlinkSync(lock);
  console.log(JSON.stringify({status:report.status,folder:path.relative(root,out),screenshots:report.screenshots.length,video:report.video,error:report.error}));
 }
}
save();main();
