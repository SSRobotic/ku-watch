// Actual read-only dashboard captures. No service changes or generated values.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'output/ppt_academic_20261016/build/dashboard');fs.mkdirSync(out,{recursive:true});
const report={started_utc:new Date().toISOString(),boundary:'Read-only real browser screenshots. Full viewport for each panel, no chart cropping. Current values may be missing indoors or without skin contact; screenshots do not establish calibration or battery endurance.',panels:[],pages:[]};
const save=()=>fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify(report,null,2));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
(async()=>{let ctx;try{
 ctx=await chromium.launchPersistentContext(path.join(root,'output/presentation_evidence/actual_tools/.capture-private'),{executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,viewport:{width:1600,height:1000}});
 const page=ctx.pages()[0]||await ctx.newPage();
 const base='http://127.0.0.1:3000/d/ku-watch-live/ku-watch-e280a2-live-and-walk?from=2026-10-16T07:00:00.000Z&to=2026-10-16T10:00:00.000Z&timezone=Asia%2FBangkok';
 await page.goto(base,{waitUntil:'domcontentloaded',timeout:25000});await page.waitForTimeout(4000);if(new URL(page.url()).pathname.startsWith('/login'))throw Error('Existing dedicated Grafana login required');
 const dashboard=await page.evaluate(async()=>{const r=await fetch('/api/dashboards/uid/ku-watch-live');if(!r.ok)throw Error('Dashboard HTTP '+r.status);return (await r.json()).dashboard;});
 const flatten=xs=>xs.flatMap(x=>[x,...flatten(x.panels||[])]);const panels=flatten(dashboard.panels).filter(x=>x.type!=='row');
 report.panel_count=panels.length;
 for(const p of panels){
  const file='Grafana_panel_'+String(p.id).padStart(2,'0')+'.png';const url=base+'&viewPanel='+p.id+'&kiosk';
  await page.goto(url,{waitUntil:'domcontentloaded',timeout:20000});await page.waitForTimeout(p.type==='timeseries'?1800:1000);
  await page.screenshot({path:path.join(out,file),fullPage:false});report.panels.push({file,panel_id:p.id,title:p.title,type:p.type,url,captured_utc:new Date().toISOString(),sha256:hash(path.join(out,file)),visual_review:'pending'});save();
  if(report.panels.length%10===0)console.log(JSON.stringify({panels:report.panels.length,total:panels.length}));
 }
 await page.goto(base,{waitUntil:'domcontentloaded',timeout:20000});await page.waitForTimeout(3000);
 const total=await page.evaluate(()=>Math.max(document.body.scrollHeight,document.documentElement.scrollHeight));
 for(let y=0,i=1;y<Math.min(total,18000);y+=800,i++){
  await page.evaluate(y=>window.scrollTo(0,y),y);await page.waitForTimeout(600);const file='Grafana_overview_'+String(i).padStart(2,'0')+'.png';await page.screenshot({path:path.join(out,file)});report.pages.push({file,service:'Grafana',scroll_y:y,captured_utc:new Date().toISOString(),sha256:hash(path.join(out,file))});
 }
 await page.goto('http://127.0.0.1:1880/dashboard/page1',{waitUntil:'domcontentloaded',timeout:20000});await page.waitForTimeout(2500);
 const h=await page.evaluate(()=>Math.max(document.body.scrollHeight,document.documentElement.scrollHeight));
 for(let y=0,i=1;y<Math.min(h,12000);y+=800,i++){
  await page.evaluate(y=>window.scrollTo(0,y),y);await page.waitForTimeout(500);const file='NodeRED_page_'+String(i).padStart(2,'0')+'.png';await page.screenshot({path:path.join(out,file)});report.pages.push({file,service:'Node-RED',scroll_y:y,captured_utc:new Date().toISOString(),sha256:hash(path.join(out,file))});
 }
 report.status='completed';
 }catch(e){report.status='error';report.error=e.message;console.error(e.message);}finally{if(ctx)await ctx.close().catch(()=>{});report.finished_utc=new Date().toISOString();save();console.log(JSON.stringify({status:report.status,panels:report.panels.length,pages:report.pages.length,error:report.error}));}})();
