// All current observers use the configured topic; older installations keep their fallback.
const fs=require('fs'),path=require('path');
const configFile=path.join(__dirname,'../config/cloud.local.json');
const cfg=fs.existsSync(configFile)?JSON.parse(fs.readFileSync(configFile,'utf8')):{};
const topic=cfg.topic||'ku_watch/live';
if(typeof topic!=='string'||!topic.length||/[+#\s]/.test(topic))throw Error('Invalid configured telemetry topic');
module.exports={topic,statusTopic:topic+'/status'};
