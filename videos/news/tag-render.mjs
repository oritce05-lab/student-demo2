// מרנדר את התגית לתמונה שקופה (ברזולוציה כפולה)
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node-tools/node_modules/playwright');
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const p = await b.newPage({ deviceScaleFactor: 2 });
await p.goto(pathToFileURL(process.cwd() + '/tag.html').href);
await p.evaluate(() => document.fonts.ready);
await p.locator('#t').screenshot({ path: 'assets/tag.png', omitBackground: true });
await b.close();
