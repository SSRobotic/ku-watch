import fs from 'node:fs/promises';
import path from 'node:path';
const root='C:/Users/pomma/OneDrive/Desktop/02_Projects/KU_Watch_Display_First';
const b=path.join(root,'output/canva_presentation_20261015/build_v2');
const pages=JSON.parse(await fs.readFile(path.join(b,'canva_pages.json'),'utf8')).items;
await fs.mkdir(path.join(b,'canva'),{recursive:true});
const rs=await Promise.allSettled(pages.map(async p=>{const r=await fetch(p.thumbnail.url);if(!r.ok)throw Error(p.index+': HTTP '+r.status);await fs.writeFile(path.join(b,'canva',`slide-${String(p.index).padStart(2,'0')}.png`),new Uint8Array(await r.arrayBuffer()));return p.index;}));
console.log(JSON.stringify(rs));
