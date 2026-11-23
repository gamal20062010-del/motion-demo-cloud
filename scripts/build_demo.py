import asyncio
import array
import json
import math
import subprocess
import wave
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont, features

WIDTH, HEIGHT = 1080, 1920
FPS = 30
BG = (12, 20, 38)
PANEL = (19, 31, 54)
GOLD = (230, 186, 74)
WHITE = (248, 250, 252)
MUTED = (171, 187, 207)
VOICE = "ar-SA-HamedNeural"
FONT_PATH = "assets/fonts/Cairo[slnt,wght].ttf"
CHAR_W, CHAR_H = 440, 660

SCENES = [
    {
        "id": 1, "badge": "المرحلة الأولى", "title": "التخطيط الدقيق",
        "text": "أَوَّلًا: التَّخْطِيطُ الدَّقِيقُ يُحَدِّدُ المَسَارَ وَيُقَلِّلُ المَخَاطِرَ.",
        "icon": "plan", "character": "navy", "entry_side": "right",
    },
    {
        "id": 2, "badge": "المرحلة الثانية", "title": "التنفيذ المنظم",
        "text": "ثَانِيًا: التَّنْفِيذُ المُنَظَّمُ يُحَوِّلُ الخُطَطَ إِلَى وَاقِعٍ مَلْمُوسٍ.",
        "icon": "execute", "character": "teal", "entry_side": "left",
    },
    {
        "id": 3, "badge": "المرحلة الثالثة", "title": "المتابعة المستمرة",
        "text": "ثَالِثًا: المُتَابَعَةُ المُسْتَمِرَّةُ تَضْمَنُ الجَوْدَةَ وَالِالْتِزَامَ بِالوَقْتِ.",
        "icon": "monitor", "character": "plum", "entry_side": "right",
    },
]

PALETTES = {
    "navy": {"skin": (211, 158, 119), "hair": (42, 32, 28), "shirt": (42, 76, 126), "shirt2": (25, 48, 89), "accent": (235, 190, 82)},
    "teal": {"skin": (194, 139, 104), "hair": (54, 38, 32), "shirt": (35, 142, 139), "shirt2": (23, 99, 104), "accent": (243, 202, 116)},
    "plum": {"skin": (228, 179, 139), "hair": (76, 47, 45), "shirt": (126, 83, 127), "shirt2": (79, 53, 92), "accent": (239, 190, 96)},
}


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, **kwargs)


def clamp01(value):
    return max(0.0, min(1.0, float(value)))


def ease_out_cubic(t):
    t = clamp01(t)
    return 1.0 - (1.0 - t) ** 3


def get_duration(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True).strip()
    return float(out)


