# פסקול שני: Half-time 100 BPM – בס 808 גולש, קלאפ, היי-האט 16-יות ואקורדי פלאק עם דיליי.
# שימוש: python3 music2.py <משך בשניות> <קובץ פלט> <זמני מעבר מופרדים בפסיק>
import sys
import wave
import numpy as np

SR = 44100
BPM = 100
BEAT = 60 / BPM
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
OUT = sys.argv[2] if len(sys.argv) > 2 else 'assets/music2.wav'
HITS = [float(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else []
END = DUR - 3.5
N = int(SR * DUR)
out = np.zeros(N)
rng = np.random.default_rng(11)


def place(sig, at, gain=1.0):
    i = int(at * SR)
    if 0 <= i < N:
        j = min(N, i + len(sig))
        out[i:j] += sig[: j - i] * gain


def env(n, a=0.002, d=8.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t * d)


def lowpass(x, a):
    y = np.zeros_like(x)
    for i in range(1, len(x)):
        y[i] = y[i - 1] + a * (x[i] - y[i - 1])
    return y


def kick():
    t = np.arange(int(SR * 0.35)) / SR
    return np.sin(2 * np.pi * np.cumsum(50 + 140 * np.exp(-t * 35)) / SR) * np.exp(-t * 9)


def clap():
    n = int(SR * 0.25)
    s = rng.standard_normal(n)
    s = s - lowpass(s, 0.15)
    e = sum(env(n, 0.001, 60) * (np.arange(n) >= int(SR * d)) for d in (0, 0.012, 0.024)) + env(n, 0.001, 14) * 0.6
    return s * e * 0.7


def hat(n_sec=0.04):
    n = int(SR * n_sec)
    s = np.diff(rng.standard_normal(n + 1))
    return s * env(n, 0.0005, 90)


def bass808(freq, length, glide_to=None):
    n = int(SR * length)
    t = np.arange(n) / SR
    f = np.full(n, freq) if glide_to is None else freq + (glide_to - freq) * np.clip(t / 0.12, 0, 1)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return np.tanh(s * 2.2) * env(n, 0.003, 1.8)


def pluck(freqs, length=0.6):
    n = int(SR * length)
    t = np.arange(n) / SR
    s = sum(np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + np.sin(2 * np.pi * f * 2 * t) * 0.3 for f in freqs)
    return lowpass(s * env(n, 0.002, 7), 0.18)


def impact(length=2.0):
    t = np.arange(int(SR * length)) / SR
    return np.sin(2 * np.pi * np.cumsum(28 + 70 * np.exp(-t * 7)) / SR) * np.exp(-t * 2.5) + rng.standard_normal(len(t)) * np.exp(-t * 6) * 0.3


def sweep(length):
    n = int(SR * length)
    s = rng.standard_normal(n)
    k = np.linspace(0.01, 0.5, n)
    y = np.zeros(n)
    for i in range(1, n):
        y[i] = y[i - 1] + k[i] * (s[i] - y[i - 1])
    return y * np.linspace(0, 1, n) ** 2


# אקורדים: Am – F – C – G, כל אקורד בר אחד
CHORDS = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 261.63, 329.63], [196.0, 246.94, 293.66]]
ROOTS = [55.0, 43.65, 65.41, 49.0]
BAR = 4 * BEAT

# פתיחה: אקורד פלאק בודד + סוויפ
place(pluck(CHORDS[0], 1.2), 0.0, 0.5)
place(sweep(1.9), 0.1, 0.4)

bar = 0
while bar * BAR < END:
    a = bar * BAR
    c = CHORDS[bar % 4]
    # פלאק בסינקופה + דיליי
    for off in (0, 1.5, 2.5, 3.0):
        for d, g in ((0, 0.42), (BEAT * 0.75, 0.18), (BEAT * 1.5, 0.08)):
            place(pluck(c, 0.5), a + off * BEAT + d, g)
    if a >= 2 * BEAT * 0.99:
        place(kick(), a, 1.0)
        place(kick(), a + 2.5 * BEAT, 0.8)
        place(clap(), a + 2 * BEAT, 0.8)
        for s16 in range(16):
            roll = (bar % 2 == 1 and s16 >= 12)
            place(hat(0.03), a + s16 * BEAT / 4, 0.12 if s16 % 2 else 0.2)
            if roll:
                place(hat(0.02), a + s16 * BEAT / 4 + BEAT / 8, 0.1)
        nxt = ROOTS[(bar + 1) % 4]
        place(bass808(ROOTS[bar % 4], 2.4 * BEAT), a, 0.75)
        place(bass808(ROOTS[bar % 4], 1.4 * BEAT, nxt), a + 2.5 * BEAT, 0.6)
    bar += 1

for h in HITS:
    place(impact(1.1), h, 0.35)
place(sweep(1.6), END - 1.6, 0.4)
place(impact(3.0), END, 1.0)
place(pluck(CHORDS[0], 2.5), END, 0.5)

t_all = np.arange(N) / SR
out *= np.clip((DUR - t_all) / 2.0, 0, 1)
out = np.tanh(out * 1.3)
out /= np.max(np.abs(out)) * 1.05
stereo = np.stack([out, np.roll(out, 120)], axis=1)
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((stereo * 32767).astype(np.int16).tobytes())
print(OUT, DUR, 's')
