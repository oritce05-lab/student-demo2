# פסקול שביעי: פאנקי-האוס / ניו-דיסקו 122 BPM – בס אוקטבות דיסקו, סטאבים מסוננים, היי-האט פתוח באוף-ביט, קלאפ (A מינור).
# בר ראשון בלי קיק (בלי מכת פתיחה), עוצמה מתונה. שימוש: python3 music7.py <משך> <פלט>
import sys
import wave
import numpy as np

SR = 44100
BPM = 122
BEAT = 60 / BPM
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 24.0
OUT = sys.argv[2] if len(sys.argv) > 2 else 'assets/music-smallspace.wav'
END = DUR - 3.0
N = int(SR * DUR)
out = np.zeros(N)
rng = np.random.default_rng(67)


def place(sig, at, gain=1.0):
    i = int(at * SR)
    if 0 <= i < N:
        j = min(N, i + len(sig))
        out[i:j] += sig[: j - i] * gain


def env(n, a=0.002, d=8.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t * d)


def lowpass(x, a):
    y = np.zeros_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc); y[i] = acc
    return y


def stab(freqs, length, cut):
    n = int(SR * length); t = np.arange(n) / SR
    s = sum(2 * ((f * d * t) % 1) - 1 for f in freqs for d in (0.996, 1.004)) / (2 * len(freqs))
    return lowpass(s * env(n, 0.003, 9), cut)


def kick():
    t = np.arange(int(SR * 0.3)) / SR
    return np.sin(2 * np.pi * np.cumsum(50 + 100 * np.exp(-t * 40)) / SR) * np.exp(-t * 10)


def clap():
    n = int(SR * 0.22)
    s = np.diff(rng.standard_normal(n + 1))
    e = sum(env(n, 0.001, 70) * (np.arange(n) >= int(SR * d)) for d in (0, 0.011, 0.022)) + env(n, 0.001, 16) * 0.5
    return s * e * 0.45


def hat(open_=False):
    n = int(SR * (0.2 if open_ else 0.035))
    s = np.diff(rng.standard_normal(n + 1))
    return s * env(n, 0.001, 15 if open_ else 90) * 0.4


def bass(f, length):
    n = int(SR * length); t = np.arange(n) / SR
    s = 2 * ((f * t) % 1) - 1
    return lowpass(s * env(n, 0.003, 9), 0.06) * 2.2


# Am – F – C – G
CH = [[440.0, 523.25, 659.25], [349.23, 440.0, 523.25], [392.0, 523.25, 659.25], [392.0, 493.88, 587.33]]
RT = [55.0, 43.65, 65.41, 49.0]
BAR = 4 * BEAT
S16 = BEAT / 4
bar = 0
while bar * BAR < END:
    a = bar * BAR; c = CH[bar % 4]; r = RT[bar % 4]
    cut = 0.04 + 0.12 * min(1, bar / 4)          # הפילטר נפתח בהדרגה
    for st in (2, 6, 10, 14, 15):                # סטאבים סינקופטיים
        place(stab(c, S16 * 1.6, cut), a + st * S16, 0.5)
    for q in range(4):
        at = a + q * BEAT
        place(hat(True), at + BEAT / 2, 0.28)
        place(hat(), at + S16, 0.1); place(hat(), at + 3 * S16, 0.1)
        if bar >= 1:
            place(kick(), at, 0.8)
            if q in (1, 3): place(clap(), at, 0.5)
            # בס דיסקו: אוקטבה נמוכה-גבוהה בשמיניות
            place(bass(r, BEAT / 2 * 0.8), at, 0.5)
            place(bass(r * 2, BEAT / 2 * 0.8), at + BEAT / 2, 0.42)
    bar += 1

place(stab(CH[0], 2.2, 0.16), END, 0.6)
place(bass(RT[0], 1.4), END, 0.6); place(kick(), END, 0.7)

t_all = np.arange(N) / SR
out *= np.clip((DUR - t_all) / 1.5, 0, 1) * np.clip(t_all / 0.4, 0, 1)
out = out / np.max(np.abs(out)) * 0.5        # עוצמה מתונה, בלי דחיסה
stereo = np.stack([out, np.roll(out, 170)], axis=1)
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((stereo * 32767).astype(np.int16).tobytes())
print(OUT, DUR, 's')
