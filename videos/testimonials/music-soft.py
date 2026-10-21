# מוזיקת רקע עדינה (בלי תופים): פד אקורדים רך + נקישות פסנתר עם הד. מסונתז בקוד, בלי בעיית זכויות.
# שימוש: python3 music-soft.py <משך> <קובץ פלט>
import sys, wave
import numpy as np
SR = 44100
DUR = float(sys.argv[1]); OUT = sys.argv[2]
N = int(SR * DUR); t = np.arange(N) / SR
out = np.zeros(N)
BAR = 3.2  # ~75 BPM, אקורד לכל בר
CH = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [261.63, 329.63, 392.0], [196.0, 246.94, 293.66]]  # Am F C G
def place(sig, at, g):
    i = int(at * SR); j = min(N, i + len(sig))
    if i < N: out[i:j] += sig[: j - i] * g
bar = 0
while bar * BAR < DUR:
    a = bar * BAR; c = CH[bar % 4]
    n = int(SR * (BAR + 1.0)); tt = np.arange(n) / SR
    env = np.minimum(1, tt / 0.9) * np.exp(-tt * 0.35)
    pad = sum(np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.003 * tt) for f in c) * env
    place(pad, a, 0.09)
    for k, f in enumerate([c[0] * 2, c[1] * 2, c[2] * 2, c[1] * 2]):
        m = int(SR * 1.6); tm = np.arange(m) / SR
        bell = (np.sin(2 * np.pi * f * tm) + 0.25 * np.sin(2 * np.pi * f * 3 * tm)) * np.exp(-tm * 3.2) * np.minimum(1, tm / 0.004)
        place(bell, a + k * BAR / 4, 0.05)
    bass = np.sin(2 * np.pi * c[0] / 2 * tt) * env
    place(bass, a, 0.08)
    bar += 1
# הד פשוט
d = int(0.32 * SR); wet = np.zeros(N)
for k, g in ((1, .35), (2, .18), (3, .09)):
    wet[d * k:] += out[:-d * k] * g
out = out + wet
out *= np.clip(t / 2.0, 0, 1) * np.clip((DUR - t) / 2.5, 0, 1)
out /= np.max(np.abs(out)) * 1.1
st = np.stack([out, np.roll(out, 200)], axis=1)
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print(OUT, DUR)
