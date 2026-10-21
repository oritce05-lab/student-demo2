# פסקול שלישי: פופ קליל ושמח 112 BPM – מרימבה, קלאפים, שייקר בסווינג ובס קופצני (D מז'ור). בלי מכות פתיחה.
# שימוש: python3 music3.py <משך בשניות> <קובץ פלט>
import sys
import wave
import numpy as np

SR = 44100
BPM = 112
BEAT = 60 / BPM
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
OUT = sys.argv[2] if len(sys.argv) > 2 else 'music3.wav'
END = DUR - 3.0
N = int(SR * DUR)
out = np.zeros(N)
rng = np.random.default_rng(23)


def place(sig, at, gain=1.0):
    i = int(at * SR)
    if 0 <= i < N:
        j = min(N, i + len(sig))
        out[i:j] += sig[: j - i] * gain


def env(n, a=0.002, d=8.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t * d)


def marimba(f, length=0.45):
    n = int(SR * length)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 30)
    return s * env(n, 0.001, 9)


def kick():
    t = np.arange(int(SR * 0.3)) / SR
    return np.sin(2 * np.pi * np.cumsum(55 + 90 * np.exp(-t * 40)) / SR) * np.exp(-t * 12)


def clap():
    n = int(SR * 0.2)
    s = np.diff(rng.standard_normal(n + 1))
    e = sum(env(n, 0.001, 70) * (np.arange(n) >= int(SR * d)) for d in (0, 0.01, 0.02)) + env(n, 0.001, 18) * 0.5
    return s * e * 0.5


def shaker():
    n = int(SR * 0.07)
    s = np.diff(np.diff(rng.standard_normal(n + 2)))
    return s * env(n, 0.012, 50) * 0.5


def bass(f, length):
    n = int(SR * length)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    return np.tanh(s * 1.5) * env(n, 0.004, 5)


# D – Bm – G – A
CH = [[293.66, 369.99, 440.0], [246.94, 293.66, 369.99], [196.0, 246.94, 293.66], [220.0, 277.18, 329.63]]
RT = [73.42, 61.74, 49.0, 55.0]
MEL = [[880.0, 739.99, 659.25, 739.99], [739.99, 587.33, 659.25, 587.33], [587.33, 493.88, 587.33, 659.25], [659.25, 554.37, 659.25, 739.99]]
BAR = 4 * BEAT
SW = BEAT / 2 * 0.62  # סווינג
bar = 0
while bar * BAR < END:
    a = bar * BAR
    c = CH[bar % 4]
    # מרימבה: אקורד שבור בשמיניות עם סווינג
    for e in range(8):
        at = a + (e // 2) * BEAT + (SW if e % 2 else 0)
        place(marimba(c[[0, 2, 1, 2, 0, 1, 2, 1][e]] * 2), at, 0.28)
    # מנגינה קצרה בבר הזוגי (אחרי הפתיחה)
    if bar >= 2 and bar % 2 == 0:
        for q, f in enumerate(MEL[bar % 4]):
            place(marimba(f, 0.6), a + q * BEAT, 0.2)
    # תופים נכנסים בהדרגה: שייקר מהבר הראשון, קיק וקלאפ מהבר השני
    for q in range(4):
        place(shaker(), a + q * BEAT, 0.25)
        place(shaker(), a + q * BEAT + SW, 0.4)
        if bar >= 1:
            if q in (0, 2):
                place(kick(), a + q * BEAT, 0.8)
            else:
                place(clap(), a + q * BEAT, 0.55)
    if bar >= 1:
        place(kick(), a + 2 * BEAT + SW, 0.45)
        for at, L in ((0, 0.9), (1.5, 0.4), (2, 0.9), (3.5, 0.4)):
            place(bass(RT[bar % 4], L * BEAT), a + at * BEAT, 0.55)
    bar += 1

# סיום: אקורד מרימבה פתוח
for f in CH[0]:
    place(marimba(f * 2, 2.0), END, 0.35)
    place(marimba(f, 2.0), END, 0.3)
place(bass(RT[0], 2.0), END, 0.6)

t_all = np.arange(N) / SR
out *= np.clip((DUR - t_all) / 1.5, 0, 1) * np.clip(t_all / 0.8, 0, 1)
out = np.tanh(out * 1.2)
out /= np.max(np.abs(out)) * 1.05
stereo = np.stack([out, np.roll(out, 150)], axis=1)
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((stereo * 32767).astype(np.int16).tobytes())
print(OUT, DUR, 's')
