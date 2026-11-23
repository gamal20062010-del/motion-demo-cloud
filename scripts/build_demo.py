import asyncio
import json
import math
import shutil
import subprocess
from pathlib import Path

try:
    import edge_tts
except ImportError:
    edge_tts = None
from PIL import Image, ImageDraw, ImageFont, ImageFilter, features

# Motion Demo v4: persistent topic illustrations, calm transitions, and preserved source narration.
WIDTH, HEIGHT, FPS = 1080, 1920, 30
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "scripts" else SCRIPT_DIR
ASSETS = ROOT / "assets"
CUTOUTS = ASSETS / "cutouts"
FONT_PATH = ASSETS / "fonts" / "Cairo[slnt,wght].ttf"
VOICE_CANDIDATES = [ASSETS / "narration.wav", ASSETS / "narration.mp3", ASSETS / "narration.m4a"]
VOICE = "ar-SA-HamedNeural"

# TTS fallback is used only when no supplied narration file exists.
TTS_SCENES = [
    {"caption": "فَلَيْتَكَ تَحْلُو وَالْحَيَاةُ مُرِيرَةٌ", "speech": "فَلَيْتَكَ تَحْلُو وَالْحَيَاةُ مُرِيرَةٌ.", "visual": "book_quill", "palette": "rose", "side": "right"},
    {"caption": "وَلَيْتَكَ تَرْضَى وَالْأَنَامُ غِضَابُ", "speech": "وَلَيْتَكَ تَرْضَى وَالْأَنَامُ غِضَابُ.", "visual": "lantern", "palette": "lavender", "side": "left"},
    {"caption": "وَكُلُّ الَّذِي فَوْقَ التُّرَابِ تُرَابٌ", "speech": "وَكُلُّ الَّذِي فَوْقَ التُّرَابِ تُرَابٌ.", "visual": "river", "palette": "sky", "side": "right"},
]

PALETTES = {
    "rose": ((255, 244, 243), (250, 211, 211), (210, 119, 125), (75, 55, 63)),
    "lavender": ((250, 246, 255), (224, 211, 247), (145, 119, 183), (62, 51, 80)),
    "sky": ((242, 250, 255), (198, 229, 246), (73, 151, 185), (42, 65, 83)),
    "cream": ((255, 251, 239), (246, 228, 190), (193, 151, 79), (80, 64, 39)),
    "mint": ((241, 251, 244), (202, 232, 211), (86, 153, 117), (43, 72, 55)),
    "peach": ((255, 247, 235), (251, 218, 190), (199, 126, 85), (83, 56, 43)),
    "aqua": ((239, 252, 250), (190, 231, 226), (51, 153, 148), (34, 75, 74)),
}


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, **kwargs)


