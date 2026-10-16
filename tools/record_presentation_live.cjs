// Capture only an actual current device stream. No generated data or state changes.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..');
const base=path.join(root,'output/presentation_media_20261016/live_capture');fs.mkdirSync(base,{recursive:true});
const lock=path.join(base,'active.json');
if(fs.existsSync(lock)){const old=JSON.parse(fs.readFileSync(lock));try{process.kill(old.pid,0);throw Error('Capture already running');}catch(e){if(e.code!=='ESRCH')throw e;}}
const token=/INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"/.exec(fs.readFileSync(path.join(root,'include/config.h'),'utf8'))?.[1];
if(!token)throw Error('Existing DB access not configured');
const started=new Date(),out=path.join(base,started.toISOString().replace(/[-:.]/g,''));fs.mkdirSync(out);
const report={started_utc:started.toISOString(),pid:process.pid,status:'waiting_for_actual_data',boundary:'Actual native Node-RED dashboard and InfluxDB response. Not a physical LCD mirror or full requirements pass. No generated measurements. No GPS coordinates or raw PPG stored.',images:[],observations:[]};
const save=()=>fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify({...report,updated_utc:new Date().toISOString()},null,2));
fs.writeFileSync(lock,JSON.stringify({pid:process.pid,folder:out}));save();
async function query(q){const r=await fetch('http://127.0.0.1:8181/api/v3/query_sql',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({db:'iot',q,format:'json'}),signal:AbortSignal.timeout(6000)});if(!r.ok)throw Error('Influx HTTP '+r.status);return r.json();}
const latestQ='SELECT time,sample_id,temp,humidity,iaq,battery_voltage FROM ku_watch ORDER BY time DESC LIMIT 1';
function age(row){return row?.time?(Date.now()-Date.parse(row.time.endsWith('Z')?row.time:row.time+'Z'))/1000:Infinity;}
const hash=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
async function shot(page,name,caption){const f=path.join(out,name);await page.screenshot({path:f,fullPage:false});report.images.push({file:name,captured_utc:new Date().toISOString(),caption,url:page.url(),sha256:hash(f)});save();}
async function main(){let browser,ctx,video;
 try{
  let firstId=null,ready=false;const waitUntil=Date.now()+90000;
  while(Date.now()<waitUntil){const rows=await query(latestQ);const row=rows[0];if(age(row)>=-5&&age(row)<20){if(firstId&&row.sample_id!==firstId){ready=true;break;}firstId=row.sample_id;}await new Promise(r=>setTimeout(r,3000));}
  if(!ready){report.status='waiting_for_device';report.reason='No fresh progressing device sample IDs during bounded 90-second wait.';save();console.log(JSON.stringify({status:report.status,folder:out}));return;}
  browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  ctx=await browser.newContext({viewport:{width:1600,height:1000},recordVideo:{dir:out,size:{width:1600,height:1000}}});
  const page=await ctx.newPage();video=page.video();await page.goto('http://127.0.0.1:1880/dashboard/page1',{waitUntil:'domcontentloaded',timeout:20000});await page.waitForTimeout(3000);
  await page.getByText('Trends',{exact:true}).evaluate(e=>e.scrollIntoView({block:'start'}));
  report.status='recording';report.recording_started_utc=new Date().toISOString();save();console.log(JSON.stringify({status:report.status,folder:out}));
  for(let i=0;i<6;i++){const rows=await query(latestQ);report.observations.push({queried_utc:new Date().toISOString(),row:rows[0],age_s:age(rows[0])});await shot(page,`NodeRED_${i*10}s.png`,'Actual current Node-RED Trends view');await page.waitForTimeout(10000);}
  await ctx.close();ctx=null;const vf=path.join(out,'NodeRED_actual_live.webm');await video.saveAs(vf);report.video={file:path.basename(vf),sha256:hash(vf)};video=null;
  const proofCtx=await browser.newContext({viewport:{width:1600,height:1000},extraHTTPHeaders:{Authorization:'Bearer '+token}});
  await proofCtx.route('**/*',r=>new URL(r.request().url()).origin==='http://127.0.0.1:8181'?r.continue():r.abort());
  const dbPage=await proofCtx.newPage();
  const q="SELECT COUNT(*) AS stored_rows,COUNT(DISTINCT sample_id) AS unique_samples,MIN(time) AS first_utc,MAX(time) AS last_utc FROM ku_watch WHERE time >= now()-INTERVAL '5 minutes'";
  const url='http://127.0.0.1:8181/api/v3/query_sql?'+new URLSearchParams({db:'iot',q,format:'json'});const res=await dbPage.goto(url,{waitUntil:'domcontentloaded'});if(res.ok()){fs.writeFileSync(path.join(out,'influx_actual_response.json'),JSON.stringify(JSON.parse(await res.text()),null,2));await shot(dbPage,'Influx_actual_5min.png','Actual InfluxDB SQL response; not a full 5-minute delivery acceptance test');}
  await proofCtx.close();
  const gf=await browser.newContext({viewport:{width:1600,height:1000}});const gp=await gf.newPage();await gp.goto('http://127.0.0.1:3000/d/ku-watch-live?from=now-5m&to=now&timezone=Asia%2FBangkok&refresh=1s',{waitUntil:'domcontentloaded'});await gp.waitForTimeout(3000);
  if(new URL(gp.url()).pathname.startsWith('/login'))report.grafana='needs_existing_user_login; no screenshot taken';else await shot(gp,'Grafana_actual_live.png','Actual Grafana current dashboard');await gf.close();
  report.fresh_sample_progressed=new Set(report.observations.map(x=>x.row?.sample_id)).size>1;
  report.all_observations_fresh=report.observations.every(x=>x.age_s>=-5&&x.age_s<20);report.status='captured';
 }catch(e){report.status='error';report.error=e.message;console.error(e.message);}
 finally{if(ctx)await ctx.close().catch(()=>{});if(video)await video.saveAs(path.join(out,'NodeRED_partial.webm')).catch(()=>{});if(browser)await browser.close().catch(()=>{});report.finished_utc=new Date().toISOString();save();if(fs.existsSync(lock)&&JSON.parse(fs.readFileSync(lock)).pid===process.pid)fs.unlinkSync(lock);console.log(JSON.stringify({status:report.status,folder:out,images:report.images.length}));}
}
main();
