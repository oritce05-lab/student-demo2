// מרנדר כל כתובית לתמונה שקופה: work/cap-XX.png
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { readFileSync, writeFileSync } from 'node:fs';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node-tools/node_modules/playwright');
const E = JSON.parse(readFileSync('edit.json', 'utf8'));
const items = [{ text: E.hook, cls: 'hook' }];
E.pieces.forEach((p) => p[3].forEach((c) => items.push({ text: c[2], cls: c[3] === 'q' ? 'q' : '' })));
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const pg = await b.newPage({ viewport: { width: 1080, height: 800 } });
await pg.goto(pathToFileURL(process.cwd() + '/caption.html').href);
await pg.evaluate(() => document.fonts.ready);
const meta = [];
for (let i = 0; i < items.length; i++) {
  await pg.evaluate(([t, c]) => { const e = document.getElementById('c'); e.textContent = t; e.className = c; }, [items[i].text, items[i].cls]);
  const el = pg.locator('#c');
  await el.screenshot({ path: `work/cap-${String(i).padStart(2, '0')}.png`, omitBackground: true });
  const bb = await el.boundingBox(); meta.push({ w: Math.round(bb.width), h: Math.round(bb.height) });
}
writeFileSync('work/captions.json', JSON.stringify(meta));
await b.close();
console.log(items.length, 'captions');
