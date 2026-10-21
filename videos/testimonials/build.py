# סרטון המלצות: עריכה נקייה של שתי המלצות לסרטון אחד.
# חיתוך רק בתוך שתיקות (≥0.4 שנ', מקוצרות ל-0.18 שנ'), זום מתחלף עדין להסתרת החיתוכים,
# מעבר רך בין הדוברים, ניקוי רעשים, איזון עוצמות ומוזיקה עדינה ברקע.
import subprocess, sys
VERTICAL = '--tiktok' in sys.argv  # גרסה אנכית 1080x1920
from PIL import Image
U = '/root/.claude/uploads/c00d9c52-64e7-5c47-9b43-a60e46d2a6ce/'
CLIPS = {
    # [התחלה, סוף] של כל קטע דיבור, אחרי הסרת השתיקות
    'man': (U + '1461c0ba-WhatsApp_Video_2026-10-21_at_11.13.55.mp4',
            [(0.45, 2.10), (2.43, 7.03), (7.27, 12.07), (12.63, 13.97), (14.49, 16.53), (16.95, 17.91), (18.39, 20.27), (20.49, 23.30)]),
    'woman': (U + 'baf57236-WhatsApp_Video_2026-10-21_at_11.13.47.mp4',
              [(0.30, 12.51), (12.77, 21.23), (21.47, 24.95)]),
}
ORDER = ['man', 'woman']
XF = 0.6          # מעבר בין הדוברים
END_CARD = 3.0
W, H = (1080, 1920) if VERTICAL else (1920, 1080)

# כרטיס סיום: לוגו היחידה על רקע לבן
img = Image.new('RGB', (W, H), 'white')
logo = Image.open('../../brochures/assets/logo-full.png').convert('RGBA')
logo.thumbnail((900 if VERTICAL else 1100, 400))
img.paste(logo, ((W - logo.width) // 2, (H - logo.height) // 2), logo)
EC = 'endcard-v.png' if VERTICAL else 'endcard.png'
img.save(EC)

inputs, fc, people = [], [], []
for pi, name in enumerate(ORDER):
    src, segs = CLIPS[name]
    inputs += ['-i', src]
    labels = []
    for si, (a, b) in enumerate(segs):
        z = 1.0 if si % 2 == 0 else 1.07
        sw, sh = int(W * z) // 2 * 2, int(H * z) // 2 * 2
        if VERTICAL:
            # מרכז: חיתוך 3:4 של הדובר; למעלה ולמטה: אותו צילום מטושטש וכהה
            cw = 540 / z
            fc.append(f'[{pi}:v]trim={a}:{b},setpts=PTS-STARTPTS,fps=30,split[sa{pi}_{si}][sb{pi}_{si}]')
            fc.append(f'[sa{pi}_{si}]crop={cw:.0f}:{576 / z:.0f}:(iw-{cw:.0f})/2:(ih-{576 / z:.0f})/2,scale=1080:1152:flags=lanczos,unsharp=5:5:0.5,setsar=1[fg{pi}_{si}]')
            fc.append(f'[sb{pi}_{si}]scale=-2:1920,crop=1080:1920,boxblur=28:2,eq=brightness=-0.18:saturation=0.9,setsar=1[bg{pi}_{si}]')
            fc.append(f'[bg{pi}_{si}][fg{pi}_{si}]overlay=0:384,format=yuv420p,settb=1/30[v{pi}_{si}]')
        else:
            fc.append(f'[{pi}:v]trim={a}:{b},setpts=PTS-STARTPTS,fps=30,scale={sw}:{sh}:flags=lanczos,crop={W}:{H},setsar=1,format=yuv420p,settb=1/30[v{pi}_{si}]')
        fc.append(f'[{pi}:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,afade=t=out:st={b - a - 0.04:.2f}:d=0.04[a{pi}_{si}]')
        labels.append(f'[v{pi}_{si}][a{pi}_{si}]')
    fc.append(f'{"".join(labels)}concat=n={len(segs)}:v=1:a=1[pvc{pi}][pa_raw{pi}]')
    fc.append(f'[pvc{pi}]settb=1/30[pv{pi}]')
    # ניקוי רעשים ואיזון עוצמה לכל דובר
    fc.append(f'[pa_raw{pi}]highpass=f=90,lowpass=f=11000,afftdn=nf=-28:nr=14,dynaudnorm=f=200:g=11,loudnorm=I=-16:TP=-1.5:LRA=7,aresample=44100[pa{pi}]')
    people.append(sum(b - a for a, b in segs))

d0, d1 = people
total = d0 + d1 - XF
inputs += ['-loop', '1', '-t', str(END_CARD + 1), '-i', EC]
ei = len(ORDER)
fc.append(f'[pv0][pv1]xfade=transition=fade:duration={XF}:offset={d0 - XF:.3f}[vp]')
fc.append(f'[pa0][pa1]acrossfade=d={XF}[speech]')
fc.append(f'[{ei}:v]fps=30,scale={W}:{H},setsar=1,format=yuv420p,trim=0:{END_CARD + 0.6},setpts=PTS-STARTPTS,settb=1/30[ec]')
fc.append(f'[vp][ec]xfade=transition=fade:duration=0.6:offset={total - 0.6:.3f},fade=t=in:d=0.4[v]')
full = total + END_CARD
subprocess.run(['python3', '-I', 'music-soft.py', f'{full:.2f}', 'music.wav'], check=True)
inputs += ['-i', 'music.wav']
mi = ei + 1
# מוזיקה נמוכה מתחת לדיבור, עולה בכרטיס הסיום
fc.append(f"[{mi}:a]volume='if(lt(t,{total:.2f}),0.16,0.16+0.5*min(1,(t-{total:.2f})/0.8))':eval=frame[mus]")
fc.append(f'[speech]apad=pad_dur={END_CARD + 1}[sp]')
fc.append('[sp][mus]amix=inputs=2:duration=shortest:normalize=0,alimiter=limit=0.95[a]')
cmd = ['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '[a]',
       '-t', f'{full:.2f}', '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p',
       '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', 'output/testimonials-tiktok.mp4' if VERTICAL else 'output/testimonials.mp4']
subprocess.run(cmd, check=True)
print('✓', cmd[-1], round(full, 1), 's')
