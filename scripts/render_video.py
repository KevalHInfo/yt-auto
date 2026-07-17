import os
import sys
import json
import subprocess

manifest_path = sys.argv[1]

with open(manifest_path, "r", encoding="utf-8") as f:
    manifest = json.load(f)

clips = manifest["clips"]
audio_path = manifest["audio"]
title_text = manifest.get("title", "")
output_path = manifest["output"]
clip_length = manifest.get("clipLength", 8)

W, H = 1280, 720
# Configurable so the same script works on Windows (arial) and in the Linux
# container (DejaVu, set via YT_FONT_FILE in docker-compose).
FONT_FILE = os.environ.get("YT_FONT_FILE", "C:/Windows/Fonts/arial.ttf")

inputs = []
filter_parts = []
for i, clip in enumerate(clips):
    inputs += ["-i", clip]
    filter_parts.append(
        f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1,fps=30,trim=0:{clip_length},setpts=PTS-STARTPTS[v{i}]"
    )

concat_inputs = "".join(f"[v{i}]" for i in range(len(clips)))
filter_parts.append(f"{concat_inputs}concat=n={len(clips)}:v=1:a=0[vcat]")

safe_title = (
    title_text.replace("\\", "\\\\")
    .replace(":", "\\:")
    .replace("'", "’")
)
safe_font = FONT_FILE.replace(":", "\\:")
filter_parts.append(
    f"[vcat]drawtext=fontfile='{safe_font}':text='{safe_title}':fontcolor=white:fontsize=48:"
    f"box=1:boxcolor=black@0.5:boxborderw=20:x=(w-text_w)/2:y=(h-text_h)/2:"
    f"enable='lte(t,3)'[vout]"
)

filter_complex = ";".join(filter_parts)

audio_index = len(clips)
inputs += ["-i", audio_path]

cmd = [
    "ffmpeg", "-y",
    *inputs,
    "-filter_complex", filter_complex,
    "-map", "[vout]",
    "-map", f"{audio_index}:a",
    "-shortest",
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    output_path,
]

result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    sys.stderr.write(result.stderr)
    sys.exit(1)

print(output_path)
