# פסקול שישי: UPBEAT פופ-דאנס 124 BPM – אקורדי סינת' בהירים באוף-ביט, קיק רך ארבע לרבע, היי-האט פתוח, קלאפ ובס קופצני (G מז'ור).
# נקי, בלי דיסטורשן, בעוצמה מתונה. בר ראשון בלי קיק – בלי מכת פתיחה. שימוש: python3 music6.py <משך> <פלט>
import sys
import wave
import numpy as np

SR = 44100
BPM = 124
BEAT = 60 / BPM
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 24.0
OUT = sys.argv[2] if len(sys.argv) > 2 else 'assets/music-painter.wav'
END = DUR - 3.0
N = int(SR * DUR)
out = np.zeros(N)
rng = np.random.default_rng(53)


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


def chord(freqs, length):
    # סינת' "סופר-סאו" עדין ומסונן
    n = int(SR * length); t = np.arange(n) / SR
    s = 0
    for f in freqs:
        for det in (0.995, 1.0, 1.005):
            s = s + 2 * ((f * det * t) % 1) - 1
    return lowpass(s / (3 * len(freqs)) * env(n, 0.005, 6), 0.12)


def kick():
    t = np.arange(int(SR * 0.28)) / SR
    return np.sin(2 * np.pi * np.cumsum(52 + 95 * np.exp(-t * 38)) / SR) * np.exp(-t * 11)


def clap():
    n = int(SR * 0.2)
    s = np.diff(rng.standard_normal(n + 1))
    e = sum(env(n, 0.001, 70) * (np.arange(n) >= int(SR * d)) for d in (0, 0.01, 0.02)) + env(n, 0.001, 20) * 0.5
    return s * e * 0.45


def hat(open_=False):
    n = int(SR * (0.18 if open_ else 0.04))
    s = np.diff(rng.standard_normal(n + 1))
    return s * env(n, 0.001, 18 if open_ else 80) * 0.4


def bass(f, length):
    n = int(SR * length); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * env(n, 0.004, 6)


def bell(f, length=0.5):
    n = int(SR * length); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 3 * t) * np.exp(-t * 20)) * env(n, 0.001, 7)


# G – D – Em – C
CH = [[392.0, 493.88, 587.33], [369.99, 440.0, 587.33], [329.63, 392.0, 493.88], [329.63, 392.0, 523.25]]
RT = [98.0, 73.42, 82.41, 65.41]
MEL = [784.0, 880.0, 987.77, 880.0, 784.0, 659.25, 739.99, 784.0]
BAR = 4 * BEAT
bar = 0
while bar * BAR < END:
    a = bar * BAR; c = CH[bar % 4]
    for q in range(4):
        at = a + q * BEAT
        place(chord(c, BEAT * 0.45), at + BEAT / 2, 0.55)          # אקורד באוף-ביט – התחושה הקופצנית
        place(hat(True), at + BEAT / 2, 0.3)
        place(hat(), at + BEAT / 4, 0.12); place(hat(), at + 3 * BEAT / 4, 0.12)
        if bar >= 1:
            place(kick(), at, 0.75)
            if q in (1, 3): place(clap(), at, 0.5)
            place(bass(RT[bar % 4], BEAT * 0.4), at + BEAT / 2, 0.55)
    if bar >= 2:
        for e, f in enumerate(MEL):
            if (e + bar) % 3 != 2: place(bell(f), a + e * BEAT / 2, 0.14)
    bar += 1

for f in CH[0]: place(chord([f], 2.5), END, 0.6)
place(bass(RT[0], 1.6), END, 0.6); place(bell(784.0, 2.0), END, 0.2)

t_all = np.arange(N) / SR
out *= np.clip((DUR - t_all) / 1.5, 0, 1) * np.clip(t_all / 0.5, 0, 1)
out = out / np.max(np.abs(out)) * 0.8       # עוצמה מתונה (בערך ‎-19 LUFS), בלי דחיסה
stereo = np.stack([out, np.roll(out, 160)], axis=1)
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((stereo * 32767).astype(np.int16).tobytes())
print(OUT, DUR, 's')
