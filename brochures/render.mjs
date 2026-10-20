// הפקת ידיעון: node render.mjs <course-folder> [...]
// לדוגמה: node render.mjs courses/site-supervisor
// התוצרים: output/<id>.html (תצוגה מקדימה) ו-output/<id>.pdf
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { resolve, dirname, basename, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const ROOT = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

function loadPlaywright() {
  for (const p of ['playwright', '/opt/node-tools/node_modules/playwright']) {
    try { return require(p); } catch {}
  }
  throw new Error('Playwright לא נמצא. התקינו: npm i playwright');
}

const dirs = process.argv.slice(2);
if (!dirs.length) {
  console.error('שימוש: node render.mjs courses/<course-folder> [...]');
  process.exit(1);
}

const { chromium } = loadPlaywright();
const launch = existsSync('/opt/pw-browsers/chromium') ? { executablePath: '/opt/pw-browsers/chromium' } : {};
const browser = await chromium.launch(launch).catch(() => chromium.launch());
mkdirSync(join(ROOT, 'output'), { recursive: true });
let failed = false;

for (const dir of dirs) {
  const courseDir = resolve(ROOT, dir);
  const course = JSON.parse(readFileSync(join(courseDir, 'course.json'), 'utf8'));
  const id = course.id || basename(courseDir);
  const rel = courseDir.slice(ROOT.length + 1).replace(/\\/g, '/') + '/';

  const html = `<!doctype html>
<html lang="he" dir="rtl"><head><meta charset="utf-8">
<base href="../">
<title>${course.title}</title>
<link rel="stylesheet" href="template/brochure.css">
${course.theme ? `<style>:root{${Object.entries(course.theme).map(([k, v]) => `--${k}:${v};`).join('')}}</style>` : ''}
</head><body><div id="root"></div>
<script>window.COURSE = ${JSON.stringify(course)}; window.COURSE_BASE = ${JSON.stringify(rel)};</script>
<script src="template/brochure.js"></script>
</body></html>`;
  const htmlPath = join(ROOT, 'output', `${id}.html`);
  writeFileSync(htmlPath, html);

  const page = await browser.newPage();
  page.on('pageerror', (e) => { console.error(`[${id}] JS error:`, e.message); failed = true; });
  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  const overflow = await page.evaluate(() => window.checkOverflow ? window.checkOverflow() : []);
  if (overflow.length) {
    failed = true;
    for (const o of overflow) console.warn(`[${id}] ⚠ עמוד ${o.page}: התוכן גולש ב-${Math.round(o.overflowPx)}px – יש לקצר או לפצל`);
  }
  // לא מדפיסים את המסגרת האדומה של גלישה ל-PDF
  await page.evaluate(() => document.querySelectorAll('.page.overflow').forEach((p) => p.classList.remove('overflow')));
  const pdfPath = join(ROOT, 'output', `${id}.pdf`);
  await page.pdf({ path: pdfPath, preferCSSPageSize: true, printBackground: true });
  if (process.env.SCREENSHOTS) {
    await page.setViewportSize({ width: 820, height: 1200 });
    const n = await page.locator('.page').count();
    mkdirSync(join(ROOT, 'output', 'preview', id), { recursive: true });
    for (let i = 0; i < n; i++) {
      await page.locator('.page').nth(i).screenshot({ path: join(ROOT, 'output', 'preview', id, `${String(i + 1).padStart(2, '0')}.png`) });
    }
  }
  console.log(`✓ ${id}: ${pdfPath}`);
  await page.close();
}

await browser.close();
process.exit(failed ? 2 : 0);
