// User logs into this dedicated browser manually; never read or print credentials.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),base=path.join(root,'output/presentation_media_20261016/live_capture');
const stamp=new Date().toISOString().replace(/[-:.]/g,''),out=path.join(base,stamp+'_grafana');fs.mkdirSync(out,{recursive:true});
const profile=path.join(root,'output/presentation_evidence/actual_tools/.capture-private');
const report={started_utc:new Date().toISOString(),status:'opening',boundary:'Actual Grafana UI recording and screenshots; user enters existing login manually. Does not establish measured display latency, endurance or a full requirements pass.',images:[]};
const save=()=>fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify({...report,updated_utc:new Date().toISOString()},null,2));
const hash=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
(async()=>{let ctx,video;
 try{
  ctx=await chromium.launchPersistentContext(profile,{executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:false,viewport:{width:1600,height:1000},args:['--window-size=1640,1100']});
  let pg=ctx.pages()[0]||await ctx.newPage();const live='http://127.0.0.1:3000/d/ku-watch-live?from=now-5m&to=now&timezone=Asia%2FBangkok&refresh=1s';
  await pg.goto(live,{waitUntil:'domcontentloaded',timeout:20000});
  if(new URL(pg.url()).pathname.startsWith('/login')){report.status='waiting_for_user_login';save();console.log(JSON.stringify({status:report.status,folder:out}));const deadline=Date.now()+8*60*1000;while(new URL(pg.url()).pathname.startsWith('/login')&&Date.now()<deadline)await pg.waitForTimeout(2000);if(new URL(pg.url()).pathname.startsWith('/login')){report.status='needs_login';return;}}
  await pg.goto(live,{waitUntil:'domcontentloaded'});await pg.waitForTimeout(5000);
  // Enable recording only after login, so no authentication dialog or typed password is recorded.
  await ctx.close();ctx=null;
  ctx=await chromium.launchPersistentContext(profile,{executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,viewport:{width:1600,height:1000},recordVideo:{dir:out,size:{width:1600,height:1000}}});
  pg=ctx.pages()[0]||await ctx.newPage();video=pg.video();await pg.goto(live,{waitUntil:'domcontentloaded'});await pg.waitForTimeout(4000);if(new URL(pg.url()).pathname.startsWith('/login'))throw Error('Login session unavailable for capture');
  report.status='recording';report.recording_started_utc=new Date().toISOString();save();console.log(JSON.stringify({status:report.status,folder:out}));
  for(let i=0;i<6;i++){const name=`Grafana_live_${i*10}s.png`,f=path.join(out,name);await pg.screenshot({path:f,fullPage:false});report.images.push({file:name,captured_utc:new Date().toISOString(),url:pg.url(),sha256:hash(f)});await pg.waitForTimeout(10000);}
  // Existing panel IDs from this dashboard, read-only navigation.
  for(const [id,label] of [[15,'temperature'],[16,'humidity'],[74,'iaq']]){await pg.goto(live+'&viewPanel='+id+'&kiosk',{waitUntil:'domcontentloaded'});await pg.waitForTimeout(3500);const name='Grafana_'+label+'.png',f=path.join(out,name);await pg.screenshot({path:f,fullPage:false});report.images.push({file:name,captured_utc:new Date().toISOString(),url:pg.url(),sha256:hash(f),visual_review:'pending'});}
  const rawVideoPath=await video.path();await ctx.close();ctx=null;const dest=path.join(out,'Grafana_actual_live.webm');fs.copyFileSync(rawVideoPath,dest);video=null;report.video={file:path.basename(dest),sha256:hash(dest)};report.status='captured';
 }catch(e){report.status='error';report.error=e.message;console.error(e.message);}
 finally{if(ctx)await ctx.close().catch(()=>{});report.finished_utc=new Date().toISOString();save();console.log(JSON.stringify({status:report.status,folder:out,images:report.images.length}));}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
