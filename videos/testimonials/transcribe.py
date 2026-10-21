# תמלול עברית לפי משפטים: חלוקה לפי שתיקות ותמלול כל קטע (Whisper turbo דרך sherpa-onnx).
# פלט: work/<name>.json – רשימת קטעים {start, end, text}
import json, sys, subprocess, wave
import numpy as np
import sherpa_onnx
M = sys.argv[1]  # תיקיית המודל
SR = 16000
rec = sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder=f'{M}/turbo-encoder.int8.onnx', decoder=f'{M}/turbo-decoder.int8.onnx',
    tokens=f'{M}/turbo-tokens.txt', language='he', task='transcribe', num_threads=8)
for name, src in json.load(open('sources.json')).items():
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-vn', '-ac', '1', '-ar', str(SR), '-af', 'highpass=f=90,afftdn=nf=-28', f'work/{name}.wav'], check=True)
    w = wave.open(f'work/{name}.wav'); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    hop = 320
    r = np.array([20 * np.log10(np.sqrt(np.mean(a[i:i + hop] ** 2)) + 1e-9) for i in range(0, len(a) - hop, hop)])
    speech = r > -38
    # קטעי דיבור: מאחדים פערים קצרים מ-0.25 שנ'
    segs, s, gap = [], None, 0
    for i, v in enumerate(speech):
        if v:
            if s is None: s = i
            gap = 0
        elif s is not None:
            gap += 1
            if gap * 0.02 >= 0.25:
                segs.append((s * 0.02, (i - gap + 1) * 0.02)); s = None; gap = 0
    if s is not None: segs.append((s * 0.02, len(speech) * 0.02))
    segs = [(a0, b0) for a0, b0 in segs if b0 - a0 > 0.25]
    out = []
    for a0, b0 in segs:
        chunk = a[int(max(0, a0 - 0.1) * SR): int((b0 + 0.1) * SR)]
        st = rec.create_stream(); st.accept_waveform(SR, chunk); rec.decode_stream(st)
        out.append({'start': round(a0, 2), 'end': round(b0, 2), 'text': st.result.text.strip()})
        print(name, f'{a0:5.2f}-{b0:5.2f}', out[-1]['text'], flush=True)
    json.dump(out, open(f'work/{name}.json', 'w'), ensure_ascii=False, indent=1)
