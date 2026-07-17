import os
import sys
import subprocess
import hashlib

title_file = sys.argv[1]
output = sys.argv[2]
# Optional 3rd arg: a still frame pulled from the rendered video. When provided it is
# used as the thumbnail background (darkened) so each thumbnail contains original,
# per-video visual production instead of a flat template. Pass a clip/frame path here
# (e.g. a frame extracted from final_video.mp4) to enable it.
bg_image = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None

with open(title_file, "r", encoding="utf-8") as f:
    title = f.read().strip()

W, H = 1280, 720
# Env-driven for portability (Windows arial vs Docker/Linux DejaVu); falls back to Windows.
FONT_FILE = (
    os.environ.get("YT_FONT_BOLD")
    or os.environ.get("YT_FONT_FILE")
    or "C:/Windows/Fonts/arialbd.ttf"
)

# On-brand Nexiora palettes. Rotating through them removes the "same template with no
# variation" signal that YouTube's inauthentic-content policy flags, while keeping the
# dark + accent identity consistent.
PALETTES = [
    ("0x1a1a2e", "0xe94560"),  # navy / pink-red (primary Nexiora)
    ("0x0f3460", "0xe94560"),  # deep blue / pink-red
    ("0x16213e", "0x00b4d8"),  # navy / cyan
    ("0x1b1b2f", "0xf9a826"),  # charcoal / amber
    ("0x22223b", "0x4ea8de"),  # slate / sky blue
    ("0x2d132c", "0xee4540"),  # plum / red
]

# Deterministic per-title selection: the same topic always yields the same thumbnail,
# but different topics get different colors/layout -> natural variation across videos.
seed = int(hashlib.md5(title.encode("utf-8")).hexdigest(), 16)
BG_COLOR, ACCENT_COLOR = PALETTES[seed % len(PALETTES)]

# Vary vertical text placement (upper / center / lower third).
Y_POSITIONS = ["(h-text_h)/2", "h*0.15", "h*0.60"]
y_expr = Y_POSITIONS[(seed // 7) % len(Y_POSITIONS)]


def wrap_text(text, max_chars=22, max_lines=4):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".") + "..."
    return "\n".join(lines)


wrapped = wrap_text(title)

textfile_path = title_file + ".wrapped.txt"
with open(textfile_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(wrapped)

safe_font = FONT_FILE.replace(":", "\\:")
safe_textfile = textfile_path.replace("\\", "/").replace(":", "\\:")

drawtext = (
    f"drawtext=fontfile='{safe_font}':textfile='{safe_textfile}':"
    f"fontcolor=white:fontsize=70:line_spacing=16:"
    f"box=1:boxcolor={ACCENT_COLOR}@0.85:boxborderw=40:"
    f"text_align=center:x=(w-text_w)/2:y={y_expr}"
)

# Small "NEXIORA" brand watermark in the top-left corner of every thumbnail.
watermark = (
    f"drawtext=fontfile='{safe_font}':text='NEXIORA':"
    f"fontcolor=white@0.9:fontsize=34:"
    f"box=1:boxcolor={ACCENT_COLOR}@0.9:boxborderw=12:x=40:y=36"
)

if bg_image:
    # Use a real video frame, scaled/cropped to 1280x720 and darkened for text contrast.
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},eq=brightness=-0.25:saturation=1.1,"
        f"{drawtext},{watermark}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", bg_image,
        "-vf", vf,
        "-frames:v", "1",
        "-q:v", "2",
        output,
    ]
else:
    # Fall back to a solid brand-colored background.
    vf = f"{drawtext},{watermark}"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={BG_COLOR}:s={W}x{H}:d=1",
        "-vf", vf,
        "-frames:v", "1",
        "-q:v", "2",
        output,
    ]

result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    sys.stderr.write(result.stderr)
    sys.exit(1)

print(output)