async def generate_scene_audio(scene, out_dir):
    mp3_path = out_dir / f"scene_{scene['id']}.mp3"
    wav_path = out_dir / f"scene_{scene['id']}.wav"
    communicate = edge_tts.Communicate(scene["text"], VOICE)
    boundaries = []
    with mp3_path.open("wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                boundaries.append({
                    "text": chunk["text"],
                    "offset_s": round(chunk["offset"] / 10_000_000, 3),
                    "duration_s": round(chunk["duration"] / 10_000_000, 3),
                })
    if not mp3_path.exists() or mp3_path.stat().st_size == 0:
        raise RuntimeError(f"Edge TTS produced no audio for scene {scene['id']}")

    raw_duration = get_duration(mp3_path)
    padded_duration = max(4.8, raw_duration + 0.65)
    run([
        "ffmpeg", "-y", "-i", str(mp3_path),
        "-af", f"apad=whole_dur={padded_duration:.3f}",
        "-t", f"{padded_duration:.3f}", "-ar", "44100", "-ac", "2",
        "-acodec", "pcm_s16le", str(wav_path)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return {
        "scene_id": scene["id"],
        "audio_file": str(wav_path.resolve()),
        "duration_s": round(padded_duration, 3),
        "words": boundaries,
    }


def read_lip_sync_envelope(wav_path, frame_count):
    """Create one mouth-opening value per video frame from actual speech RMS."""
    with wave.open(str(wav_path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        if sample_width != 2:
            raise RuntimeError(f"Expected 16-bit PCM speech audio, got {sample_width * 8}-bit")
        raw = wav.readframes(wav.getnframes())
    samples = array.array("h")
    samples.frombytes(raw)
    if samples.itemsize != 2:
        raise RuntimeError("Unsupported PCM sample width for lip-sync")
    if len(samples) % channels:
        samples = samples[:len(samples) - (len(samples) % channels)]

    samples_per_frame = max(1, round(sample_rate / FPS))
    frame_samples = samples_per_frame * channels
    raw_rms = []
    for index in range(frame_count):
        start = index * frame_samples
        chunk = samples[start:start + frame_samples]
        if not chunk:
            raw_rms.append(0.0)
            continue
        square_sum = sum(int(value) * int(value) for value in chunk)
        raw_rms.append(math.sqrt(square_sum / len(chunk)) / 32768.0)

    peak = max(raw_rms, default=0.0)
    if peak < 0.0005:
        return [0.0] * frame_count

    normalized = [clamp01(value / peak) for value in raw_rms]
    mouth = [0.0] * frame_count
    previous = 0.0
    for i, value in enumerate(normalized):
        target = clamp01((value - 0.10) / 0.62)
        previous = previous * 0.38 + target * 0.62
        mouth[i] = previous
    return mouth


def draw_character(mouth_open, style, bob=0, gesture=0.0):
    """Draw an original transparent 2D presenter cutout with controllable mouth."""
    c = PALETTES[style]
    layer = Image.new("RGBA", (CHAR_W, CHAR_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    skin, hair = c["skin"], c["hair"]
    shirt, shirt2, accent = c["shirt"], c["shirt2"], c["accent"]

    d.ellipse((58, 625, 386, 655), fill=(0, 0, 0, 48))
    d.rounded_rectangle((151, 246 + bob, 289, 350 + bob), radius=34, fill=skin)
    d.rounded_rectangle((62, 315 + bob, 378, 672), radius=105, fill=shirt)
    d.polygon([(145, 302 + bob), (220, 350 + bob), (295, 302 + bob), (330, 670), (110, 670)], fill=shirt2)
    d.line([(85, 364 + bob), (40, 455 + bob), (78, 525 + bob)], fill=shirt, width=48, joint="curve")
    d.ellipse((53, 505 + bob, 99, 554 + bob), fill=skin)

    arm_raise = int(gesture * 20)
    d.line([(350, 365 + bob), (393, 300 + bob - arm_raise), (365, 242 + bob - arm_raise)], fill=shirt, width=48, joint="curve")
    d.ellipse((343, 213 + bob - arm_raise, 389, 264 + bob - arm_raise), fill=skin)
    d.line([(365, 220 + bob - arm_raise), (385, 194 + bob - arm_raise)], fill=skin, width=11)
    d.line([(357, 222 + bob - arm_raise), (355, 190 + bob - arm_raise)], fill=skin, width=10)

    d.polygon([(148, 306 + bob), (218, 360 + bob), (187, 434 + bob)], fill=(242, 244, 247))
    d.polygon([(292, 306 + bob), (218, 360 + bob), (250, 434 + bob)], fill=(228, 233, 240))
    d.polygon([(210, 356 + bob), (229, 356 + bob), (242, 465 + bob), (219, 493 + bob), (197, 465 + bob)], fill=accent)

    d.ellipse((100, 91, 151, 163), fill=skin)
    d.ellipse((288, 91, 339, 163), fill=skin)
    d.ellipse((119, 40, 321, 275), fill=skin, outline=(104, 70, 54), width=4)

    if style == "navy":
        d.pieslice((112, 25, 326, 170), 180, 355, fill=hair)
        d.ellipse((132, 25, 270, 105), fill=hair)
        d.polygon([(122, 123), (135, 63), (177, 85), (214, 44), (259, 84), (305, 58), (319, 135)], fill=hair)
    elif style == "teal":
        d.pieslice((110, 22, 330, 176), 180, 360, fill=hair)
        d.ellipse((132, 25, 280, 112), fill=hair)
        d.polygon([(121, 95), (151, 42), (192, 66), (222, 30), (274, 62), (314, 102)], fill=hair)
        # Keep the side-swept hairstyle clear of the face and mouth area.
    else:
        d.pieslice((110, 22, 330, 172), 180, 360, fill=hair)
        for hx, hy, radius in [(145, 63, 28), (179, 41, 31), (218, 35, 32), (259, 49, 31), (294, 78, 25)]:
            d.ellipse((hx-radius, hy-radius, hx+radius, hy+radius), fill=hair)

    d.line([(157, 145), (190, 139)], fill=hair, width=8)
    d.line([(246, 139), (279, 145)], fill=hair, width=8)
    d.ellipse((157, 151, 192, 181), fill=(255, 255, 255))
    d.ellipse((244, 151, 279, 181), fill=(255, 255, 255))
    d.ellipse((172, 157, 187, 178), fill=(37, 42, 52))
    d.ellipse((255, 157, 270, 178), fill=(37, 42, 52))
    d.ellipse((177, 160, 183, 166), fill=(255, 255, 255))
    d.ellipse((260, 160, 266, 166), fill=(255, 255, 255))
    d.arc((199, 166, 238, 208), 15, 155, fill=(153, 103, 79), width=5)

    m = clamp01(mouth_open)
    if m < 0.12:
        d.arc((190, 207, 249, 238), 10, 170, fill=(112, 48, 54), width=6)
    else:
        mouth_h = int(5 + m * 31)
        top = 220 - mouth_h // 2
        bottom = 220 + mouth_h // 2
        d.ellipse((196, top, 240, bottom), fill=(79, 31, 43), outline=(105, 48, 54), width=3)
        if m > 0.38:
            d.ellipse((205, bottom - max(8, mouth_h // 3), 233, bottom - 2), fill=(213, 104, 119))
        if m > 0.72:
            d.arc((198, top + 1, 238, top + 17), 180, 360, fill=(255, 220, 220), width=3)

    d.ellipse((137, 190, 158, 202), fill=(231, 145, 130, 95))
    d.ellipse((278, 190, 299, 202), fill=(231, 145, 130, 95))
    d.ellipse((310, 385 + bob, 345, 420 + bob), fill=accent)
    d.ellipse((320, 395 + bob, 335, 410 + bob), fill=shirt2)
    return layer


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


def draw_arabic_centered(draw, text, y, font, fill):
    kwargs = {"direction": "rtl", "language": "ar"}
    bbox = draw.textbbox((0, 0), text, font=font, **kwargs)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) // 2, y), text, font=font, fill=fill, **kwargs)


def draw_scene_background(scene, local_t, scene_dur, global_progress, fonts):
    font_badge, font_title, font_body, font_footer = fonts
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((42, 88, WIDTH-42, HEIGHT-72), radius=42, outline=(39, 55, 79), width=3)
    d.rounded_rectangle((75, 205, WIDTH-75, 1210), radius=34, fill=PANEL)
    d.rectangle((80, 150, WIDTH-80, 162), fill=(37, 51, 73))
    d.rectangle((80, 150, 80 + int((WIDTH-160)*global_progress), 162), fill=GOLD)

    enter = ease_out_cubic(local_t / 0.7)
    exit_progress = ease_out_cubic(max(0.0, (local_t - (scene_dur - 0.55)) / 0.55))
    alpha = min(enter, 1.0-exit_progress)
    title_y = 570 + int((1.0-enter)*38)
    draw_arabic_centered(d, scene["badge"], 485 + int((1.0-enter)*38), font_badge, GOLD)
    draw_arabic_centered(d, scene["title"], title_y, font_title, WHITE)
    d.rounded_rectangle((WIDTH//2-145, 700, WIDTH//2+145, 708), radius=4, fill=GOLD)

    y = 790 + int((1.0-enter)*38)
    for line in wrap_arabic(scene["text"], font_body, WIDTH-210):
        draw_arabic_centered(d, line, y, font_body, WHITE)
        y += 92

    d.rounded_rectangle((335, 1120, 745, 1184), radius=28, fill=(27, 42, 66), outline=(67, 83, 107), width=2)
    draw_arabic_centered(d, "المتحدث يشرح الفكرة", 1127, font_footer, MUTED)
    if alpha < 0.99:
        img = Image.blend(Image.new("RGB", (WIDTH, HEIGHT), BG), img, alpha)
    return img, alpha


def compose_frame(scene, frame_index, local_t, scene_duration, global_progress, fonts, mouth_value):
    frame, scene_alpha = draw_scene_background(scene, local_t, scene_duration, global_progress, fonts)
    side = 1 if scene["entry_side"] == "right" else -1
    target_x = 600 if side == 1 else 40
    start_x = WIDTH + 35 if side == 1 else -CHAR_W - 35
    exit_x = WIDTH + 35 if side == 1 else -CHAR_W - 35
    in_progress = ease_out_cubic(local_t / 0.82)
    out_progress = ease_out_cubic(max(0.0, (local_t - (scene_duration - 0.62)) / 0.62))
    x = int(start_x + (target_x - start_x) * in_progress + (exit_x - target_x) * out_progress)

    bob = int(math.sin(local_t * 4.2) * 5)
    gesture = 0.5 + 0.5 * math.sin(local_t * 3.2)
    character = draw_character(mouth_value, scene["character"], bob=bob, gesture=gesture)
    if scene_alpha < 0.999:
        alpha_channel = character.getchannel("A").point(lambda value: int(value * scene_alpha))
        character.putalpha(alpha_channel)
    frame_rgba = frame.convert("RGBA")
    frame_rgba.alpha_composite(character, (x, 1235 + bob))
    return frame_rgba.convert("RGB")


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
        raise RuntimeError("Final MP4 must contain both video and audio streams")
    if (video_stream.get("width"), video_stream.get("height")) != (WIDTH, HEIGHT):
        raise RuntimeError("Unexpected video dimensions")
    if video_stream.get("r_frame_rate") != f"{FPS}/1":
        raise RuntimeError("Unexpected frame rate")
    volume = subprocess.run([
        "ffmpeg", "-i", str(video_path), "-af", "volumedetect", "-f", "null", "-"
    ], capture_output=True, text=True)
    levels = [line.strip() for line in volume.stderr.splitlines() if "mean_volume:" in line or "max_volume:" in line]
    if volume.returncode != 0 or not levels:
        raise RuntimeError("Audio volume verification failed")
    report_path.write_text(
        "=== VIDEO/AUDIO STREAM INSPECTION ===\n" + json.dumps(data, ensure_ascii=False, indent=2)
        + "\n=== AUDIO VOLUMEDETECT ===\n" + "\n".join(levels)
        + f"\nExpected video frames: {expected_frames}\n"
        + "Lip-sync method: per-frame speech RMS envelope (audio-reactive approximation, not phoneme-level visemes).\n",
        encoding="utf-8"
    )
    print(report_path.read_text(encoding="utf-8"))


async def main():
    out_dir = Path("out")
    tmp_dir = Path("tmp_audio")
    out_dir.mkdir(exist_ok=True)
    tmp_dir.mkdir(exist_ok=True)
    if not features.check_feature("raqm"):
        raise RuntimeError("Pillow RAQM support is required for Arabic shaping")
    print("Pillow RAQM:", features.version_feature("raqm"))

    fonts = (
        ImageFont.truetype(FONT_PATH, 38),
        ImageFont.truetype(FONT_PATH, 78),
        ImageFont.truetype(FONT_PATH, 48),
        ImageFont.truetype(FONT_PATH, 30),
    )

    timings = []
    for scene in SCENES:
        timings.append(await generate_scene_audio(scene, tmp_dir))
    (out_dir / "timing.json").write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8")

    for scene in SCENES:
        sprite_sheet = Image.new("RGBA", (CHAR_W * 4, CHAR_H), (0, 0, 0, 0))
        for frame_no, mouth_state in enumerate((0.0, 0.28, 0.62, 1.0)):
            sprite_sheet.alpha_composite(draw_character(mouth_state, scene["character"]), (frame_no * CHAR_W, 0))
        sprite_sheet.save(out_dir / f"character_{scene['id']}_{scene['character']}_mouth_spritesheet.png", optimize=True)

    audio_list = tmp_dir / "concat.txt"
    audio_list.write_text("\n".join(f"file '{Path(t['audio_file']).as_posix()}'" for t in timings) + "\n", encoding="utf-8")
    full_audio = tmp_dir / "narration_full.wav"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(audio_list), "-c", "copy", str(full_audio)])

    frame_counts = [int(math.ceil(t["duration_s"] * FPS)) for t in timings]
    envelopes = [read_lip_sync_envelope(t["audio_file"], count) for t, count in zip(timings, frame_counts)]
    lip_sync_summary = []
    for scene, values in zip(SCENES, envelopes):
        maximum = max(values, default=0.0)
        if maximum < 0.12:
            raise RuntimeError(f"Lip-sync envelope is silent for scene {scene['id']}; check generated speech audio.")
        lip_sync_summary.append({
            "scene_id": scene["id"],
            "frames": len(values),
            "mouth_open_min": round(min(values, default=0.0), 4),
            "mouth_open_max": round(maximum, 4),
            "mouth_open_mean": round(sum(values) / max(1, len(values)), 4),
            "values": [round(value, 3) for value in values],
        })
    (out_dir / "lip_sync.json").write_text(json.dumps(lip_sync_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    total_frames = sum(frame_counts)
    video_path = out_dir / "demo_final.mp4"
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "rgb24", "-r", str(FPS), "-i", "-",
        "-i", str(full_audio), "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-t", f"{total_frames/FPS:.6f}", "-movflags", "+faststart", str(video_path)
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    frame_index = 0
    try:
        for scene, count, mouth_values in zip(SCENES, frame_counts, envelopes):
            scene_duration = count / FPS
            for local_index in range(count):
                progress = frame_index / max(1, total_frames - 1)
                frame = compose_frame(
                    scene, frame_index, local_index/FPS, scene_duration, progress,
                    fonts, mouth_values[local_index] if local_index < len(mouth_values) else 0.0
                )
                proc.stdin.write(frame.tobytes())
                frame_index += 1
    except BrokenPipeError as exc:
        raise RuntimeError("FFmpeg stopped while receiving video frames") from exc
    finally:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("FFmpeg encoding failed")

    verify_output(video_path, out_dir / "verification_report.txt", total_frames)


if __name__ == "__main__":
    asyncio.run(main())
