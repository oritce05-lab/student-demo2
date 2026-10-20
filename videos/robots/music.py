# פסקול אלקטרוני ל-120 BPM, מסונתז בקוד (בלי בעיית זכויות). פלט: assets/music.wav
import wave
import numpy as np

SR = 44100
BPM = 120
BEAT = 60 / BPM
DUR = 24.0
N = int(SR * DUR)
t_all = np.arange(N) / SR
out = np.zeros(N)
rng = np.random.default_rng(7)


def place(sig, at, gain=1.0):
    i = int(at * SR)
    if i >= N:
        return
    j = min(N, i + len(sig))
    out[i:j] += sig[: j - i] * gain


def kick(length=0.45):
    t = np.arange(int(SR * length)) / SR
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 7.5) + 0.25 * np.exp(-t * 90) * rng.standard_normal(len(t))


def hat(length=0.06):
    n = rng.standard_normal(int(SR * length))
    n = np.diff(n, prepend=0)  # highpass גס
    return n * np.exp(-np.arange(len(n)) / SR * 70)


def impact(length=2.2):
    t = np.arange(int(SR * length)) / SR
    boom = np.sin(2 * np.pi * np.cumsum(30 + 60 * np.exp(-t * 6)) / SR) * np.exp(-t * 2.2)
    noise = rng.standard_normal(len(t)) * np.exp(-t * 4) * 0.35
    return boom + noise


def riser(length):
    t = np.arange(int(SR * length)) / SR
    n = rng.standard_normal(len(t))
    k = np.linspace(0.02, 0.6, len(t))  # פתיחת פילטר הדרגתית
    y = np.zeros_like(n)
    for i in range(1, len(n)):
        y[i] = y[i - 1] + k[i] * (n[i] - y[i - 1])
    return y * (t / length) ** 2


def saw(freq, length):
    t = np.arange(int(SR * length)) / SR
    return sum(np.sin(2 * np.pi * freq * h * t) / h for h in range(1, 9)) * 0.6


def lowpass(x, a):
    y = np.zeros_like(x)
    for i in range(1, len(x)):
        y[i] = y[i - 1] + a * (x[i] - y[i - 1])
    return y


# מבנה: 0–2 הוק (מכות), 2–20 גרוב, 20–24 סיום
for b in range(4):  # הוק: מכה על כל פעמה
    place(impact(0.9), b * BEAT, 0.9)
place(riser(2.0 - 0.05), 0.0, 0.5)

beats = int(DUR / BEAT)
for b in range(4, beats):
    at = b * BEAT
    if at >= 20.0:
        break
    place(kick(), at, 1.0)
    place(hat(), at + BEAT / 2, 0.22)
    place(hat(0.03), at + BEAT / 4, 0.08)
    place(hat(0.03), at + 3 * BEAT / 4, 0.08)

# בס בשמיניות עם דאקינג מהקיק
roots = [55.0, 43.65, 65.41, 49.0]  # A1 F1 C2 G1
for bar in range(1, 10):
    f = roots[bar % 4]
    for e in range(8):
        at = bar * 4 * BEAT + e * BEAT / 2
        if at >= 20.0:
            break
        note = lowpass(saw(f, BEAT / 2 * 0.9), 0.08)
        env = np.minimum(1, np.linspace(0, 12, len(note))) * np.exp(-np.linspace(0, 3, len(note)))
        place(note * env, at, 0.55)

# ארפג'יו בחלק הרובוטים (14–20)
arp = [440.0, 523.25, 659.25, 880.0]
for k in range(int(6 / (BEAT / 4))):
    at = 14.0 + k * BEAT / 4
    t = np.arange(int(SR * BEAT / 4)) / SR
    tone = np.sign(np.sin(2 * np.pi * arp[k % 4] * t)) * np.exp(-t * 18)
    place(lowpass(tone, 0.25), at, 0.12)

# מעברים
place(riser(1.5), 12.5, 0.35)
place(riser(1.5), 18.5, 0.45)
for at in (2.0, 8.0, 14.0):
    place(impact(1.2), at, 0.45)
place(impact(3.5), 20.0, 1.0)

# דאקינג (sidechain) מהקיק
duck = np.ones(N)
for b in range(4, int(20.0 / BEAT)):
    i = int(b * BEAT * SR)
    L = int(0.22 * SR)
    duck[i:i + L] = np.minimum(duck[i:i + L], np.linspace(0.35, 1, L))
out *= duck * 0.5 + 0.5

# סיום: דעיכה
fade = np.clip((DUR - t_all) / 2.5, 0, 1)
out *= fade
out = np.tanh(out * 1.4)
out /= np.max(np.abs(out)) * 1.05
stereo = np.stack([out, np.roll(out, 90)], axis=1)
with wave.open('assets/music.wav', 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((stereo * 32767).astype(np.int16).tobytes())
print('assets/music.wav', DUR, 's')
