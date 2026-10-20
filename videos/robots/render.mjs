// הפקת סרטון: node render.mjs [--preview]
// כל פריים מצולם מ-scene.html ונשלח ל-ffmpeg. --preview מפיק רק תמונות לבדיקה.
import { spawn } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import { mkdirSync, existsSync } from 'node:fs';

const ROOT = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
let pw;
for (const p of ['playwright', '/opt/node-tools/node_modules/playwright']) { try { pw = require(p); break; } catch {} }
const FPS = 30;
const preview = process.argv.includes('--preview');

const browser = await pw.chromium.launch(existsSync('/opt/pw-browsers/chromium') ? { executablePath: '/opt/pw-browsers/chromium' } : {});
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
page.on('pageerror', (e) => console.error('JS error:', e.message));
await page.goto(pathToFileURL(join(ROOT, 'scene.html')).href);
await page.evaluate(() => document.fonts.ready);
const duration = await page.evaluate(() => window.DURATION);
mkdirSync(join(ROOT, 'output'), { recursive: true });

if (preview) {
  for (const t of [2.5, 7, 14, 19, 22.5, 28, 36.5, 42]) {
    await page.evaluate((t) => window.render(t), t);
    await page.screenshot({ path: join(ROOT, 'output', `preview-${String(t).replace('.', '_')}.jpg`), type: 'jpeg', quality: 80 });
  }
  await browser.close();
  process.exit(0);
}

const out = join(ROOT, 'output', 'robots-construction.mp4');
const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
  '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });

const total = Math.round(duration * FPS);
for (let i = 0; i < total; i++) {
  await page.evaluate((t) => window.render(t), i / FPS);
  const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
  if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
  if (i % 150 === 0) console.log(`${i}/${total}`);
}
ff.stdin.end();
await new Promise((r) => ff.on('close', r));
await browser.close();
console.log('✓', out);
