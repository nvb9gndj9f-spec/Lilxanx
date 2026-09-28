# Montaggio "Sopra l'acqua"

Script usati per creare l'edit dal girato originale (non incluso nel repo).
Mettere il video sorgente come `src.mp4` nella stessa cartella ed eseguire in ordine:

1. `build_video.py` – tagli, slow motion, reframe, color grading → `video_noaudio.mp4`
2. `build_audio.py` – colonna sonora sintetizzata, sound design, audio ambiente → `mix.wav`
3. `build_final.py` – titoli, grana, vignettatura, export → `sopra_l_acqua_wingfoil.mp4`

Richiede ffmpeg (percorso `FF` negli script), Python con numpy, scipy, pillow.
