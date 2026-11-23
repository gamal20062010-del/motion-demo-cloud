import asyncio
import json
import math
import subprocess
import textwrap
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont, features

WIDTH, HEIGHT = 1080, 1920
FPS = 30
BG_COLOR = (15, 23, 42)
GOLD = (212, 175, 55)
WHITE = (248, 250, 252)
VOICE = "ar-SA-HamedNeural"
FONT_PATH = "assets/fonts/Cairo[slnt,wght].ttf"

SCENES = [
    {
        "id": 1, "badge": "المرحلة الأولى", "title": "التخطيط الدقيق",
        "text": "أَوَّلًا: التَّخْطِيطُ الدَّقِيقُ يُحَدِّدُ المَسَارَ وَيُقَلِّلُ المَخَاطِرَ.",
        "icon": "plan",
    },
    {
        "id": 2, "badge": "المرحلة الثانية", "title": "التنفيذ المنظم",
        "text": "ثَانِيًا: التَّنْفِيذُ المُنَظَّمُ يُحَوِّلُ الخُطَطَ إِلَى وَاقِعٍ مَلْمُوسٍ.",
        "icon": "execute",
    },
    {
        "id": 3, "badge": "المرحلة الثالثة", "title": "المتابعة المستمرة",
        "text": "ثَالِثًا: المُتَابَعَةُ المُسْتَمِرَّةُ تَضْمَنُ الجَوْدَةَ وَالِالْتِزَامَ بِالوَقْتِ.",
        "icon": "monitor",
    },
]


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, **kwargs)


def ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def get_duration(file_path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)
    ], text=True).strip()
    return float(out)


