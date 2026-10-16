const fs=require('fs'),assert=require('assert');
const src=fs.readFileSync('integration/node-red/environment_alert.vue','utf8').split('<script>')[1].split('</script>')[0];
const ui=new Function(src.replace('export default','return'))();
function status(p,age=0){const ctx={p,now:1790123456000+age*1000};ctx.fresh=ui.computed.fresh.call(ctx);return [ui.methods.text.call(ctx,'alert_temp_state'),ui.methods.level.call(ctx,'alert_temp_state')];}
assert.deepEqual(status({timestamp:1790123456,alert_temp_state:2}),['เกินเกณฑ์','high']);
assert.deepEqual(status({timestamp:1790123456,alert_temp_state:0}),['รอเซ็นเซอร์พร้อม','waiting']);
assert.deepEqual(status({timestamp:1790123456,alert_temp_state:2},16),['รอข้อมูลล่าสุด','waiting']);
assert.deepEqual(status({timestamp:1790123456,alert_temp_state:2,backfill:true}),['รอข้อมูลล่าสุด','waiting']);
assert.deepEqual(status({timestamp:null,alert_temp_state:2}),['รอข้อมูลล่าสุด','waiting']);
console.log('Alert live-card: high/warming/stale/backfill/unclocked behavior passed');
const simulation='output/acceptance/alert_simulation.json';
if(fs.existsSync(simulation)){
    const proof=JSON.parse(fs.readFileSync(simulation,'utf8'));
    assert.equal(proof.samples.length,3);
    for(let n=0;n<proof.samples.length;n++){
        const p=proof.samples[n],ctx={p,now:p.timestamp*1000};
        ctx.fresh=ui.computed.fresh.call(ctx);
        assert.equal(ui.methods.level.call(ctx,'alert_temp_state'),n===2?'high':'normal');
        assert.equal(ui.methods.level.call(ctx,'alert_iaq_state'),n===2?'high':'normal');
    }
    assert(proof.trigger_ms<=5000);
    console.log('Production dashboard methods match the three-sample simulation; DOM paint and network latency are not claimed.');
}
