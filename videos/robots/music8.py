# פסקול שמיני: EDM מדליק 128 BPM – בילד-אפ מסונן עם ריזר, דרופ בזמן החשיפה, אקורדי סאו עם סייד-צ'יין, ליד פלאק וקיק חזק (F# מינור).
# הפתיחה בלי תופים (רק פד ופלאק מסוננים + ריזר), המכה הראשונה בדרופ. עוצמה מתונה.
# שימוש: python3 music8.py <משך> <פלט> <זמן דרופ>
import sys
import wave
import numpy as np

SR = 44100
BPM = 128
BEAT = 60 / BPM
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 24.0
OUT = sys.argv[2] if len(sys.argv) > 2 else 'assets/music-smallspace2.wav'
DROP = float(sys.argv[3]) if len(sys.argv) > 3 else 3.75
END = DUR - 3.4
N = int(SR * DUR)
out = np.zeros(N)
rng = np.random.default_rng(83)


def place(sig, at, gain=1.0):
    i = int(at * SR)
    if 0 <= i < N:
        j = min(N, i + len(sig))
        out[i:j] += sig[: j - i] * gain


def env(n, a=0.002, d=8.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t * d)


def lowpass(x, a):
    a = np.broadcast_to(np.asarray(a, float), x.shape)
    y = np.zeros_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc); y[i] = acc
    return y


def saw_chord(freqs, length, cut, dec=3.0):
    n = int(SR * length); t = np.arange(n) / SR
    s = sum(2 * ((f * d * t) % 1) - 1 for f in freqs for d in (0.993, 1.0, 1.007)) / (3 * len(freqs))
    return lowpass(s * env(n, 0.004, dec), cut)


def pluck(f, length=0.25, cut=0.3):
    n = int(SR * length); t = np.arange(n) / SR
    s = (2 * ((f * t) % 1) - 1) * 0.6 + np.sign(np.sin(2 * np.pi * f * t)) * 0.4
    return lowpass(s * env(n, 0.001, 14), cut)


def kick():
    t = np.arange(int(SR * 0.4)) / SR
    return np.tanh(np.sin(2 * np.pi * np.cumsum(48 + 140 * np.exp(-t * 32)) / SR) * np.exp(-t * 8) * 1.6)


def clap():
    n = int(SR * 0.25)
    s = np.diff(rng.standard_normal(n + 1))
    e = sum(env(n, 0.001, 60) * (np.arange(n) >= int(SR * d)) for d in (0, 0.01, 0.02)) + env(n, 0.001, 13) * 0.6
    return s * e * 0.5


def hat(open_=False):
    n = int(SR * (0.2 if open_ else 0.035))
    s = np.diff(rng.standard_normal(n + 1))
    return s * env(n, 0.001, 14 if open_ else 90) * 0.4


def riser(length):
    n = int(SR * length); t = np.arange(n) / SR
    s = rng.standard_normal(n)
    y = lowpass(s, np.linspace(0.01, 0.7, n))
    tone = np.sin(2 * np.pi * np.cumsum(200 + 1400 * (t / length) ** 2) / SR) * 0.3
    return (y + tone) * (t / length) ** 2


def impact(length=2.0):
    t = np.arange(int(SR * length)) / SR
    return np.sin(2 * np.pi * np.cumsum(32 + 80 * np.exp(-t * 7)) / SR) * np.exp(-t * 2.6) + rng.standard_normal(len(t)) * np.exp(-t * 5) * 0.3


def bass(f, length):
    n = int(SR * length); t = np.arange(n) / SR
    return lowpass((2 * ((f * t) % 1) - 1) * env(n, 0.003, 5), 0.05) * 2.5


# F#m – D – A – E
CH = [[369.99, 440.0, 554.37], [293.66, 369.99, 440.0], [277.18, 329.63, 440.0], [329.63, 415.3, 493.88]]
RT = [46.25, 36.71, 55.0, 41.2]
LEAD = [[739.99, 880.0, 1108.73, 880.0], [739.99, 880.0, 987.77, 880.0], [659.25, 880.0, 1108.73, 880.0], [659.25, 830.61, 987.77, 830.61]]
BAR = 4 * BEAT
S16 = BEAT / 4

# בילד-אפ: פד מסונן שנפתח + פלאק בשש-עשרה + ריזר עד הדרופ
for k in range(int(DROP / S16)):
    at = k * S16
    c = CH[0]
    place(pluck(c[k % 3] * 2, 0.18, 0.05 + 0.3 * at / DROP), at, 0.12 + 0.12 * at / DROP)
place(saw_chord(CH[0], DROP, np.linspace(0.02, 0.2, int(SR * DROP)), 0.3), 0, 0.5)
place(riser(DROP), 0, 0.35)

# דרופ
place(impact(2.2), DROP, 0.6)
bar = 0
while DROP + bar * BAR < END:
    a = DROP + bar * BAR; c = CH[bar % 4]; r = RT[bar % 4]
    for q in range(4):
        at = a + q * BEAT
        place(kick(), at, 0.85)
        if q in (1, 3): place(clap(), at, 0.5)
        place(hat(True), at + BEAT / 2, 0.25)
        place(hat(), at + S16, 0.1); place(hat(), at + 3 * S16, 0.1)
        place(saw_chord(c, BEAT * 0.9, 0.16, 4.0), at + 0.03, 0.42)       # אקורד "נושם" עם הקיק
        place(bass(r * 2, BEAT / 2 * 0.85), at + BEAT / 2, 0.5)
    for e, f in enumerate(LEAD[bar % 4] * 2):
        if e % 4 != 3 or bar % 2: place(pluck(f, 0.22, 0.35), a + e * BEAT / 2, 0.16)
    bar += 1

# סוף: ריזר קצר ואקורד ארוך
place(saw_chord(CH[0], 3.0, 0.14, 1.2), END, 0.6)
place(bass(RT[0], 2.0), END, 0.7); place(kick(), END, 0.8); place(impact(2.5), END, 0.45)

# סייד-צ'יין מהקיק אחרי הדרופ
duck = np.ones(N)
for b in range(int((END - DROP) / BEAT) + 1):
    i = int((DROP + b * BEAT) * SR); L = int(0.2 * SR)
    duck[i:i + L] = np.minimum(duck[i:i + L], np.linspace(0.4, 1, len(duck[i:i + L])))
out *= duck

t_all = np.arange(N) / SR
out *= np.clip((DUR - t_all) / 1.6, 0, 1) * np.clip(t_all / 0.3, 0, 1)
out = np.tanh(out * 1.1)
out = out / np.max(np.abs(out)) * 0.25       # עוצמה מתונה (בערך ‎-21 LUFS)
stereo = np.stack([out, np.roll(out, 210)], axis=1)
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((stereo * 32767).astype(np.int16).tobytes())
print(OUT, DUR, 's')
