const fs=require('fs'),path=require('path'),crypto=require('crypto'),cp=require('child_process');
const {chromium}=require('C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'..'),base=path.join(root,'output/presentation_media_20261016/live_capture');
const source=path.join(base,'20261016T073857510Z_grafana');
const old=JSON.parse(fs.readFileSync(path.join(source,'manifest.json')));
const out=path.join(base,new Date().toISOString().replace(/[-:.]/g,'')+'_grafana');fs.mkdirSync(out);
const hash=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const report={started_utc:new Date().toISOString(),recording_started_utc:old.recording_started_utc,status:'preparing',boundary:old.boundary,images:[],recovery:{original_manifest:path.relative(root,path.join(source,'manifest.json')),original_manifest_sha256:hash(path.join(source,'manifest.json')),original_job_status:old.status,original_job_error:old.error,explanation:'Browser API saveAs failed after recording. The actual raw WebM was complete; it is preserved and independently checked with ffprobe. MP4 is trimmed from that unmodified recording.'}};
const save=()=>fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify({...report,updated_utc:new Date().toISOString()},null,2));
save();
(async()=>{let ctx;try{
 const raw=fs.readdirSync(source).filter(f=>f.startsWith('page@')&&f.endsWith('.webm'));if(raw.length!==1)throw Error('Expected one actual recording');const sourceVideo=path.join(source,raw[0]);
 const probe=JSON.parse(cp.execFileSync('ffprobe',['-v','error','-show_entries','format=duration:stream=codec_name,width,height','-of','json',sourceVideo],{encoding:'utf8'}));
 if(Number(probe.format.duration)<65||probe.streams[0].width!==1600)throw Error('Raw recording incomplete');
 report.recovery.raw_video={source:path.relative(root,sourceVideo),sha256:hash(sourceVideo),duration_s:Number(probe.format.duration)};
 const vf=path.join(out,'Grafana_สด_16ตุลา2569_60วินาที.mp4');
 cp.execFileSync('ffmpeg',['-hide_banner','-loglevel','error','-n','-ss','4.5','-i',sourceVideo,'-t','60','-an','-c:v','libx264','-preset','fast','-crf','24','-pix_fmt','yuv420p','-movflags','+faststart',vf]);
 const verified=JSON.parse(cp.execFileSync('ffprobe',['-v','error','-show_entries','format=duration','-of','json',vf],{encoding:'utf8'}));if(Math.abs(Number(verified.format.duration)-60)>.1)throw Error('Incorrect MP4 duration');
 report.video={file:path.basename(vf),sha256:hash(vf),duration_s:Number(verified.format.duration),source_start_s:4.5,playback_speed:1};
 for(const name of ['Grafana_live_0s.png','Grafana_live_50s.png','Grafana_temperature.png','Grafana_humidity.png']){const r=old.images.find(x=>x.file===name);if(!r||hash(path.join(source,name))!==r.sha256)throw Error('Source image mismatch');fs.copyFileSync(path.join(source,name),path.join(out,name));report.images.push({...r,source_file:path.relative(root,path.join(source,name))});}
 // The prior file named iaq actually showed panel28 (GPS status). Preserve it but exclude it.
 report.recovery.excluded_mislabeled_image={source:'Grafana_iaq.png',actual_panel:28,actual_title:'สถานะตำแหน่ง',reason:'IAQ is panel74; take a new correctly identified screenshot.'};
 const profile=path.join(root,'output/presentation_evidence/actual_tools/.capture-private');ctx=await chromium.launchPersistentContext(profile,{executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,viewport:{width:1600,height:1000}});
 const pg=ctx.pages()[0]||await ctx.newPage();
 for(const [id,label,title] of [[74,'iaq','IAQ ย้อนหลัง'],[25,'acceleration','การเคลื่อนไหว 3 แกน • ค่าดิบ'],[82,'battery_voltage','แรงดันแบตเตอรี่ย้อนหลัง'],[85,'iaq_alert','แจ้งเตือน IAQ']]){
 const url='http://127.0.0.1:3000/d/ku-watch-live?from=now-5m&to=now&timezone=Asia%2FBangkok&refresh=1s&viewPanel='+id+'&kiosk';await pg.goto(url,{waitUntil:'domcontentloaded',timeout:20000});await pg.waitForTimeout(3500);if(new URL(pg.url()).pathname.startsWith('/login'))throw Error('Existing Grafana login required');
 const file='Grafana_'+label+'.png';await pg.screenshot({path:path.join(out,file),fullPage:false});report.images.push({file,captured_utc:new Date().toISOString(),url:pg.url(),panel_id:id,expected_panel_title:title,sha256:hash(path.join(out,file)),visual_review:'pending'});save();}
 report.status='captured';
 }catch(e){report.status='error';report.error=e.message;console.error(e.message);}finally{if(ctx)await ctx.close().catch(()=>{});report.finished_utc=new Date().toISOString();save();console.log(JSON.stringify({status:report.status,folder:out,images:report.images.length,video:report.video?.file,error:report.error}));}})();
