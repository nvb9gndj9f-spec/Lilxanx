#!/usr/bin/env python3
"""Colonna sonora originale sintetizzata (120 BPM, La minore) + sound design + ambiente reale."""
import json, os, subprocess
import numpy as np
from scipy import signal
from scipy.io import wavfile

FF = "/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
S = os.path.dirname(os.path.abspath(__file__))
SR = 48000
DUR = 28.0
N = int(SR * DUR)
T = np.arange(N) / SR
rng = np.random.default_rng(7)
BEAT = 0.5  # 120 BPM


def buf():
    return np.zeros(N)


def put(dst, x, t0, g=1.0):
    i = int(t0 * SR)
    if i >= N:
        return
    x = x[: N - i]
    dst[i:i + len(x)] += g * x


def filt(x, kind, f, order=2):
    sos = signal.butter(order, f, btype=kind, fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def env_ad(n, a, d):
    t = np.arange(n) / SR
    e = np.minimum(t / max(a, 1e-4), 1.0) * np.exp(-np.maximum(t - a, 0) / d)
    return e


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# --- strumenti -------------------------------------------------------------
def kick(g=1.0):
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 45 + 85 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t / 0.18)
    x += 0.3 * filt(rng.standard_normal(n), "high", 3000) * np.exp(-t / 0.004)
    return g * np.tanh(1.6 * x)


def snare(g=1.0):
    n = int(0.3 * SR); t = np.arange(n) / SR
    nz = filt(rng.standard_normal(n), "band", [1200, 7000]) * np.exp(-t / 0.09)
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05)
    return g * (0.8 * nz + 0.5 * tone)


def hat(g=1.0, d=0.035):
    n = int(0.15 * SR); t = np.arange(n) / SR
    return g * filt(rng.standard_normal(n), "high", 8000) * np.exp(-t / d)


def saw_voice(f, n, detune=(0, -0.08, 0.07, 0.15)):
    t = np.arange(n) / SR
    return sum(signal.sawtooth(2 * np.pi * f * 2 ** (c / 12) * t + rng.uniform(0, 6)) for c in detune) / len(detune)


def boom(g=1.0, d=1.4):
    n = int(2.5 * SR); t = np.arange(n) / SR
    f = 28 + 40 * np.exp(-t / 0.25)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / d)
    x += 0.6 * filt(rng.standard_normal(n), "low", 400) * np.exp(-t / 0.3)
    return g * np.tanh(1.3 * x)


