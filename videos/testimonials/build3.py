# המלצות v3 – חיתוך שתיקות ארוכות בתוך קטע (רק בשתיקה), כתוביות לפי זמן מקור, מוזיקה music3.py.
# המלצות – עריכה בפורמט שאלה–תשובה, אנכי 1080x1920 (כמו המקור), כתוביות בעברית, מוזיקה קצבית ברקע.
# קודם: python3 transcribe… (לא חובה), node captions.mjs ; אחר כך: python3 build2.py
import json, subprocess, sys, wave
import numpy as np
from PIL import Image
E = json.load(open('edit.json'))
SRC = json.load(open('sources.json'))
CAPS = json.load(open('work/captions.json'))
W, H, FPS = 1080, 1920, 30
END_CARD, XF = 2.6, 0.4
names = list(SRC)
inputs = []
for n in names: inputs += ['-i', SRC[n]]

# כרטיס סיום
img = Image.new('RGB', (W, H), 'white')
logo = Image.open('../../brochures/assets/logo-full.png').convert('RGBA'); logo.thumbnail((900, 400))
img.paste(logo, ((W - logo.width) // 2, (H - logo.height) // 2), logo); img.save('work/endcard.png')

def pauses(n, min_len=0.75):
    w = wave.open(f'work/{n}.wav'); x = np.frombuffer(w.readframes(w.getnframes()), np.int16) / 32768; sr = w.getframerate()
    fr = int(sr * 0.02); k = len(x) // fr
    quiet = 20 * np.log10(np.sqrt((x[:k * fr].reshape(k, fr) ** 2).mean(1)) + 1e-9) < -40
    out, i = [], 0
    while i < k:
        if quiet[i]:
            j = i
            while j < k and quiet[j]: j += 1
            if (j - i) * 0.02 >= min_len: out.append((i * 0.02, j * 0.02))
            i = j
        else: i += 1
    return out
P = {n: pauses(n) for n in names}

def keep(n, a, b, pad=0.2):
    # מסיר שתיקות ארוכות בתוך הקטע, משאיר 0.2 שנ' שקט בכל צד – אף מילה לא נחתכת
    segs, cur = [], a
    for p0, p1 in P[n]:
        if p0 > a + 0.1 and p1 < b - 0.1:
            segs.append((cur, p0 + pad)); cur = p1 - pad
    return segs + [(cur, b)]

fc, cat, t, events, cnt = [], [], 0.0, [], 0
for n, a, b, caps in E['pieces']:
    si = names.index(n); segs = keep(n, a, b); starts = []
    for (s0, s1) in segs:
        d = s1 - s0; i = cnt; cnt += 1; starts.append((s0, s1, t))
        z = 1.0 if i % 2 == 0 else 1.08          # זום מתחלף בכל חיתוך
        fc.append(f'[{si}:v]trim={s0:.3f}:{s1:.3f},setpts=PTS-STARTPTS,fps={FPS},scale={int(W*z)//2*2}:{int(H*z)//2*2}:flags=lanczos,'
                  f'crop={W}:{H}:(iw-{W})/2:(ih-{H})/3,unsharp=5:5:0.4,setsar=1,format=yuv420p,settb=1/{FPS}[v{i}]')
        fc.append(f'[{si}:a]atrim={s0:.3f}:{s1:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,afade=t=out:st={d-0.05:.3f}:d=0.05[a{i}]')
        cat.append(f'[v{i}][a{i}]'); t += d
    def m(x):  # זמן מקור -> זמן פלט
        for s0, s1, o in starts:
            if x <= s1: return o + max(0, x - s0)
        return starts[-1][2] + starts[-1][1] - starts[-1][0]
    for c in caps: events.append((m(c[0]), m(c[1]), c[3]))
    print(n, a, b, [(round(x, 2), round(y, 2)) for x, y in segs])
total = t
fc.append(f'{"".join(cat)}concat=n={cnt}:v=1:a=1[vc0][ac]')
fc.append(f'[vc0]settb=1/{FPS}[vc]')
fc.append('[ac]highpass=f=90,lowpass=f=11000,afftdn=nf=-28:nr=14,dynaudnorm=f=200:g=11,loudnorm=I=-15:TP=-1.5:LRA=7,aresample=44100[speech]')

# כתוביות: הראשונה היא כותרת ההוק (למעלה), השאר בתחתית
k = len(names)
inputs += ['-loop', '1', '-t', str(total + END_CARD), '-i', 'work/endcard.png']; ec = k; k += 1
last = 'vc'
hook_end = E.get('hook_until', 4.0)
cap_list = [(0.05, hook_end, 'hook')] + events
for j, (s0, s1, sp) in enumerate(cap_list):
    inputs += ['-i', f'work/cap-{j:02d}.png']
    w_, h_ = CAPS[j]['w'], CAPS[j]['h']
    y = 300 if sp == 'hook' else 1400
    fc.append(f'[{last}][{k}:v]overlay=x=({W}-overlay_w)/2:y={y}:enable=\'between(t,{s0:.2f},{s1:.2f})\'[o{j}]')
    last = f'o{j}'; k += 1
fc.append(f'[{ec}:v]fps={FPS},scale={W}:{H},setsar=1,format=yuv420p,trim=0:{END_CARD + XF},setpts=PTS-STARTPTS,settb=1/{FPS}[ecv]')
fc.append(f'[{last}][ecv]xfade=transition=fade:duration={XF}:offset={total - XF:.3f}[v]')
full = total + END_CARD
NOMUSIC = '--no-music' in sys.argv   # גרסה בלי מוזיקת רקע: רק הדיבור
fc.append(f'[speech]apad=pad_dur={END_CARD + 1}[sp]')
if NOMUSIC:
    fc.append('[sp]alimiter=limit=0.95[a]')
else:
    subprocess.run(['python3', '-I', 'music3.py', f'{full:.2f}', 'work/music.wav'], check=True)
    inputs += ['-i', 'work/music.wav']
    fc.append(f"[{k}:a]volume='if(lt(t,{total - XF:.2f}),0.15,0.15+0.35*min(1,(t-{total - XF:.2f})/0.6))':eval=frame[mus]")
    fc.append('[sp][mus]amix=inputs=2:duration=shortest:normalize=0,alimiter=limit=0.95[a]')
out = 'output/testimonials-tiktok-nomusic.mp4' if NOMUSIC else 'output/testimonials-tiktok.mp4'
subprocess.run(['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '[a]', '-t', f'{full:.2f}',
                '-c:v', 'libx264', '-crf', '19', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out], check=True)
print('✓', out, round(full, 1), 's')
