#!/usr/bin/env python3
"""Monta il video wing foil: solo tagli, velocita', reframe, grading, grafiche."""
import os, subprocess, json

FF = "/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
S = os.path.dirname(os.path.abspath(__file__))
SRC = f"{S}/src.mp4"
OUT = f"{S}/seg"
os.makedirs(OUT, exist_ok=True)
FPS = 24
W, H = 1080, 1920

# Color grading globale (nessun intervento locale su volto/corpo)
GRADE = ("eq=contrast=1.07:saturation=1.10:gamma=0.98,"
         "colorbalance=rs=-0.03:gs=0.0:bs=0.03:rm=0.0:bm=0.0:rh=0.03:gh=0.01:bh=-0.02,"
         "curves=master='0/0.02 0.25/0.23 0.75/0.78 1/0.96',"
         "vibrance=intensity=0.12")

# (tipo, src_in, src_out, velocita', zoom_inizio, zoom_fine)
# zoom >= 1.07 con finestra ancorata in alto: taglia la scritta "Insta360 X5" in basso
SEGS = [
    # HOOK: secondo salto al 35%, poi freeze
    ("clip", 23.95, 24.475, 0.35, 1.10, 1.16),
    ("freeze", 0.25),
    ("white", 2 / FPS), ("black", 0.25 - 2 / FPS),
    # APERTURA
    ("clip", 0.00, 3.00, 1.0, 1.07, 1.14),
    # VOLO (speed ramp 100 -> 70 -> 100)
    ("clip", 3.20, 5.20, 1.0, 1.08, 1.10),
    ("clip", 5.20, 6.25, 0.7, 1.10, 1.12),
    ("clip", 6.60, 8.10, 1.0, 1.12, 1.08),
    # CRESCITA: 8 tagli da un beat (0.5 s), punch-in alternati
    ("clip", 9.30, 9.80, 1.0, 1.07, 1.09),
    ("clip", 10.60, 11.10, 1.0, 1.15, 1.15),
    ("clip", 12.00, 12.50, 1.0, 1.08, 1.10),
    ("clip", 12.70, 13.20, 1.0, 1.16, 1.16),
    ("clip", 14.30, 14.80, 1.0, 1.08, 1.11),
    ("clip", 15.50, 16.00, 1.0, 1.17, 1.17),
    ("clip", 16.80, 17.30, 1.0, 1.09, 1.12),
    ("clip", 17.60, 18.10, 1.0, 1.18, 1.18),
    # PRIMO SALTO: stacco reale, volo al 50%
    ("clip", 18.80, 19.30, 1.0, 1.07, 1.09),
    ("clip", 19.30, 20.55, 0.5, 1.09, 1.15),
    # SILENZIO
    ("white", 2 / FPS), ("black", 0.5 - 2 / FPS),
    # CLIMAX: rincorsa, decollo sul drop, volo al 45%, atterraggio reale
    ("clip", 22.95, 23.45, 1.0, 1.07, 1.07),
    ("clip", 23.45, 25.25, 0.45, 1.08, 1.14),
    ("clip", 25.25, 26.75, 1.0, 1.10, 1.18),
    # CHIUSURA: pull-out
    ("clip", 26.75, 29.25, 1.0, 1.14, 1.07),
    ("black", 2.0),
]

ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an"]


def run(cmd):
    subprocess.run(cmd, check=True)


def clip(i, a, b, speed, z0, z1):
    dur = (b - a) / speed
    n = max(1, round(dur * FPS))
    # zoom lineare per frame; finestra centrata in orizzontale, bordo basso <= 93.5% dell'altezza
    z = f"{z0}+({z1}-{z0})*on/{max(n - 1, 1)}"
    vf = (f"trim=start={a}:end={b},setpts=(PTS-STARTPTS)/{speed},fps={FPS},{GRADE},"
          f"scale={W*2}:{H*2}:flags=lanczos,"
          f"zoompan=z='{z}':x='(iw-iw/zoom)/2':y='max(0,ih*0.935-ih/zoom)':d=1:s={W}x{H}:fps={FPS},"
          f"unsharp=5:5:0.35,setsar=1,trim=end_frame={n}")
    out = f"{OUT}/{i:02d}.mp4"
    run([FF, "-v", "error", "-y", "-i", SRC, "-vf", vf, *ENC, out])
    return out, n / FPS


def solid(i, color, dur):
    out = f"{OUT}/{i:02d}.mp4"
    n = max(1, round(dur * FPS))
    run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s={W}x{H}:r={FPS}",
         "-frames:v", str(n), *ENC, out])
    return out, n / FPS


def freeze(i, prev, dur):
    out = f"{OUT}/{i:02d}.mp4"
    n = max(1, round(dur * FPS))
    run([FF, "-v", "error", "-y", "-sseof", "-0.05", "-i", prev, "-vf",
         f"tpad=stop_mode=clone:stop_duration={dur},trim=end_frame={n}", *ENC, out])
    return out, n / FPS


parts, t, timeline, prev = [], 0.0, [], None
for i, s in enumerate(SEGS):
    if s[0] == "clip":
        p, d = clip(i, *s[1:])
    elif s[0] == "freeze":
        p, d = freeze(i, prev, s[1])
    else:
        p, d = solid(i, s[0], s[1])
    timeline.append({"i": i, "kind": s[0], "src": list(s[1:3]) if s[0] == "clip" else None,
                     "speed": s[3] if s[0] == "clip" else None, "t0": round(t, 4), "dur": round(d, 4)})
    parts.append(p); t += d; prev = p
    print(f"{i:02d} {s[0]:6s} t={timeline[-1]['t0']:6.3f} dur={d:.3f}")

with open(f"{OUT}/list.txt", "w") as f:
    f.writelines(f"file '{p}'\n" for p in parts)
run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{OUT}/list.txt", "-c", "copy", f"{S}/video_noaudio.mp4"])
json.dump(timeline, open(f"{S}/timeline.json", "w"), indent=1)
print("TOTALE", round(t, 3))
