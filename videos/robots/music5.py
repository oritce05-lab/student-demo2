# פסקול חמישי: רוק אנרגטי / פיטנס 132 BPM – גיטרות דיסטורשן (פאוור קורדים), תופי רוק ובס (E מינור).
# פתיחה בריף גיטרה מושתק לבד, התופים נכנסים בבר השני – בלי מכת פתיחה. שימוש: python3 music5.py <משך> <פלט>
import sys
import wave
import numpy as np

SR = 44100
BPM = 132
BEAT = 60 / BPM
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 24.0
OUT = sys.argv[2] if len(sys.argv) > 2 else 'assets/music-painter.wav'
# soft: גיטרה נקייה יותר, תופים רכים ועוצמה כללית נמוכה (לבקשה "פחות רועש")
SOFT = len(sys.argv) > 3 and sys.argv[3] == 'soft'
END = DUR - 3.0
N = int(SR * DUR)
out = np.zeros(N)
rng = np.random.default_rng(41)


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
    acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc); y[i] = acc
    return y


def power(root, length, mute=False):
    # פאוור קורד: שורש + קווינטה + אוקטבה, שני ערוצים מעט מכוונים, דיסטורשן
    n = int(SR * length)
    t = np.arange(n) / SR
    s = 0
    for f in (root, root * 1.4983, root * 2):
        for det in (0.997, 1.003):
            ph = 2 * np.pi * f * det * t
            s = s + (2 * ((ph / (2 * np.pi)) % 1) - 1)   # סאו
    s = np.tanh(s * ((1.2 if mute else 1.6) if SOFT else (2.5 if mute else 4.0)))
    e = env(n, 0.003, 22 if mute else 1.2)
    return lowpass(s * e, (0.10 if mute else 0.14) if SOFT else (0.22 if mute else 0.35))


def kick():
    t = np.arange(int(SR * 0.3)) / SR
    return np.tanh(np.sin(2 * np.pi * np.cumsum(50 + 120 * np.exp(-t * 30)) / SR) * np.exp(-t * 10) * 1.8)


def snare():
    n = int(SR * 0.28)
    t = np.arange(n) / SR
    s = rng.standard_normal(n) * env(n, 0.001, 16) * 0.8 + np.sin(2 * np.pi * 190 * t) * env(n, 0.001, 30)
    return s


def hat(open_=False):
    n = int(SR * (0.25 if open_ else 0.05))
    s = np.diff(rng.standard_normal(n + 1))
    return s * env(n, 0.0005, 12 if open_ else 70) * 0.5


def crash():
    n = int(SR * 1.6)
    s = np.diff(rng.standard_normal(n + 1))
    return s * env(n, 0.001, 2.2) * 0.5


def bass(f, length):
    n = int(SR * length)
    t = np.arange(n) / SR
    return np.tanh(np.sin(2 * np.pi * f * t) * 2.5) * env(n, 0.003, 4)


# E5 – E5 – C5 – D5 (רוק קלאסי), ריף שמיניות מושתקות + אקצנטים
RT = [82.41, 82.41, 65.41, 73.42]
BAR = 4 * BEAT
E8 = BEAT / 2
mutes = {}
bar = 0
while bar * BAR < END:
    a = bar * BAR
    r = RT[bar % 4]
    if r not in mutes: mutes[r] = power(r, E8 * 0.95, True)
    for e in range(8):
        at = a + e * E8
        if at >= END: break
        if bar >= 1 and e in (0, 3, 6):
            place(power(r, E8 * (3 if e < 6 else 2) * 0.95), at, 0.32)   # אקורד פתוח באקצנט
        else:
            place(mutes[r], at, 0.3 if bar >= 1 else 0.24 + 0.02 * e)
        if bar >= 1:
            place(bass(r, E8 * 0.9), at, 0.4)
    if bar >= 1:
        for q in range(4):
            at = a + q * BEAT
            place(kick(), at, (0.6 if SOFT else 0.85) if q in (0, 2) else 0.0)
            if q in (1, 3): place(snare(), at, 0.3 if SOFT else 0.55)
            place(hat(q == 3 and bar % 2), at + E8, 0.2)
            place(hat(), at, 0.14)
        place(kick(), a + 2.5 * BEAT, 0.6)
        if bar % 4 == 1: place(crash(), a, 0.15 if SOFT else 0.35)
    if bar == 0:
        # מילוי תופים קצר בסוף בר הפתיחה במקום מכה בהתחלה
        for k in range(4): place(snare(), a + 3 * BEAT + k * BEAT / 4, 0.18 + 0.08 * k)
    bar += 1

# סיום: אקורד E5 ארוך + קראש
place(power(82.41, 2.6), END, 0.4)
place(bass(82.41, 2.0), END, 0.5)
place(kick(), END, 0.6 if SOFT else 0.9); place(crash(), END, 0.2 if SOFT else 0.5)

t_all = np.arange(N) / SR
out *= np.clip((DUR - t_all) / 1.4, 0, 1) * np.clip(t_all / 0.5, 0, 1)
if SOFT:
    # תופים וגיטרות כבר רכים; מנרמלים לשיא נמוך (בערך ‎-9dB) בלי דחיסה
    out = lowpass(out, 0.5)
    out = out / np.max(np.abs(out)) * 0.35
else:
    out = np.tanh(out * 1.3)
    out /= np.max(np.abs(out)) * 1.05
stereo = np.stack([out, np.roll(out, 200)], axis=1)
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((stereo * 32767).astype(np.int16).tobytes())
print(OUT, DUR, 's')
