# פסקול תשיעי: עדין ומרגש 84 BPM – פסנתר רך, פד חם, בס עמוק ושייקר שקט (C מז'ור), לסרטון סיפור.
# בלי תופים בפתיחה, עוצמה נמוכה לרקע. שימוש: python3 music9.py <משך> <פלט>
import sys
import wave
import numpy as np

SR = 44100
BPM = 84
BEAT = 60 / BPM
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 28.0
OUT = sys.argv[2] if len(sys.argv) > 2 else 'assets/music-amit.wav'
END = DUR - 3.5
N = int(SR * DUR)
out = np.zeros(N)
rng = np.random.default_rng(97)


def place(sig, at, gain=1.0):
    i = int(at * SR)
    if 0 <= i < N:
        j = min(N, i + len(sig))
        out[i:j] += sig[: j - i] * gain


def piano(f, length=2.2):
    n = int(SR * length); t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * h * t) * a * np.exp(-t * (1.5 + h * 0.9)) for h, a in ((1, 1), (2, 0.45), (3, 0.2), (4, 0.08)))
    return s * np.minimum(1, t / 0.004)


def pad(freqs, length):
    n = int(SR * length); t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * d * t) for f in freqs for d in (0.997, 1.003)) / (2 * len(freqs))
    return s * np.minimum(1, t / 1.0) * np.minimum(1, (length - t) / 1.0)


def bass(f, length):
    n = int(SR * length); t = np.arange(n) / SR
    return np.sin(2 * np.pi * f * t) * np.minimum(1, t / 0.02) * np.exp(-t * 0.8)


def shaker():
    n = int(SR * 0.06)
    s = np.diff(np.diff(rng.standard_normal(n + 2)))
    return s * np.minimum(1, np.arange(n) / SR / 0.01) * np.exp(-np.arange(n) / SR * 50) * 0.25


# C – G – Am – F
CH = [[261.63, 329.63, 392.0], [246.94, 293.66, 392.0], [220.0, 261.63, 329.63], [220.0, 261.63, 349.23]]
RT = [65.41, 49.0, 55.0, 43.65]
MEL = [[659.25, 783.99], [587.33, 783.99], [523.25, 659.25], [523.25, 698.46]]
BAR = 4 * BEAT
bar = 0
while bar * BAR < END:
    a = bar * BAR; c = CH[bar % 4]
    place(pad(c, BAR + 0.8), a, 0.22)
    # פסנתר: ארפג'יו רך בשמיניות
    for e, idx in enumerate([0, 1, 2, 1, 0, 1, 2, 1]):
        place(piano(c[idx] * (2 if e in (2, 6) else 1), 1.6), a + e * BEAT / 2, 0.12)
    if bar >= 1:
        place(bass(RT[bar % 4], BAR), a, 0.35)
        for q in range(8):
            place(shaker(), a + q * BEAT / 2, 0.5 if q % 2 else 0.25)
    if bar >= 2:
        for q, f in enumerate(MEL[bar % 4]):
            place(piano(f, 2.5), a + q * 2 * BEAT, 0.16)
    bar += 1

for f in CH[0]:
    place(piano(f, 4.0), END, 0.2); place(piano(f * 2, 4.0), END + 0.05, 0.1)
place(pad(CH[0], 3.5), END, 0.25); place(bass(RT[0], 3.0), END, 0.35)

t_all = np.arange(N) / SR
out *= np.clip((DUR - t_all) / 2.0, 0, 1) * np.clip(t_all / 1.0, 0, 1)
out = out / np.max(np.abs(out)) * 0.35       # מוזיקת רקע עדינה
stereo = np.stack([out, np.roll(out, 250)], axis=1)
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((stereo * 32767).astype(np.int16).tobytes())
print(OUT, DUR, 's')