def whoosh(dur, f0, f1, g=1.0, rev=False):
    n = int(dur * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    out = np.zeros(n); blk = 1024
    for i in range(0, n, blk):
        fr = f0 * (f1 / f0) ** (i / n)
        seg = nz[max(0, i - 2048): i + blk]
        y = filt(seg, "band", [fr * 0.6, min(fr * 1.6, SR / 2 - 100)])
        out[i:i + blk] = y[-len(nz[i:i + blk]):]
    e = np.sin(np.pi * t / dur) ** 2
    if rev:
        e = (t / dur) ** 3
    return g * out * e


CHORDS = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # Am F C G
ROOTS = [33, 29, 36, 31]


def chord_at(t):
    return int(t // 2) % 4


# --- tracce -----------------------------------------------------------------
pad, bass, drums, arp, fx = buf(), buf(), buf(), buf(), buf()

# PAD: intro scuro -> aperto nel drop -> coda
def pad_section(t0, t1, cutoff, g):
    t = t0
    while t < t1:
        bar_end = min((int(t // 2) + 1) * 2, t1)
        n = int((bar_end - t + 0.6) * SR)
        ch = CHORDS[chord_at(t)]
        x = sum(saw_voice(midi(m), n) for m in ch + [ch[0] + 12]) / 4
        x = filt(x, "low", cutoff, 2)
        e = env_ad(n, 0.25, 9.0) * np.clip((bar_end - t + 0.6 - np.arange(n) / SR) / 0.6, 0, 1)
        put(pad, x * e, t, g)
        t = bar_end

pad_section(0.0, 1.5, 700, 0.35)     # hook: drone
pad_section(2.0, 10.0, 900, 0.45)    # intro + volo
pad_section(10.0, 17.0, 1600, 0.45)  # crescita
pad_section(18.0, 23.5, 3200, 0.5)   # drop
pad_section(23.5, 27.6, 1400, 0.45)  # chiusura

# BASSO
def bass_note(t0, dur, m, g):
    n = int(dur * SR)
    f = midi(m)
    x = 0.7 * np.sin(2 * np.pi * f * np.arange(n) / SR) + 0.3 * filt(saw_voice(f, n, (0, 0.05)), "low", 300)
    e = env_ad(n, 0.01, dur * 0.8) * np.clip((dur - np.arange(n) / SR) / 0.02, 0, 1)
    put(bass, x * e, t0, g)

for bt in np.arange(5.0, 10.0, 2.0):           # note lunghe nel volo
    bass_note(bt, 1.95 if bt + 2 <= 10 else 10 - bt, ROOTS[chord_at(bt)], 0.55)
for bt in np.arange(10.0, 17.0, 0.5):          # ottavi di semiminima
    bass_note(bt, 0.45, ROOTS[chord_at(bt)], 0.6)
for bt in np.arange(18.0, 23.5, 0.25):         # drop: crome
    bass_note(bt, 0.22, ROOTS[chord_at(bt)] + (12 if int(bt * 4) % 4 == 2 else 0), 0.62)
for bt in np.arange(23.5, 27.5, 2.0):
    bass_note(bt, 2.0, ROOTS[chord_at(bt)], 0.45 * (1 - (bt - 23.5) / 5))

# ARPEGGIO (pluck)
def pluck(t0, m, g):
    n = int(0.4 * SR); t = np.arange(n) / SR
    f = midi(m)
    x = signal.sawtooth(2 * np.pi * f * t, 0.5) * np.exp(-t / 0.12)
    put(arp, filt(x, "low", 3500), t0, g)

pattern = [0, 1, 2, 3, 2, 1, 0, 2]
for i, bt in enumerate(np.arange(3.0, 17.0, 0.25 if False else 0.5)):
    ch = CHORDS[chord_at(bt)] + [CHORDS[chord_at(bt)][0] + 12]
    pluck(bt, ch[pattern[i % 8]] + 12, 0.18 if bt < 10 else 0.22)
for i, bt in enumerate(np.arange(18.0, 23.5, 0.25)):
    ch = CHORDS[chord_at(bt)] + [CHORDS[chord_at(bt)][0] + 12]
    pluck(bt, ch[pattern[i % 8]] + 12, 0.22)

# BATTERIA
for bt in np.arange(5.0, 10.0, 1.0):
    put(drums, kick(), bt, 0.8)
for bt in np.arange(7.0, 10.0, 0.5):
    put(drums, hat(), bt + 0.25, 0.25)
for bt in np.arange(10.0, 17.0, 0.5):
    put(drums, kick(), bt, 0.95)
    put(drums, hat(), bt + 0.25, 0.35)
    if int(round(bt / 0.5)) % 2 == 1 and bt < 15:
        put(drums, snare(), bt, 0.55)
# rullata accelerata 15 -> 17
t = 15.0
while t < 17.0:
    step = 0.25 if t < 16 else (0.125 if t < 16.5 else 0.0625)
    put(drums, snare(), t, 0.25 + 0.5 * (t - 15) / 2)
    t += step
for bt in np.arange(18.0, 23.5, 0.5):
    put(drums, kick(), bt, 1.0)
    if int(round(bt / 0.5)) % 2 == 1:
        put(drums, snare(), bt, 0.8)
for bt in np.arange(18.0, 23.5, 0.125):
    put(drums, hat(d=0.025), bt, 0.22 if int(bt * 8) % 2 else 0.3)

# SIDECHAIN: pompa pad/basso/arpeggio sui kick
pump = np.ones(N)
kick_times = list(np.arange(5.0, 10.0, 1.0)) + list(np.arange(10.0, 17.0, 0.5)) + list(np.arange(18.0, 23.5, 0.5))
for kt in kick_times:
    i = int(kt * SR); n = int(0.4 * SR)
    seg = 1 - 0.55 * np.exp(-np.arange(n) / SR / 0.1)
    pump[i:i + n] = np.minimum(pump[i:i + n], seg[: N - i])
pad *= pump; bass *= pump; arp *= pump

# SOUND DESIGN
put(fx, whoosh(1.5, 200, 3000, rev=True), 0.0, 0.5)   # risucchio verso il freeze
put(fx, boom(d=0.9), 1.5, 0.9)                         # impatto sul freeze
put(fx, whoosh(0.5, 400, 4000), 1.85, 0.6)             # flash -> apertura
for tt in [4.8, 9.8, 13.8]:                            # transizioni
    put(fx, whoosh(0.45, 300, 5000), tt, 0.45)
for tt in np.arange(10.5, 14.0, 1.0):                  # micro whoosh sugli stacchi
    put(fx, whoosh(0.25, 800, 6000), tt - 0.12, 0.2)
# riser 10 -> 17 (rumore + sinusoide che sale), tagliato netto
n = int(7.0 * SR); tr = np.arange(n) / SR
riser = whoosh(7.0, 250, 9000, rev=True)
riser += 0.25 * np.sin(2 * np.pi * np.cumsum(200 * 2 ** (tr / 7.0 * 3)) / SR) * (tr / 7.0) ** 2
put(fx, riser, 10.0, 0.55)
put(fx, whoosh(0.4, 3000, 300), 17.0, 0.35)            # flash bianco
put(fx, whoosh(0.35, 300, 6000, rev=True), 17.65, 0.6) # risucchio prima del drop
put(fx, boom(), 18.0, 1.1)                             # DROP
put(fx, boom(d=1.0), 22.75, 0.9)                       # atterraggio
put(fx, whoosh(0.6, 5000, 400), 22.6, 0.4)             # spruzzo

# CODA: fade globale della musica
music = 0.55 * pad + 0.7 * bass + 0.9 * drums + 0.6 * arp
fade = np.clip((27.8 - T) / 2.3, 0, 1); fade[T < 25.5] = 1
music *= fade
music[(T >= 17.0) & (T < 18.0)] *= 0.0  # silenzio vero prima del drop
music[(T >= 1.75) & (T < 2.0)] *= 0.0
sec = np.ones(N)
sec[(T >= 10.0) & (T < 17.0)] = 0.8   # crescita un po' sotto
sec[(T >= 18.0) & (T < 23.5)] = 1.35  # drop: la sezione piu' forte
music *= np.convolve(sec, np.ones(1200) / 1200, mode="same")

# AMBIENTE REALE (vento/acqua) seguendo il montaggio
subprocess.run([FF, "-v", "error", "-y", "-i", f"{S}/src.mp4", "-vn", "-ac", "1", "-ar", str(SR), f"{S}/src_audio.wav"], check=True)
_, src = wavfile.read(f"{S}/src_audio.wav")
src = src.astype(np.float64) / 32768.0
amb = buf()
for seg in json.load(open(f"{S}/timeline.json")):
    if seg["kind"] != "clip":
        continue
    a, b = seg["src"]; sp = seg["speed"]
    x = src[int(a * SR): int(b * SR)]
    if sp != 1.0:  # slow motion: rallenta e scurisci il suono
        x = signal.resample(x, int(len(x) / sp))
        x = filt(x, "low", 1800)
    fl = int(0.01 * SR)
    x[:fl] *= np.linspace(0, 1, fl); x[-fl:] *= np.linspace(1, 0, fl)
    put(amb, x, seg["t0"])
amb = filt(amb, "high", 60)
amb_gain = np.full(N, 0.35)
amb_gain[(T >= 17.5) & (T < 18.0)] = 0.9    # vento in primo piano nel silenzio
amb_gain[(T >= 22.5) & (T < 23.5)] = 0.8    # spruzzo dell'atterraggio
amb_gain[T >= 23.5] = 0.5
amb_gain = np.convolve(amb_gain, np.ones(2400) / 2400, mode="same")
amb *= amb_gain * np.clip((27.5 - T) / 1.5, 0, 1)

mix = music + amb + 0.8 * fx
# stereo leggero: arpeggio e hat allargati tramite piccolo ritardo
d = int(0.012 * SR)
wide = np.concatenate([np.zeros(d), (0.3 * arp + 0.3 * drums)[:-d]]) * fade
L = mix + 0.15 * wide; R = mix - 0.15 * wide
st = np.stack([L, R], 1)
st = np.tanh(st / (np.abs(st).max() + 1e-9) * 1.3) * 0.9
wavfile.write(f"{S}/mix_raw.wav", SR, (st * 32767).astype(np.int16))
# normalizzazione statica (preserva la dinamica) + limiter
r = subprocess.run([FF, "-hide_banner", "-i", f"{S}/mix_raw.wav", "-af", "ebur128", "-f", "null", "-"],
                   capture_output=True, text=True).stderr
I = float(r.split("Integrated loudness:")[1].split("I:")[1].split("LUFS")[0])
subprocess.run([FF, "-v", "error", "-y", "-i", f"{S}/mix_raw.wav", "-af",
                f"volume={-14 - I:.2f}dB,alimiter=limit=0.89:level=false", "-ar", str(SR), f"{S}/mix.wav"], check=True)
print("audio ok")
