# פסקול עשירי: קצבי ומעורר השראה 112 BPM – אקורדי פסנתר סטקטו בשמיניות, קיק וקלאפ קלילים, בס קופצני ופעמונים (D מז'ור).
# הבר הראשון בלי תופים (בלי מכת פתיחה). עוצמה נמוכה – רק לרקע. שימוש: python3 music10.py <משך> <פלט>
import sys
import wave
import numpy as np

SR = 44100
BPM = 112
BEAT = 60 / BPM
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 28.0
OUT = sys.argv[2] if len(sys.argv) > 2 else 'assets/music-amit.wav'
END = DUR - 3.2
N = int(SR * DUR)
out = np.zeros(N)
rng = np.random.default_rng(101)


def place(sig, at, gain=1.0):
    i = int(at * SR)
    if 0 <= i < N:
        j = min(N, i + len(sig))
        out[i:j] += sig[: j - i] * gain


def env(n, a=0.002, d=8.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t * d)


def piano(freqs, length=0.3, dec=9.0):
    n = int(SR * length); t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * h * t) * a for f in freqs for h, a in ((1, 1), (2, 0.4), (3, 0.15)))
    return s / len(freqs) * env(n, 0.003, dec)


def kick():
    t = np.arange(int(SR * 0.28)) / SR
    return np.sin(2 * np.pi * np.cumsum(55 + 95 * np.exp(-t * 38)) / SR) * np.exp(-t * 11)


def clap():
    n = int(SR * 0.2)
    s = np.diff(rng.standard_normal(n + 1))
    e = sum(env(n, 0.001, 70) * (np.arange(n) >= int(SR * d)) for d in (0, 0.01, 0.02)) + env(n, 0.001, 18) * 0.5
    return s * e * 0.45


def hat():
    n = int(SR * 0.04)
    return np.diff(rng.standard_normal(n + 1)) * env(n, 0.001, 80) * 0.35


def bass(f, length):
    n = int(SR * length); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * env(n, 0.004, 6)


def bell(f, length=0.8):
    n = int(SR * length); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 12)) * env(n, 0.001, 5)


# D – A – Bm – G
CH = [[293.66, 369.99, 440.0], [277.18, 329.63, 440.0], [246.94, 293.66, 369.99], [246.94, 293.66, 392.0]]
RT = [73.42, 55.0, 61.74, 49.0]
MEL = [[880.0, 739.99, 659.25, 739.99], [659.25, 554.37, 659.25, 880.0], [739.99, 587.33, 739.99, 880.0], [783.99, 739.99, 659.25, 587.33]]
BAR = 4 * BEAT
bar = 0
while bar * BAR < END:
    a = bar * BAR; c = CH[bar % 4]
    for e in range(8):                                     # פסנתר סטקטו בשמיניות, אקצנט באוף-ביט
        place(piano(c, 0.32), a + e * BEAT / 2, 0.3 if e % 2 else 0.2)
    if bar >= 1:
        for q in range(4):
            at = a + q * BEAT
            place(kick(), at, 0.7 if q in (0, 2) else 0.0)
            if q in (1, 3): place(clap(), at, 0.45)
            place(hat(), at + BEAT / 2, 0.3); place(hat(), at, 0.12)
            place(bass(RT[bar % 4], BEAT * 0.45), at, 0.5); place(bass(RT[bar % 4] * 2, BEAT * 0.3), at + BEAT / 2, 0.3)
        place(kick(), a + 2.5 * BEAT, 0.4)
    if bar >= 2:
        for q, f in enumerate(MEL[bar % 4]):
            place(bell(f), a + q * BEAT, 0.14)
    bar += 1

place(piano(CH[0], 3.0, 1.2), END, 0.5); place(bass(RT[0], 2.0), END, 0.55); place(bell(880.0, 2.5), END, 0.2)

t_all = np.arange(N) / SR
out *= np.clip((DUR - t_all) / 1.8, 0, 1) * np.clip(t_all / 0.6, 0, 1)
out = out / np.max(np.abs(out)) * 0.28       # נמוך – רק לרקע (בערך ‎-27 LUFS)
stereo = np.stack([out, np.roll(out, 180)], axis=1)
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((stereo * 32767).astype(np.int16).tobytes())
print(OUT, DUR, 's')
