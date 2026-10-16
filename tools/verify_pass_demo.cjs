const fs = require('fs');
const path = require('path');
const {pathToFileURL} = require('url');
const {chromium} = require('C:/Users/pomma/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const crypto = require('crypto');
const root = path.resolve(__dirname,'..');
const out = path.join(root,'output/demo_20261011');
const statusFile = path.join(root,'output/soak_audit/status.json');
const digest = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
async function main() {
  const statusBefore = digest(statusFile);
  const browser = await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
  const errors=[];
  const results=[];
  try {
    for (const [width,theme] of [[736,'light'],[360,'light'],[736,'dark']]) {
      const page = await browser.newPage({viewport:{width,height:1100},colorScheme:theme,deviceScaleFactor:1});
      page.on('pageerror',e=>errors.push(e.message));
      await page.goto(pathToFileURL(path.join(out,'preview.html')).href);
      const frame=page.frames().find(f=>f!==page.mainFrame());
      if(!frame) throw Error('Missing preview frame');
      await frame.waitForSelector('#ku-watch-pass-preview');
      const check=()=>frame.evaluate(()=>{
        const r=document.getElementById('ku-watch-pass-preview');
        const rect=r.getBoundingClientRect();
        const label=r.querySelector('.ku-demo').textContent;
        const footer=r.querySelector('.ku-foot').textContent;
        return {fits: r.scrollWidth<=rect.width+1, mock_label:label.includes('ข้อมูลจำลอง'), footer_disclosure:footer.includes('ข้อมูลสมมติ')};
      });
      const passed=await check();
      if(!passed.fits||!passed.mock_label||!passed.footer_disclosure)throw Error('Mockup failed bounds or disclosure check');
      await frame.locator('#ku-watch-pass-preview').screenshot({path:path.join(out,`pass-demo-${width}-${theme}.png`)});
      await frame.locator('#ku-battery-tab').click();
      if(!await frame.locator('#ku-battery-panel').isVisible()||await frame.locator('#ku-pass-panel').isVisible())throw Error('Battery tab did not update');
      const battery=await check();
      if(!battery.fits)throw Error('Battery layout overflow');
      await frame.locator('#ku-pass-tab').click();
      if(!await frame.locator('#ku-pass-panel').isVisible())throw Error('Return tab did not update');
      results.push({width,theme,passed,battery,interaction_passed:true});
      await page.close();
    }
  } finally {await browser.close();}
  if(errors.length)throw Error(errors.join('\n'));
  const validation={data_type:'simulated',purpose:'Preview of how a successful test report could look; not hardware test evidence',results,script_errors:errors,actual_audit_unchanged:statusBefore===digest(statusFile),actual_audit_status:JSON.parse(fs.readFileSync(statusFile)).status};
  if(!validation.actual_audit_unchanged)throw Error('Actual audit was changed');
  fs.writeFileSync(path.join(out,'validation.json'),JSON.stringify(validation,null,2));
  console.log(JSON.stringify(validation));
}
main().catch(e=>{console.error(e);process.exitCode=1;});
