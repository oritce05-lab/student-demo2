# מכין טיזר מכתבה: חיתוך קטעים לפריימים, פסקול (קול מקורי + מוזיקה), וקובץ נתונים לסצנה.
# שימוש: python3 build.py teaser-duel.json <source.mp4>
import json, os, subprocess, sys, wave
import numpy as np

spec_path, src = sys.argv[1], sys.argv[2]
name = os.path.splitext(os.path.basename(spec_path))[0]
spec = json.load(open(spec_path))
FPS, SR = 30, 44100
CROP = 'crop=620:356:74:0,scale=1080:-2:flags=lanczos,unsharp=5:5:0.5,eq=contrast=1.05:saturation=1.08'
if spec.get('layout') == 'wide':
    CROP = 'scale=1920:1080:flags=lanczos,unsharp=5:5:0.5,eq=contrast=1.05:saturation=1.08'
root = f'assets/{name}'
os.makedirs(root, exist_ok=True)

def run(*a):
    subprocess.run(a, check=True, stderr=subprocess.DEVNULL)

def audio(start, dur):
    tmp = f'{root}/tmp.wav'
    run('ffmpeg', '-y', '-ss', str(start), '-t', str(dur), '-i', src, '-vn', '-ac', '2', '-ar', str(SR), tmp)
    with wave.open(tmp) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float32) / 32768
    os.remove(tmp)
    n = int(dur * SR)
    return np.pad(a, ((0, max(0, n - len(a))), (0, 0)))[:n]

t, speech, speechmask, cuts = 0.0, [], [], []
for i, s in enumerate(spec['segments']):
    s['t'] = t
    cuts.append(t)
    out_dur = s['dur'] / s.get('speed', 1) if s['type'] == 'clip' else s['dur']
    s['out'] = out_dur
    if s['type'] == 'clip' or s.get('bg'):
        a, d = (s['from'], s['dur']) if s['type'] == 'clip' else s['bg']
        d_dir = f'{root}/{i:02d}'
        os.makedirs(d_dir, exist_ok=True)
        sp = s.get('speed', 1)
        if not os.environ.get('AUDIO_ONLY'): run('ffmpeg', '-y', '-ss', str(a), '-t', str(d), '-i', src, '-vf', f'setpts=PTS/{sp},fps={FPS},{CROP}', '-q:v', '3', f'{d_dir}/%04d.jpg')
        s['dir'] = d_dir
        s['frames'] = len(os.listdir(d_dir))
    n = int(out_dur * SR)
    if s['type'] == 'clip' and s.get('speed', 1) == 1:
        speech.append(audio(s['from'], s['dur'])); speechmask.append(np.ones(n))
    else:
        speech.append(np.zeros((n, 2))); speechmask.append(np.zeros(n))
    t += out_dur

total = t
sp = np.concatenate(speech)
mask = np.concatenate(speechmask)
# מוזיקה: music.py עם נקודות מעבר
hits = ','.join(f'{c:.2f}' for c in cuts[1:])
run('python3', '-I', '../robots/music.py', f'{total:.2f}', f'{root}/music.wav', hits)
with wave.open(f'{root}/music.wav') as w:
    mu = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float32) / 32768
mu = np.pad(mu, ((0, max(0, len(sp) - len(mu))), (0, 0)))[:len(sp)]
# דאקינג חלק של המוזיקה מתחת לדיבור
k = int(0.25 * SR)
env = np.convolve(mask, np.ones(k) / k, mode='same')
gain = 0.95 - env * 0.78
mix = sp * 1.15 + mu * gain[:, None]
mix /= max(1.0, np.abs(mix).max() * 1.02)
os.makedirs('../robots/assets', exist_ok=True)
with wave.open(f'assets/music-{name}.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
open(f'{name}-data.js', 'w').write('window.EDIT = ' + json.dumps({'total': total, 'calm': True, 'segments': spec['segments']}, ensure_ascii=False, indent=1) + ';\n')
print(name, f'{total:.1f}s', [round(c, 2) for c in cuts])