def probe_duration(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True).strip())


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def make_background(palette_name, scene_index):
    top, bottom, accent, ink = PALETTES[palette_name]
    img = Image.new("RGB", (WIDTH, HEIGHT))
    d = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / max(1, HEIGHT - 1)
        d.line((0, y, WIDTH, y), fill=lerp(top, bottom, t))

    # Large, soft editorial forms; static per scene to keep rendering efficient.
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    offset = (scene_index * 97) % 260
    od.ellipse((-220 + offset // 3, 180, 390 + offset // 3, 800), fill=(*accent, 35))
    od.ellipse((720 - offset // 4, 800, 1320 - offset // 4, 1450), fill=(255, 255, 255, 85))
    od.ellipse((80, 1450 - offset // 5, 510, 1875 - offset // 5), fill=(*accent, 24))
    for i in range(9):
        x = 82 + ((i * 113 + scene_index * 37) % 900)
        y = 190 + ((i * 157 + scene_index * 51) % 1460)
        r = 5 + (i % 3) * 3
        od.ellipse((x-r, y-r, x+r, y+r), fill=(*accent, 75 if i % 2 else 48))
    od.arc((750, 110, 1050, 410), 195, 325, fill=(*accent, 120), width=5)
    od.arc((30, 1470, 320, 1760), 15, 150, fill=(*accent, 100), width=4)
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((46, 62, WIDTH-46, HEIGHT-58), radius=48, outline=(255, 255, 255, 160), width=3)
    d.rounded_rectangle((92, 112, WIDTH-92, 124), radius=6, fill=(255, 255, 255, 125))
    return img


def draw_vector_cutout(name):
    # Antialiased, original 2D cutouts generated locally; users may override them with PNGs.
    scale, w, h = 2, 650, 630
    im = Image.new("RGBA", (w*scale, h*scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def box(coords):
        return tuple(int(v*scale) for v in coords)

    def poly(points, fill, outline=(65, 55, 62, 255), width=6):
        pts = [(int(x*scale), int(y*scale)) for x, y in points]
        d.polygon(pts, fill=fill)
        if outline:
            d.line(pts + [pts[0]], fill=outline, width=width*scale, joint="curve")

    def line(points, fill, width=5):
        d.line([(int(x*scale), int(y*scale)) for x, y in points], fill=fill, width=width*scale, joint="curve")

    def ellipse(coords, fill, outline=None, width=4):
        d.ellipse(box(coords), fill=fill, outline=outline, width=width*scale if outline else 1)

    if name == "book_quill":
        line([(145, 480), (95, 335), (74, 210)], (84, 133, 86, 255), 8)
        for x, y, r in [(84, 275, 28), (104, 345, 24), (72, 405, 22), (115, 225, 18)]:
            ellipse((x-r, y-r, x+r, y+r), (133, 173, 111, 255), (71, 111, 79, 255), 3)
        line([(520, 460), (565, 300), (590, 205)], (84, 133, 86, 255), 8)
        for x, y, r in [(563, 337, 24), (586, 265, 22), (535, 410, 20)]:
            ellipse((x-r, y-r, x+r, y+r), (153, 181, 115, 255), (71, 111, 79, 255), 3)
        ellipse((115, 535, 555, 610), (28, 34, 47, 35))
        poly([(100, 330), (300, 280), (330, 540), (115, 580)], (100, 61, 46, 255), (63, 42, 39, 255), 9)
        poly([(325, 540), (345, 278), (565, 327), (548, 580)], (108, 69, 48, 255), (63, 42, 39, 255), 9)
        poly([(118, 330), (300, 292), (322, 515), (130, 548)], (255, 237, 202, 255), (159, 117, 70, 255), 4)
        poly([(331, 515), (350, 292), (548, 332), (532, 548)], (255, 245, 219, 255), (159, 117, 70, 255), 4)
        line([(325, 305), (325, 535)], (169, 124, 76, 255), 5)
        for y in [365, 400, 435, 470]:
            line([(155, y), (278, y-22)], (195, 166, 123, 180), 3)
            line([(372, y-19), (510, y+2)], (195, 166, 123, 180), 3)
        poly([(306, 508), (328, 523), (321, 592), (304, 578)], (218, 167, 70, 255), (143, 97, 45, 255), 3)
        poly([(420, 500), (496, 500), (510, 564), (406, 564)], (42, 62, 77, 255), (40, 43, 51, 255), 6)
        d.rounded_rectangle(box((423, 476, 493, 511)), radius=9*scale, fill=(39, 45, 54, 255), outline=(196, 151, 77, 255), width=4*scale)
        d.rectangle(box((438, 457, 478, 480)), fill=(33, 39, 46, 255), outline=(196, 151, 77, 255), width=3*scale)
        poly([(392, 465), (420, 300), (520, 95), (535, 225), (470, 390)], (235, 194, 119, 255), (126, 88, 52, 255), 5)
        line([(400, 476), (488, 255), (530, 110)], (119, 82, 48, 255), 5)
        for i in range(7):
            yy = 180 + i*25
            line([(488-(yy-180)*.18, yy), (520-(yy-180)*.1, yy-28)], (255, 229, 170, 210), 3)

    elif name == "lantern":
        ellipse((232, 88, 418, 270), (248, 202, 122, 65))
        d.arc(box((275, 55, 375, 190)), 180, 360, fill=(126, 85, 46, 255), width=10*scale)
        line([(325, 140), (325, 182)], (177, 126, 62, 255), 9)
        poly([(250, 190), (400, 190), (455, 286), (435, 485), (215, 485), (195, 286)], (200, 145, 76, 255), (92, 67, 48, 255), 9)
        poly([(270, 225), (380, 225), (414, 298), (400, 438), (250, 438), (236, 298)], (255, 221, 155, 210), (133, 91, 52, 255), 5)
        poly([(272, 234), (323, 246), (323, 423), (255, 432)], (255, 246, 206, 160), None)
        poly([(330, 246), (378, 234), (394, 430), (330, 423)], (255, 188, 87, 115), None)
        line([(250, 190), (325, 230), (400, 190)], (112, 74, 42, 255), 7)
        line([(195, 286), (455, 286)], (116, 78, 43, 255), 8)
        line([(215, 485), (435, 485)], (111, 72, 40, 255), 9)
        line([(252, 210), (240, 458)], (139, 95, 49, 255), 7)
        line([(398, 210), (412, 458)], (139, 95, 49, 255), 7)
        poly([(235, 485), (415, 485), (375, 535), (275, 535)], (159, 106, 58, 255), (89, 60, 39, 255), 7)
        ellipse((299, 535, 351, 570), (237, 173, 73, 255), (114, 75, 44, 255), 5)
        for x, y, r in [(150, 210, 17), (490, 180, 14), (505, 420, 10), (145, 470, 11)]:
            line([(x-r, y), (x+r, y)], (209, 160, 75, 210), 3)
            line([(x, y-r), (x, y+r)], (209, 160, 75, 210), 3)
            ellipse((x-4, y-4, x+4, y+4), (255, 223, 159, 255))

    elif name == "river":
        ellipse((390, 72, 540, 222), (249, 199, 105, 255), (202, 145, 68, 255), 5)
        poly([(38, 390), (165, 220), (265, 340), (360, 220), (535, 400), (585, 535), (52, 535)], (129, 171, 160, 255), (74, 118, 112, 255), 6)
        poly([(85, 440), (210, 300), (310, 424), (402, 300), (555, 460), (555, 560), (85, 560)], (170, 200, 177, 255), (100, 142, 128, 255), 4)
        poly([(25, 470), (145, 430), (230, 470), (315, 445), (410, 472), (560, 435), (620, 545), (530, 580), (410, 555), (300, 583), (185, 548), (60, 585)], (64, 159, 171, 255), (43, 111, 131, 255), 7)
        line([(80, 500), (165, 477), (250, 505), (335, 479), (430, 506), (535, 478)], (200, 238, 224, 255), 8)
        line([(120, 545), (220, 528), (315, 550), (410, 530), (520, 550)], (240, 247, 220, 230), 5)
        line([(118, 485), (140, 278), (165, 182)], (107, 83, 55, 255), 13)
        for points in [
            [(165, 190), (100, 140), (50, 132)],
            [(165, 190), (120, 93), (87, 70)],
            [(165, 190), (204, 98), (250, 68)],
            [(165, 190), (250, 145), (297, 142)],
            [(165, 190), (90, 220), (45, 250)],
        ]:
            line(points, (73, 135, 92, 255), 10)
            for t in range(1, 5):
                x = points[0][0] + (points[-1][0] - points[0][0]) * t / 5
                y = points[0][1] + (points[-1][1] - points[0][1]) * t / 5
                line([(x, y), (x-14, y-13)], (108, 163, 111, 255), 4)
    else:
        raise ValueError(f"Unknown vector cutout: {name}")
    return im.resize((w, h), Image.Resampling.LANCZOS)




def load_cutouts():
    result = {}
    for name in ("book_quill", "lantern", "river"):
        path = CUTOUTS / f"{name}.png"
        im = Image.open(path).convert("RGBA") if path.exists() else draw_vector_cutout(name)
        im.thumbnail((650, 630), Image.Resampling.LANCZOS)
        def make_shadow(source, amount=42, blur=12):
            sh = Image.new("RGBA", source.size, (0, 0, 0, 0))
            sh.putalpha(source.getchannel("A").point(lambda value: value * amount // 255))
            return sh.filter(ImageFilter.GaussianBlur(blur))
        compact = im.resize((470, 455), Image.Resampling.LANCZOS)
        result[name] = {
            "normal": (im, make_shadow(im)),
            "compact": (compact, make_shadow(compact, amount=42, blur=10)),
        }
    return result


def wrap_arabic(draw, text, font, max_width):
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            box = draw.textbbox((0, 0), candidate, font=font, direction="rtl", language="ar")
            if current and box[2] - box[0] > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
    return lines


def make_caption_card(scene, fonts):
    font_badge, font_caption = fonts
    _, _, accent, ink = PALETTES[scene["palette"]]
    card = Image.new("RGBA", (WIDTH, 760), (0, 0, 0, 0))
    shadow = Image.new("RGBA", card.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((68, 32, WIDTH-68, 716), radius=52, fill=(48, 43, 54, 30))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    card.alpha_composite(shadow)
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((58, 20, WIDTH-58, 700), radius=48, fill=(255, 255, 255, 218), outline=(255, 255, 255, 255), width=3)
    d.rounded_rectangle((WIDTH//2-72, 58, WIDTH//2+72, 70), radius=6, fill=(*accent, 255))
    lines = wrap_arabic(d, scene["caption"], font_caption, WIDTH-210)
    size = 62 if len(lines) <= 2 else 54
    actual_font = ImageFont.truetype(str(FONT_PATH), size)
    line_gap = 92 if size == 62 else 80
    total_h = len(lines) * line_gap
    y = 330 - total_h // 2
    for line in lines:
        d.text((WIDTH//2, y), line, font=actual_font, fill=(*ink, 255), anchor="mm", direction="rtl", language="ar", stroke_width=0)
        y += line_gap
    d.rounded_rectangle((WIDTH//2-205, 628, WIDTH//2+205, 638), radius=5, fill=(229, 225, 220, 255))
    return card


def fade_rgba(image, opacity):
    opacity = max(0.0, min(1.0, float(opacity)))
    if opacity >= 0.999:
        return image
    result = image.copy()
    result.putalpha(result.getchannel("A").point(lambda value: int(value * opacity)))
    return result


def composite_persistent_cutout(canvas, cutout_pack, topic_time, opacity=1.0):
    """Keep one topic illustration on screen with restrained, continuous idle movement."""
    image, shadow = cutout_pack
    scale = 1.0 + 0.012 * math.sin(max(0.0, topic_time) * 0.42)
    if abs(scale - 1.0) > 0.002:
        size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        image = image.resize(size, Image.Resampling.LANCZOS)
        shadow = shadow.resize(size, Image.Resampling.LANCZOS)
    image = fade_rgba(image, opacity)
    shadow = fade_rgba(shadow, opacity)
    x = (WIDTH - image.width) // 2 + int(4 * math.sin(max(0.0, topic_time) * 0.24))
    y = 1000 + int(5 * math.sin(max(0.0, topic_time) * 0.48))
    canvas.alpha_composite(shadow, (x + 8, y + 15))
    canvas.alpha_composite(image, (x, y))


def draw_frame(
    scene, local_t, duration, global_progress, background, previous_background,
    cutouts, card, topic_time, transition_progress, previous_visual=None
):
    if previous_background is not None and local_t < 0.72:
        bg = Image.blend(previous_background, background, ease(local_t / 0.72))
    else:
        bg = background.copy()
    d = ImageDraw.Draw(bg)
    rail_width = WIDTH - 184
    d.rounded_rectangle((92, 112, WIDTH-92, 124), radius=6, fill=(255, 255, 255, 125))
    d.rounded_rectangle((92, 112, 92 + int(rail_width*global_progress), 124), radius=6,
                        fill=(*PALETTES[scene["palette"]][2], 255))
    # The caption remains anchored; only its wording changes at the authored phrase boundaries.
    card_y = 205
    bg.alpha_composite(card, (0, card_y))
    d = ImageDraw.Draw(bg)
    _, _, accent, _ = PALETTES[scene["palette"]]
    caption_progress = max(0.0, min(1.0, local_t / max(0.01, duration)))
    underline_x = WIDTH//2 - 205
    d.rounded_rectangle((underline_x, card_y+628, underline_x+410, card_y+638), radius=5, fill=(229, 225, 220, 255))
    d.rounded_rectangle((underline_x, card_y+628, underline_x+int(410*caption_progress), card_y+638), radius=5, fill=(*accent, 255))
    # Cross-fade only at a real visual/topic change, not at every caption change.
    if previous_visual and transition_progress < 1.0:
        composite_persistent_cutout(bg, cutouts[previous_visual], 0.0, 1.0-transition_progress)
        composite_persistent_cutout(bg, cutouts[scene["visual"]], topic_time, transition_progress)
    else:
        initial_opacity = ease(topic_time / 0.65) if topic_time < 0.65 else 1.0
        composite_persistent_cutout(bg, cutouts[scene["visual"]], topic_time, initial_opacity)
    d = ImageDraw.Draw(bg)
    for i in range(4):
        x = int(90 + ((i*223 + scene.get("scene_no", 1)*61 + topic_time*3.0) % 900))
        y = int(900 + (i*151) % 700 + math.sin(topic_time*0.55+i)*5)
        r = 4 + (i % 2) * 3
        d.ellipse((x-r, y-r, x+r, y+r), fill=(*accent, 115))
    return bg.convert("RGB")


def find_voiceover():
    return next((p for p in VOICE_CANDIDATES if p.exists() and p.stat().st_size > 0), None)


async def make_tts_audio(scenes, tmp_dir):
    if edge_tts is None:
        raise RuntimeError("edge-tts is required when no source narration file is supplied")
    timing = []
    for index, scene in enumerate(scenes, 1):
        wav_path = tmp_dir / f"tts_{index:02d}.wav"
        mp3_path = tmp_dir / f"tts_{index:02d}.mp3"
        comm = edge_tts.Communicate(scene["speech"], VOICE)
        with mp3_path.open("wb") as f:
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
        if not mp3_path.exists() or mp3_path.stat().st_size == 0:
            raise RuntimeError(f"Edge TTS returned an empty audio file for scene {index}")
        duration = probe_duration(mp3_path) + 0.45
        run([
            "ffmpeg", "-y", "-i", str(mp3_path), "-af", f"apad=whole_dur={duration:.3f}",
            "-t", f"{duration:.3f}", "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(wav_path)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        timing.append({**scene, "scene_no": index, "audio_path": str(wav_path.resolve()), "duration_s": duration})

    concat = tmp_dir / "concat.txt"
    concat.write_text("\n".join(f"file '{x['audio_path']}'" for x in timing) + "\n", encoding="utf-8")
    full = tmp_dir / "narration_full.wav"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(full)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    total = sum(x["duration_s"] for x in timing)
    timeline = []
    current = 0.0
    for row in timing:
        start = current
        end = start + row["duration_s"]
        timeline.append({**row, "start": start, "end": end})
        current = end
    return full, timeline, total, "edge-tts"


def use_source_audio(audio_path):
    duration = probe_duration(audio_path)
    config_path = ASSETS / "scenes.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if isinstance(config, dict):
            source_scenes = config.get("scenes", [])
        elif isinstance(config, list):
            source_scenes = config
        else:
            source_scenes = []
        if not isinstance(source_scenes, list) or not source_scenes:
            raise ValueError("assets/scenes.json must contain a non-empty scenes array")
    else:
        example_path = ASSETS / "scenes.example.json"
        if not example_path.exists():
            raise FileNotFoundError("Add assets/scenes.example.json or a custom assets/scenes.json")
        example = json.loads(example_path.read_text(encoding="utf-8"))
        source_scenes = example.get("scenes", []) if isinstance(example, dict) else example

    timeline = []
    for index, scene in enumerate(source_scenes, 1):
        required = ("start", "end", "caption", "visual", "palette")
        missing = [key for key in required if key not in scene]
        if missing:
            raise ValueError(f"Scene {index} is missing required keys: {', '.join(missing)}")
        if scene["visual"] not in ("book_quill", "lantern", "river"):
            raise ValueError(f"Scene {index} uses an unknown visual cutout: {scene['visual']}")
        if scene["palette"] not in PALETTES:
            raise ValueError(f"Scene {index} uses an unknown palette: {scene['palette']}")
        start = max(0.0, min(duration, float(scene["start"])))
        end = max(0.0, min(duration, float(scene["end"])))
        if end <= start:
            continue
        timeline.append({**scene, "scene_no": index, "side": scene.get("side", "right"),
                         "start": start, "end": end, "duration_s": end-start})
    if timeline:
        timeline[-1]["end"] = duration
        timeline[-1]["duration_s"] = duration - timeline[-1]["start"]
    if not timeline:
        raise ValueError("No scene timing overlaps the supplied narration audio")
    if timeline[0]["start"] > 0.05:
        raise ValueError("Scene timing must begin at 0 seconds")
    for previous, current in zip(timeline, timeline[1:]):
        if abs(current["start"] - previous["end"]) > 0.08:
            raise ValueError("Scene timing must be chronological and continuous; fix gaps or overlaps in assets/scenes.json")
    return audio_path, timeline, duration, "supplied-original-audio"


def verify_output(video_path, audio_source, report_path, frame_count, audio_mode):
    probe = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,width,height,r_frame_rate,sample_rate,channels",
        "-of", "json", str(video_path)
    ], text=True)
    data = json.loads(probe)
    streams = data.get("streams", [])
    v = next((x for x in streams if x.get("codec_type") == "video"), None)
    a = next((x for x in streams if x.get("codec_type") == "audio"), None)
    if not v or not a:
        raise RuntimeError("The final MP4 must contain video and audio streams")
    if (v.get("width"), v.get("height")) != (WIDTH, HEIGHT):
        raise RuntimeError("Unexpected video frame dimensions")
    if v.get("r_frame_rate") != f"{FPS}/1":
        raise RuntimeError("Unexpected video frame rate")
    volume = subprocess.run([
        "ffmpeg", "-hide_banner", "-i", str(video_path), "-af", "ebur128=peak=true", "-f", "null", "-"
    ], capture_output=True, text=True)
    lines = volume.stderr.splitlines()
    start = next((i for i, line in enumerate(lines) if "Summary:" in line), max(0, len(lines)-18))
    audio_summary = "\n".join(lines[start:])
    voice_note = (
        "Voice preservation: the original supplied recording is kept; only mild loudness/true-peak adjustment and AAC encoding are applied, with no pitch conversion or cloning.\n"
        if audio_mode == "supplied-original-audio"
        else "Voice generation: Edge TTS created the built-in demonstration narration because no supplied voice file was found.\n"
    )
    report = (
        f"Audio mode: {audio_mode}\n"
        f"Audio source: {audio_source}\n"
        f"Video frame count: {frame_count}\n"
        + voice_note
        + "No speaking cartoon characters are used. Topic illustrations remain visible across caption changes and cross-fade only when the visual subject changes.\n"
        + "\n"
        "=== FFPROBE ===\n" + json.dumps(data, ensure_ascii=False, indent=2)
        + "\n\n=== EBU R128 AUDIO SUMMARY ===\n" + audio_summary + "\n"
    )
    report_path.write_text(report, encoding="utf-8")
    print(report)


async def main():
    out_dir = ROOT / "out"
    tmp_dir = ROOT / "tmp_audio"
    out_dir.mkdir(exist_ok=True)
    tmp_dir.mkdir(exist_ok=True)
    if not features.check_feature("raqm"):
        raise RuntimeError("Pillow RAQM is required for properly shaped Arabic text")
    if not FONT_PATH.exists():
        raise FileNotFoundError(f"Missing Arabic font: {FONT_PATH}")

    cutouts = load_cutouts()
    fonts = (ImageFont.truetype(str(FONT_PATH), 34), ImageFont.truetype(str(FONT_PATH), 62))
    source_audio = find_voiceover()
    if source_audio:
        audio_path, timeline, audio_duration, audio_mode = use_source_audio(source_audio)
    else:
        audio_path, timeline, audio_duration, audio_mode = await make_tts_audio(TTS_SCENES, tmp_dir)

    (out_dir / "timing.json").write_text(json.dumps({
        "audio_mode": audio_mode,
        "audio_duration_s": round(audio_duration, 3),
        "scenes": [{k: v for k, v in row.items() if k not in ("audio_path",)} for row in timeline],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # Reuse the same background and illustration across consecutive caption phrases.
    backgrounds, cards = [], []
    background_cache = {}
    visual_group_start = []
    previous_visual_key = None
    current_group_start = 0.0
    for index, scene in enumerate(timeline, 1):
        scene["scene_no"] = index
        if scene["palette"] not in background_cache:
            background_cache[scene["palette"]] = make_background(scene["palette"], 1)
        backgrounds.append(background_cache[scene["palette"]])
        cards.append(make_caption_card(scene, fonts))
        if scene["visual"] != previous_visual_key:
            current_group_start = scene["start"]
            previous_visual_key = scene["visual"]
        visual_group_start.append(current_group_start)

    visual_groups = []
    for scene in timeline:
        if not visual_groups or visual_groups[-1]["visual"] != scene["visual"]:
            visual_groups.append({
                "start": scene["start"], "end": scene["end"],
                "visual": scene["visual"], "palette": scene["palette"],
                "topic": scene.get("topic", scene["visual"]),
                "captions": [scene["caption"]],
            })
        else:
            visual_groups[-1]["end"] = scene["end"]
            visual_groups[-1]["captions"].append(scene["caption"])
    (out_dir / "visual_groups.json").write_text(
        json.dumps(visual_groups, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    frame_count = int(math.ceil(audio_duration * FPS))
    video_path = out_dir / "demo_final.mp4"
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "rgb24", "-r", str(FPS), "-i", "-",
        "-i", str(audio_path), "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-af", "loudnorm=I=-17.5:TP=-1.5:LRA=8", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
        "-t", f"{frame_count/FPS:.6f}", "-movflags", "+faststart", str(video_path)
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    frame_index = 0
    try:
        for idx, scene in enumerate(timeline):
            start_frame = int(round(scene["start"] * FPS))
            end_frame = int(round(scene["end"] * FPS))
            if idx == len(timeline)-1:
                end_frame = frame_count
            previous_scene = timeline[idx-1] if idx > 0 else None
            visual_changed = previous_scene is not None and previous_scene["visual"] != scene["visual"]
            palette_changed = previous_scene is not None and previous_scene["palette"] != scene["palette"]
            previous_visual = previous_scene["visual"] if visual_changed else None
            previous_bg = backgrounds[idx-1] if palette_changed else None
            duration = max(0.01, scene["end"] - scene["start"])
            topic_start = visual_group_start[idx]
            for absolute_frame in range(start_frame, end_frame):
                absolute_t = absolute_frame / FPS
                local_t = absolute_t - scene["start"]
                topic_t = absolute_t - topic_start
                progress = absolute_frame/max(1, frame_count-1)
                transition_progress = ease(local_t / 0.72) if visual_changed else 1.0
                frame = draw_frame(
                    scene, local_t, duration, progress, backgrounds[idx], previous_bg,
                    cutouts, cards[idx], topic_t, transition_progress, previous_visual
                )
                proc.stdin.write(frame.tobytes())
                frame_index += 1
    except BrokenPipeError as exc:
        raise RuntimeError("FFmpeg stopped while receiving frames") from exc
    finally:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("FFmpeg encoding failed")
    if frame_index != frame_count:
        raise RuntimeError(f"Rendered {frame_index} frames but expected {frame_count}; check scene timing for gaps.")

    verify_output(video_path, audio_path, out_dir / "verification_report.txt", frame_index, audio_mode)
    print(f"Rendered {video_path} with {len(timeline)} scenes and {frame_index} frames")


if __name__ == "__main__":
    asyncio.run(main())
