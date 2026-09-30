#!/usr/bin/env python3
"""Titoli (PNG trasparenti), grana, vignettatura, mux audio -> export finale."""
import os, subprocess
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FF = "/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
S = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def text_png(name, lines):
    """lines: [(testo, font, size, tracking_px, y_center, alpha)]"""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for txt, fpath, size, track, yc, a in lines:
        f = ImageFont.truetype(fpath, size)
        widths = [f.getlength(c) for c in txt]
        total = sum(widths) + track * (len(txt) - 1)
        x = (W - total) / 2
        top = yc - size / 2
        for c, w in zip(txt, widths):
            ImageDraw.Draw(shadow).text((x + 3, top + 4), c, font=f, fill=(0, 0, 0, 150))
            ImageDraw.Draw(im).text((x, top), c, font=f, fill=(255, 255, 255, a))
            x += w + track
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    out = Image.alpha_composite(shadow, im)
    p = f"{S}/{name}.png"; out.save(p); return p


titles = [
    # (png, inizio, fine, fade)
    (text_png("t_title", [("SOPRA L'ACQUA", BOLD, 92, 14, 1380, 255),
                          ("WING FOIL", REG, 34, 22, 1470, 220)]), 2.35, 4.75, 0.45),
    (text_png("t_sub", [("no engine. just wind.", REG, 44, 6, 1420, 235)]), 5.6, 8.4, 0.4),
    (text_png("t_end", [("SOPRA L'ACQUA", BOLD, 80, 14, 930, 255),
                        ("WING FOIL SESSION", REG, 32, 20, 1010, 210)]), 26.1, 27.9, 0.5),
]

inputs = ["-i", f"{S}/video_noaudio.mp4", "-i", f"{S}/mix.wav"]
fc = ["[0:v]noise=alls=2:allf=t+u,vignette=angle=PI/5.5[v0]"]
last = "v0"
for k, (png, t0, t1, fd) in enumerate(titles):
    inputs += ["-loop", "1", "-framerate", "24", "-t", f"{t1 - t0}", "-i", png]
    idx = k + 2
    fc.append(f"[{idx}:v]format=rgba,fade=in:st=0:d={fd}:alpha=1,fade=out:st={t1 - t0 - fd}:d={fd}:alpha=1,"
              f"setpts=PTS-STARTPTS+{t0}/TB[t{k}]")
    fc.append(f"[{last}][t{k}]overlay=0:0:eof_action=pass[v{k + 1}]")
    last = f"v{k + 1}"
fc.append(f"[{last}]fade=in:st=0:d=0.15,format=yuv420p[vout]")

out = f"{S}/sopra_l_acqua_wingfoil.mp4"
subprocess.run([FF, "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc),
                "-map", "[vout]", "-map", "1:a", "-c:v", "libx264", "-preset", "slower", "-crf", "19", "-maxrate", "8M", "-bufsize", "16M", "-tune", "film",
                "-profile:v", "high", "-r", "24", "-c:a", "aac", "-b:a", "192k", "-shortest",
                "-movflags", "+faststart", out], check=True)
print(out)
