# פסקול 11: אלקטרו-פופ אנרגטי 124 BPM – ארפג'יו סינת' בשש-עשרה, סאב-בס, סנר חד ו"צ'ופים" פורמנטיים (E מז'ור).
# בר ראשון רק ארפג'יו מסונן (בלי מכת פתיחה); מכה ראשונה בכניסת התופים. עוצמה מתונה. שימוש: python3 music11.py <משך> <פלט>
import sys
import wave
import numpy as np

SR = 44100
BPM = 124
BEAT = 60 / BPM
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 22.0
OUT = sys.argv[2] if len(sys.argv) > 2 else 'assets/music-polish.wav'
END = DUR - 3.0
N = int(SR * DUR)
out = np.zeros(N)
rng = np.random.default_rng(113)


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


def arp(f, cut):
    n = int(SR * BEAT / 4 * 0.9); t = np.arange(n) / SR
    s = (2 * ((f * t) % 1) - 1) * 0.5 + np.sign(np.sin(2 * np.pi * f * 1.002 * t)) * 0.5
    return lowpass(s * env(n, 0.001, 18), cut)


def chop(f, length=0.18):
    # "ווקאל צ'ופ" סינתטי: פורמנטים של אאא
    n = int(SR * length); t = np.arange(n) / SR
    src = 2 * ((f * t) % 1) - 1
    s = sum(np.sin(2 * np.pi * fm * t) * g for fm, g in ((730, 1), (1090, 0.5), (2440, 0.25))) * (src * 0.5 + 0.5)
    return s * env(n, 0.005, 12)


def kick():
    t = np.arange(int(SR * 0.3)) / SR
    return np.tanh(np.sin(2 * np.pi * np.cumsum(50 + 120 * np.exp(-t * 36)) / SR) * np.exp(-t * 10) * 1.4)


def snare():
    n = int(SR * 0.22); t = np.arange(n) / SR
    return np.diff(rng.standard_normal(n + 1)) * env(n, 0.001, 22) * 0.6 + np.sin(2 * np.pi * 200 * t) * env(n, 0.001, 35) * 0.6


def hat():
    n = int(SR * 0.03)
    return np.diff(rng.standard_normal(n + 1)) * env(n, 0.0005, 100) * 0.35


def sub(f, length):
    n = int(SR * length); t = np.arange(n) / SR
    return np.sin(2 * np.pi * f * t) * np.minimum(1, t / 0.01) * np.minimum(1, (length - t) / 0.03)


# E – C#m – A – B
CH = [[329.63, 415.3, 493.88], [277.18, 329.63, 415.3], [220.0, 277.18, 329.63], [246.94, 311.13, 369.99]]
RT = [41.2, 34.65, 55.0, 61.74]
BAR = 4 * BEAT
S16 = BEAT / 4
bar = 0
while bar * BAR < END:
    a = bar * BAR; c = CH[bar % 4]
    cut = 0.05 + 0.25 * min(1, bar / 2)
    for k in range(16):
        f = [c[0], c[1], c[2], c[1] * 2][k % 4] * (2 if k >= 8 else 1)
        place(arp(f, cut), a + k * S16, 0.16)
    if bar >= 1:
        for q in range(4):
            at = a + q * BEAT
            place(kick(), at, 0.75 if q in (0, 2) else 0.0)
            if q in (1, 3): place(snare(), at, 0.45)
            for h in range(4): place(hat(), at + h * S16, 0.18 if h == 2 else 0.08)
        place(kick(), a + 2.75 * BEAT, 0.45)
        place(sub(RT[bar % 4], 1.8 * BEAT), a, 0.55); place(sub(RT[bar % 4], 1.8 * BEAT), a + 2 * BEAT, 0.5)
    if bar >= 2:
        for st, idx in ((0.5, 2), (1.5, 1), (2.25, 2), (3.0, 0)):
            place(chop(c[idx] * 2), a + st * BEAT, 0.14)
    bar += 1

for f in CH[0]: place(lowpass((2 * ((f * np.arange(int(SR * 2.5)) / SR) % 1) - 1) * env(int(SR * 2.5), 0.005, 1.4), 0.15), END, 0.25)
place(sub(RT[0] * 2, 1.6), END, 0.5); place(kick(), END, 0.7)

t_all = np.arange(N) / SR
out *= np.clip((DUR - t_all) / 1.5, 0, 1) * np.clip(t_all / 0.4, 0, 1)
out = out / np.max(np.abs(out)) * 0.25     # נמוך יחסית – ברקע (בערך ‎-26 LUFS)
stereo = np.stack([out, np.roll(out, 190)], axis=1)
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((stereo * 32767).astype(np.int16).tobytes())
print(OUT, DUR, 's')
