# פסקול רביעי: פאנק-פופ קליל 118 BPM – גיטרה מפורטת (Karplus-Strong), סנאפים, בס קופצני ושריקה (F מז'ור).
# הפתיחה רכה, בלי מכות תופים. שימוש: python3 music4.py <משך בשניות> <קובץ פלט>
import sys
import wave
import numpy as np

SR = 44100
BPM = 118
BEAT = 60 / BPM
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 24.0
OUT = sys.argv[2] if len(sys.argv) > 2 else 'assets/music-painter.wav'
END = DUR - 3.2
N = int(SR * DUR)
out = np.zeros(N)
rng = np.random.default_rng(31)


def place(sig, at, gain=1.0):
    i = int(at * SR)
    if 0 <= i < N:
        j = min(N, i + len(sig))
        out[i:j] += sig[: j - i] * gain


def env(n, a=0.002, d=8.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t * d)


def pluck(f, length=0.5, damp=0.996):
    # Karplus-Strong: מיתר גיטרה פשוט
    p = max(2, int(SR / f))
    n = int(SR * length)
    buf = rng.uniform(-1, 1, p)
    y = np.zeros(n)
    for i in range(n):
        y[i] = buf[i % p]
        buf[i % p] = damp * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    return y * env(n, 0.001, 3)


def snap():
    n = int(SR * 0.08)
    s = np.diff(rng.standard_normal(n + 1))
    return s * env(n, 0.0005, 80) * 0.6


def kick():
    t = np.arange(int(SR * 0.25)) / SR
    return np.sin(2 * np.pi * np.cumsum(60 + 80 * np.exp(-t * 45)) / SR) * np.exp(-t * 14)


def bass(f, length):
    n = int(SR * length)
    t = np.arange(n) / SR
    return np.tanh((np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t)) * 1.6) * env(n, 0.003, 7)


def whistle(f, length):
    n = int(SR * length)
    t = np.arange(n) / SR
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * t)
    s = np.sin(2 * np.pi * np.cumsum(f * vib) / SR) + rng.standard_normal(n) * 0.02
    return s * np.minimum(1, t / 0.04) * np.minimum(1, (length - t) / 0.06)


# F – Dm – Bb – C
CH = [[349.23, 440.0, 523.25], [293.66, 349.23, 440.0], [233.08, 293.66, 349.23], [261.63, 329.63, 392.0]]
RT = [87.31, 73.42, 58.27, 65.41]
MEL = [[(0, 698.46, 0.4), (0.5, 783.99, 0.4), (1, 880.0, 0.9), (2.5, 783.99, 0.4), (3, 698.46, 0.9)],
       [(0, 587.33, 0.4), (0.5, 698.46, 0.4), (1, 880.0, 1.4), (3, 783.99, 0.9)]]
BAR = 4 * BEAT
cache = {}
bar = 0
while bar * BAR < END:
    a = bar * BAR
    c = CH[bar % 4]
    # גיטרה: סטראמים קצרים בסינקופה
    for off in (0, 0.75, 1.5, 2.5, 3.0, 3.5):
        for j, f in enumerate(c):
            key = (f, 0.45)
            if key not in cache: cache[key] = pluck(f, 0.45)
            place(cache[key], a + off * BEAT + j * 0.012, 0.22)
    if bar >= 1:
        for q in range(4):
            if q % 2: place(snap(), a + q * BEAT, 0.5)
            place(snap(), a + q * BEAT + BEAT / 2, 0.12)
        place(kick(), a, 0.7); place(kick(), a + 1.75 * BEAT, 0.45); place(kick(), a + 2 * BEAT, 0.6)
        for at, L in ((0, 0.6), (0.75, 0.3), (1.5, 0.4), (2, 0.6), (3, 0.3), (3.5, 0.4)):
            place(bass(RT[bar % 4] * (2 if at == 3.5 else 1), L * BEAT), a + at * BEAT, 0.5)
    if bar >= 2 and a + BAR < END:
        for at, f, L in MEL[bar % 2]:
            place(whistle(f, L * BEAT), a + at * BEAT, 0.12)
    bar += 1

for j, f in enumerate(CH[0]):
    place(pluck(f, 2.5, 0.998), END + j * 0.03, 0.4)
place(bass(RT[0], 1.5), END, 0.6)

t_all = np.arange(N) / SR
out *= np.clip((DUR - t_all) / 1.6, 0, 1) * np.clip(t_all / 0.6, 0, 1)
out = np.tanh(out * 1.2)
out /= np.max(np.abs(out)) * 1.05
stereo = np.stack([out, np.roll(out, 140)], axis=1)
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((stereo * 32767).astype(np.int16).tobytes())
print(OUT, DUR, 's')
