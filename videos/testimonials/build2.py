# המלצות – עריכה בפורמט שאלה–תשובה, אנכי 1080x1920 (כמו המקור), כתוביות בעברית, מוזיקה קצבית ברקע.
# קודם: python3 transcribe… (לא חובה), node captions.mjs ; אחר כך: python3 build2.py
import json, subprocess
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

fc, cat, t, events = [], [], 0.0, []
for i, (n, a, b, caps) in enumerate(E['pieces']):
    si = names.index(n); d = b - a
    z = 1.0 if i % 2 == 0 else 1.08          # זום מתחלף בכל חיתוך
    fc.append(f'[{si}:v]trim={a}:{b},setpts=PTS-STARTPTS,fps={FPS},scale={int(W*z)//2*2}:{int(H*z)//2*2}:flags=lanczos,'
              f'crop={W}:{H}:(iw-{W})/2:(ih-{H})/3,unsharp=5:5:0.4,setsar=1,format=yuv420p,settb=1/{FPS}[v{i}]')
    fc.append(f'[{si}:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,afade=t=out:st={d-0.05:.2f}:d=0.05[a{i}]')
    cat.append(f'[v{i}][a{i}]')
    for c in caps: events.append((t + c[0], t + min(c[1], d), c[3]))
    t += d
total = t
fc.append(f'{"".join(cat)}concat=n={len(E["pieces"])}:v=1:a=1[vc0][ac]')
fc.append(f'[vc0]settb=1/{FPS}[vc]')
fc.append('[ac]highpass=f=90,lowpass=f=11000,afftdn=nf=-28:nr=14,dynaudnorm=f=200:g=11,loudnorm=I=-15:TP=-1.5:LRA=7,aresample=44100[speech]')

# כתוביות: הראשונה היא כותרת ההוק (למעלה), השאר בתחתית
k = len(names)
inputs += ['-loop', '1', '-t', str(total + END_CARD), '-i', 'work/endcard.png']; ec = k; k += 1
last = 'vc'
hook_end = E['pieces'][0][2] - E['pieces'][0][1]
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
subprocess.run(['python3', '-I', '../robots/music.py', f'{full:.2f}', 'work/music.wav', '99'], check=True)
inputs += ['-i', 'work/music.wav']
fc.append(f"[{k}:a]volume='if(lt(t,{total - XF:.2f}),0.15,0.15+0.35*min(1,(t-{total - XF:.2f})/0.6))':eval=frame[mus]")
fc.append(f'[speech]apad=pad_dur={END_CARD + 1}[sp]')
fc.append('[sp][mus]amix=inputs=2:duration=shortest:normalize=0,alimiter=limit=0.95[a]')
out = 'output/testimonials-tiktok.mp4'
subprocess.run(['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '[a]', '-t', f'{full:.2f}',
                '-c:v', 'libx264', '-crf', '19', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out], check=True)
print('✓', out, round(full, 1), 's')
