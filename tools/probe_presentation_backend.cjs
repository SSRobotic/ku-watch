const fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'..');
async function main(){
 const result={checked_utc:new Date().toISOString(),services:{}};
 for(const [name,url] of [['grafana','http://127.0.0.1:3000/api/health'],['nodered','http://127.0.0.1:1880/']]){
  try{const r=await fetch(url,{signal:AbortSignal.timeout(4000)});result.services[name]={http:r.status};}catch(e){result.services[name]={online:false};}
 }
 const cfg=fs.readFileSync(path.join(root,'include/config.h'),'utf8');
 const token=/INFLUX_TOKEN\[\]\s*=\s*"([^"\n]+)"/.exec(cfg)?.[1];
 if(token){
  try{
   const q="SELECT time, sample_id, temp, humidity, iaq, battery_voltage FROM ku_watch ORDER BY time DESC LIMIT 3";
   const r=await fetch('http://127.0.0.1:8181/api/v3/query_sql',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({db:'iot',q,format:'json'}),signal:AbortSignal.timeout(7000)});
   result.services.influx={http:r.status};
   if(r.ok){const rows=await r.json();result.latest=rows;const t=rows[0]?.time;if(t){const utc=t.endsWith('Z')?t:t+'Z';result.last_data_age_s=(Date.now()-Date.parse(utc))/1000;result.fresh=result.last_data_age_s>=-5&&result.last_data_age_s<20;}}
  }catch(e){result.services.influx={online:false,error:e.message};}
 }
 const out=path.join(root,'output/presentation_media_20261016');fs.mkdirSync(out,{recursive:true});fs.writeFileSync(path.join(out,'backend_probe_latest.json'),JSON.stringify(result,null,2));
 console.log(JSON.stringify(result));
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
