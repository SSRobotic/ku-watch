const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'output/presentation_media_20261016/backend_details');fs.mkdirSync(out,{recursive:true});
const token=/INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"/.exec(fs.readFileSync(path.join(root,'include/config.h'),'utf8'))?.[1];
const report={captured_utc:new Date().toISOString(),type:'ACTUAL_TOOL_SCREENSHOTS',images:[],boundary:'Read-only current Node-RED editor and real InfluxDB SQL API. Browser native JSON pretty print and view zoom only; no changed data.'};
const hash=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
(async()=>{const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});try{
 const ctx=await browser.newContext({viewport:{width:1600,height:1000}}),pg=await ctx.newPage();await pg.goto('http://127.0.0.1:1880/',{waitUntil:'networkidle'});await pg.waitForTimeout(1500);
 await pg.screenshot({path:path.join(out,'NodeRED_actual_flow.png'),fullPage:false});report.images.push({file:'NodeRED_actual_flow.png',sha256:hash(path.join(out,'NodeRED_actual_flow.png')),captured_utc:new Date().toISOString(),url:pg.url()});await ctx.close();
 const db=await browser.newContext({viewport:{width:1600,height:1000},extraHTTPHeaders:{Authorization:'Bearer '+token}});await db.route('**/*',r=>new URL(r.request().url()).origin==='http://127.0.0.1:8181'?r.continue():r.abort());const p=await db.newPage();
 for(const [name,q] of [['Influx_actual_rows','SELECT time,sample_id,temp,humidity,iaq,battery_voltage FROM ku_watch ORDER BY time DESC LIMIT 3'],['Influx_actual_counts',"SELECT COUNT(*) AS stored_rows,COUNT(DISTINCT sample_id) AS unique_samples,MIN(time) AS first_utc,MAX(time) AS last_utc FROM ku_watch WHERE time >= now()-INTERVAL '5 minutes'"]]){
  const url='http://127.0.0.1:8181/api/v3/query_sql?'+new URLSearchParams({db:'iot',q,format:'json'});const r=await p.goto(url,{waitUntil:'domcontentloaded'});if(!r.ok())throw Error('Influx HTTP '+r.status());const raw=await r.text();fs.writeFileSync(path.join(out,name+'.json'),JSON.stringify(JSON.parse(raw),null,2));fs.writeFileSync(path.join(out,name+'.sql'),q+'\n');
  const controls=p.getByRole('checkbox');if(await controls.count())await controls.first().check();
  await p.locator('body').evaluate(e=>{e.style.zoom='180%';});await p.waitForTimeout(500);const file=name+'.png';await p.screenshot({path:path.join(out,file),fullPage:false});report.images.push({file,sha256:hash(path.join(out,file)),captured_utc:new Date().toISOString(),sql:q,url:p.url(),native_pretty_print:await controls.count()>0});
 }await db.close();report.status='captured';
 }catch(e){report.status='error';report.error=e.message;}finally{await browser.close();fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({status:report.status,images:report.images.map(x=>({file:x.file,pretty:x.native_pretty_print})),error:report.error}));}})();
