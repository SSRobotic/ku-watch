// Backfill belongs in history, never in live gauges or the current GPS marker.
const p=msg.payload;
if(!p || typeof p!=='object' || Array.isArray(p))return null;
return p.backfill===true ? [msg,null] : [msg,msg];
