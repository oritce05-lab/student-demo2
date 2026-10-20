// הפקת סרטון: node render.mjs [scene.html|reel.html] [--preview t1,t2,...]
// כל פריים מצולם מקובץ הסצנה ונשלח ל-ffmpeg. אם קיים assets/music.wav והסצנה היא reel – הפסקול משולב.
import { spawn } from 'node:child_process';
import { dirname, join, basename } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import { mkdirSync, existsSync } from 'node:fs';

const ROOT = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
let pw;
for (const p of ['playwright', '/opt/node-tools/node_modules/playwright']) { try { pw = require(p); break; } catch {} }
const FPS = 30;
const args = process.argv.slice(2);
const scene = args.find((a) => a.endsWith('.html')) || 'scene.html';
const pi = args.indexOf('--preview');
const previewTimes = pi >= 0 ? (args[pi + 1] || '1,3,6,9,12,15,18,21').split(',').map(Number) : null;
const name = basename(scene, '.html') === 'reel' ? 'robots-reel' : 'robots-construction';

const browser = await pw.chromium.launch(existsSync('/opt/pw-browsers/chromium') ? { executablePath: '/opt/pw-browsers/chromium' } : {});
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
page.on('pageerror', (e) => console.error('JS error:', e.message));
await page.goto(pathToFileURL(join(ROOT, scene)).href);
const [w, h] = await page.evaluate(() => window.SIZE || [1920, 1080]);
await page.setViewportSize({ width: w, height: h });
await page.evaluate(() => document.fonts.ready);
const duration = await page.evaluate(() => window.DURATION);
mkdirSync(join(ROOT, 'output'), { recursive: true });

if (previewTimes) {
  for (const t of previewTimes) {
    await page.evaluate((t) => window.render(t), t);
    await page.screenshot({ path: join(ROOT, 'output', `preview-${name}-${String(t).replace('.', '_')}.jpg`), type: 'jpeg', quality: 80 });
  }
  await browser.close();
  process.exit(0);
}

const out = join(ROOT, 'output', `${name}.mp4`);
const music = join(ROOT, 'assets', 'music.wav');
const withAudio = name === 'robots-reel' && existsSync(music);
const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
  ...(withAudio ? ['-i', music, '-c:a', 'aac', '-b:a', '192k', '-shortest'] : []),
  '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });

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