async def generate_scene_audio(scene, out_dir):
    mp3_path = out_dir / f"scene_{scene['id']}.mp3"
    communicate = edge_tts.Communicate(scene["text"], VOICE)
    boundaries = []

    with mp3_path.open("wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                boundaries.append({
                    "text": chunk["text"],
                    "offset_s": round(chunk["offset"] / 10_000_000, 3),
                    "duration_s": round(chunk["duration"] / 10_000_000, 3),
                })

    if not mp3_path.exists() or mp3_path.stat().st_size == 0:
        raise RuntimeError(f"Edge TTS produced no audio for scene {scene['id']}")

    raw_dur = get_duration(mp3_path)
    target_dur = max(4.8, raw_dur + 0.5)
    wav_path = out_dir / f"scene_{scene['id']}.wav"
    run([
        "ffmpeg", "-y", "-i", str(mp3_path), "-af", f"apad=whole_dur={target_dur:.3f}",
        "-t", f"{target_dur:.3f}", "-ar", "44100", "-ac", "2", str(wav_path)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return {
        "scene_id": scene["id"],
        "audio_file": str(wav_path.resolve()),
        "duration_s": round(target_dur, 3),
        "words": boundaries,
    }


def draw_icon(draw, icon_type, cx, cy, progress):
    r = int(95 * ease_out_cubic(progress))
    if r < 5:
        return
    draw.ellipse((cx-r-25, cy-r-25, cx+r+25, cy+r+25), outline=GOLD, width=5)
    if icon_type == "plan":
        s = int(r * 0.65)
        draw.rectangle((cx-s, cy-s, cx+s, cy+s), outline=WHITE, width=5)
        draw.line((cx-s, cy, cx+s, cy), fill=GOLD, width=4)
        draw.line((cx, cy-s, cx, cy+s), fill=GOLD, width=4)
    elif icon_type == "execute":
        s = int(r * 0.45)
        draw.ellipse((cx-s-22, cy-s-10, cx+s-22, cy+s-10), outline=WHITE, width=6)
        draw.ellipse((cx-s+26, cy-s+16, cx+s+26, cy+s+16), outline=GOLD, width=6)
    elif icon_type == "monitor":
        p1 = (cx-int(r*.45), cy+int(r*.05))
        p2 = (cx-int(r*.1), cy+int(r*.4))
        p3 = (cx+int(r*.5), cy-int(r*.35))
        draw.line([p1, p2, p3], fill=WHITE, width=10, joint="curve")


def draw_arabic_centered(draw, text, y, font, fill):
    kwargs = {"direction": "rtl", "language": "ar"}
    bbox = draw.textbbox((0, 0), text, font=font, **kwargs)
    width = bbox[2] - bbox[0]
    draw.text(((WIDTH-width)//2, y), text, font=font, fill=fill, **kwargs)


def wrap_arabic(text, font, max_width):
    words = text.split()
    lines, current = [], ""
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    kwargs = {"direction": "rtl", "language": "ar"}
    for word in words:
        candidate = f"{current} {word}".strip()
        bbox = probe.textbbox((0, 0), candidate, font=font, **kwargs)
        if current and bbox[2] - bbox[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def render_frame(scene, local_t, scene_dur, global_progress, fonts):
    font_badge, font_title, font_body = fonts
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((60, 120, WIDTH-60, HEIGHT-120), radius=36, outline=(30, 41, 59), width=4)

    bar_w = int((WIDTH-160) * global_progress)
    draw.rectangle((80, 160, WIDTH-80, 170), fill=(30, 41, 59))
    draw.rectangle((80, 160, 80+bar_w, 170), fill=GOLD)

    in_p = ease_out_cubic(local_t / 0.7)
    out_p = 1.0 - ease_out_cubic(max(0.0, (local_t-(scene_dur-0.45))/0.45))
    slide_y = int((1.0-in_p) * 60)

    draw_icon(draw, scene["icon"], WIDTH//2, 560+slide_y//2, in_p)
    draw_arabic_centered(draw, scene["badge"], 770+slide_y, font_badge, GOLD)
    draw_arabic_centered(draw, scene["title"], 860+slide_y, font_title, WHITE)

    line_half = int(180*in_p)
    draw.line((WIDTH//2-line_half, 1000, WIDTH//2+line_half, 1000), fill=GOLD, width=5)

    y = 1090 + slide_y
    for line in wrap_arabic(scene["text"], font_body, WIDTH-220):
        draw_arabic_centered(draw, line, y, font_body, WHITE)
        y += 95

    alpha = min(in_p, out_p)
    if alpha < 0.99:
        img = Image.blend(Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR), img, alpha)
    return img


def verify_output(video_path, report_path, expected_frames):
    probe = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,width,height,r_frame_rate,duration",
        "-of", "json", str(video_path)
    ], text=True)
    data = json.loads(probe)
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not video_stream or not audio_stream:
        raise RuntimeError("Final MP4 must contain both video and audio streams.")
    if (video_stream.get("width"), video_stream.get("height")) != (WIDTH, HEIGHT):
        raise RuntimeError("Unexpected video dimensions.")
    if video_stream.get("r_frame_rate") != f"{FPS}/1":
        raise RuntimeError("Unexpected frame rate.")

    vol = subprocess.run([
        "ffmpeg", "-i", str(video_path), "-af", "volumedetect", "-f", "null", "-"
    ], capture_output=True, text=True)
    volume_lines = [line for line in vol.stderr.splitlines() if "mean_volume:" in line or "max_volume:" in line]
    if vol.returncode != 0 or not volume_lines:
        raise RuntimeError("Audio volume verification failed.")

    report = (
        "=== VIDEO/AUDIO STREAM INSPECTION ===\n"
        + json.dumps(data, ensure_ascii=False, indent=2)
        + "\n=== AUDIO VOLUMEDETECT ===\n"
        + "\n".join(volume_lines)
        + f"\nExpected video frames: {expected_frames}\n"
    )
    report_path.write_text(report, encoding="utf-8")
    print(report)


async def main():
    out_dir = Path("out")
    tmp_dir = Path("tmp_audio")
    out_dir.mkdir(exist_ok=True)
    tmp_dir.mkdir(exist_ok=True)

    if not features.check_feature("raqm"):
        raise RuntimeError("Pillow RAQM support is required for Arabic shaping.")
    print("Pillow RAQM:", features.version_feature("raqm"))

    timings = []
    for scene in SCENES:
        timings.append(await generate_scene_audio(scene, tmp_dir))

    (out_dir / "timing.json").write_text(
        json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    concat_list = tmp_dir / "concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{Path(t['audio_file']).as_posix()}'" for t in timings) + "\n",
        encoding="utf-8"
    )
    full_audio = tmp_dir / "narration_full.wav"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(full_audio)])

    # Use integer frame counts and derive each scene duration from its frame count.
    frame_counts = [int(math.ceil(t["duration_s"] * FPS)) for t in timings]
    total_frames = sum(frame_counts)
    video_path = out_dir / "demo_final.mp4"
    fonts = (
        ImageFont.truetype(FONT_PATH, 46),
        ImageFont.truetype(FONT_PATH, 86),
        ImageFont.truetype(FONT_PATH, 54),
    )

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-", "-i", str(full_audio),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-t", f"{total_frames/FPS:.6f}", "-movflags", "+faststart", str(video_path)
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    frame_idx = 0
    try:
        for scene, t_info, count in zip(SCENES, timings, frame_counts):
            scene_duration = count / FPS
            for f in range(count):
                local_t = f / FPS
                progress = frame_idx / max(1, total_frames-1)
                frame = render_frame(scene, local_t, scene_duration, progress, fonts)
                proc.stdin.write(frame.tobytes())
                frame_idx += 1
    except BrokenPipeError as exc:
        raise RuntimeError("FFmpeg stopped while receiving video frames.") from exc
    finally:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("FFmpeg encoding failed.")

    verify_output(video_path, out_dir / "verification_report.txt", total_frames)


if __name__ == "__main__":
    asyncio.run(main())
