#!/usr/bin/env python3
"""Generate deterministic smoke-test assets for Arabic Kinetic Video.

The generated narration is synthetic Arabic speech (espeak-ng/espeak), not a
replacement for a real speaker recording. All images are transparent PNGs
with an identical 3:4 canvas and matching composition.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
TIMELINE_PATH = ROOT / "src/data/timeline.json"

TEST_WORDS = {
    "word-001": "نحوّل",
    "word-002": "المعنى",
    "word-003": "إلى",
    "word-004": "مشاهد",
    "word-005": "مرئية",
    "word-006": "تتحرك",
    "word-007": "الكلمات",
    "word-008": "مع",
    "word-009": "الصوت",
    "word-010": "بإيقاعٍ متناسق",
}
TEST_VERTICAL_LABEL = "الفكرة"


def require_binary(*names: str) -> str:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    raise RuntimeError(f"Required executable not found: one of {', '.join(names)}")


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, cwd=ROOT)


def draw_asset(index: int, output: Path) -> None:
    """Draw same-size, same-position geometric cutout assets (transparent PNG)."""
    scale = 3
    width, height = 900, 1200
    canvas = Image.new("RGBA", (width * scale, height * scale), (255, 255, 255, 0))
    draw = ImageDraw.Draw(canvas)

    palettes = [
        ((201, 79, 118, 255), (248, 176, 184, 255), (78, 77, 100, 255)),
        ((108, 132, 170, 255), (186, 204, 225, 255), (69, 78, 104, 255)),
        ((118, 151, 119, 255), (197, 218, 179, 255), (76, 91, 77, 255)),
        ((160, 124, 178, 255), (218, 194, 232, 255), (94, 76, 111, 255)),
    ]
    main, light, dark = palettes[index - 1]

    def xy(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
        return [(x * scale, y * scale) for x, y in points]

    # Soft but contained shadow under the central cutout object.
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse((225 * scale, 1000 * scale, 675 * scale, 1070 * scale), fill=(38, 31, 45, 55))
    shadow = shadow.filter(ImageFilter.GaussianBlur(22 * scale))
    canvas.alpha_composite(shadow)

    # Three layered geometric plates, locked to identical coordinates.
    draw.polygon(xy([(450, 145), (670, 265), (670, 790), (450, 930), (230, 790), (230, 265)]), fill=dark)
    draw.polygon(xy([(450, 165), (630, 270), (630, 760), (450, 865), (270, 760), (270, 270)]), fill=light)
    draw.polygon(xy([(450, 235), (565, 300), (565, 710), (450, 780), (335, 710), (335, 300)]), fill=main)

    # Identical motif placement; palette changes make the image swap obvious.
    draw.polygon(xy([(450, 335), (535, 390), (450, 445), (365, 390)]), fill=(255, 255, 255, 235))
    draw.polygon(xy([(365, 510), (450, 565), (450, 690), (365, 635)]), fill=dark)
    draw.polygon(xy([(535, 510), (450, 565), (450, 690), (535, 635)]), fill=light)
    draw.ellipse((414 * scale, 820 * scale, 486 * scale, 892 * scale), fill=(255, 255, 255, 235))

    # A slim outer accent line reinforces a crisp, cut-out silhouette.
    draw.line(xy([(450, 145), (670, 265), (670, 790), (450, 930), (230, 790), (230, 265), (450, 145)]),
              fill=(255, 255, 255, 230), width=5 * scale, joint="curve")

    canvas = canvas.resize((width, height), Image.Resampling.LANCZOS)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)


def update_timeline() -> dict[str, Any]:
    data = json.loads(TIMELINE_PATH.read_text(encoding="utf-8"))
    for scene in data["scenes"]:
        if scene.get("verticalText"):
            # The label remains hidden outside scene 02, but must contain real
            # text because the validator rejects unresolved placeholders even
            # for invisible elements.
            scene["verticalText"]["text"] = TEST_VERTICAL_LABEL if scene["verticalText"].get("visible") else "تجربة"
        for word in scene.get("wordEvents", []):
            word_id = word["id"]
            text = TEST_WORDS.get(word_id)
            if not text:
                raise RuntimeError(f"No smoke-test text configured for {word_id}")
            word["text"] = text
            if word.get("kashida", {}).get("enabled"):
                # Keep the literal Arabic text readable; use a single deliberate
                # kashida on longer display words as a typography smoke test.
                display = text
                if word_id in {"word-001", "word-002", "word-004", "word-005", "word-007", "word-009"}:
                    display = text.replace("ا", "اـ", 1) if "ا" in text else text
                word["kashida"]["displayText"] = display
    TIMELINE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def make_speech_segments(data: dict[str, Any], temp_dir: Path, espeak: str | None, ffmpeg: str) -> list[tuple[Path, int]]:
    fps = int(data["project"]["fps"])
    segments: list[tuple[Path, int]] = []
    speech_mode = "Arabic TTS" if espeak else "synthetic tone fallback"
    for scene in data["scenes"]:
        for word in scene.get("wordEvents", []):
            text = TEST_WORDS[word["id"]]
            path = temp_dir / f"{word['id']}.wav"
            spoken = False
            if espeak:
                result = subprocess.run([espeak, "-v", "ar", "-s", "142", "-a", "170", "-w", str(path), text],
                                        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                spoken = result.returncode == 0 and path.exists() and path.stat().st_size > 1000
                if not spoken:
                    path.unlink(missing_ok=True)
            if not spoken:
                # CI remains deterministic even if an eSpeak installation omits
                # Arabic voice data: use a short, voiced carrier as an audio path
                # smoke test and report it clearly (not represented as speech).
                tone = 185 + (sum(ord(ch) for ch in text) % 150)
                run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                     f"sine=frequency={tone}:sample_rate=48000:duration=0.38", "-af",
                     "tremolo=f=5:d=0.55,afade=t=in:st=0:d=0.025,afade=t=out:st=0.24:d=0.14,volume=0.55",
                     "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(path)])
                speech_mode = "synthetic tone fallback"
            segments.append((path, int(word["startFrame"])))
    print(f"Narration generator mode: {speech_mode}")
    return segments


def create_narration(data: dict[str, Any], ffmpeg: str, espeak: str | None, destination: Path) -> None:
    duration = float(data["project"]["durationSeconds"])
    fps = int(data["project"]["fps"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="akv-test-audio-") as temp_name:
        temp_dir = Path(temp_name)
        segments = make_speech_segments(data, temp_dir, espeak, ffmpeg)
        command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                   "-f", "lavfi", "-t", f"{duration:.3f}", "-i",
                   "anullsrc=channel_layout=stereo:sample_rate=48000"]
        for path, _ in segments:
            command.extend(["-i", str(path)])
        filters = ["[0:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[base]"]
        labels = ["[base]"]
        for i, (_, frame) in enumerate(segments, start=1):
            delay = round(frame / fps * 1000)
            label = f"v{i}"
            filters.append(
                f"[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"volume=0.72,adelay={delay}|{delay},apad,atrim=duration={duration:.3f}[{label}]"
            )
            labels.append(f"[{label}]")
        filters.append("".join(labels) + f"amix=inputs={len(labels)}:duration=first:normalize=0,alimiter=limit=0.92[out]")
        command.extend(["-filter_complex", ";".join(filters), "-map", "[out]", "-ar", "48000", "-ac", "2",
                        "-c:a", "pcm_s16le", "-t", f"{duration:.3f}", str(destination)])
        run(command)


def create_sfx(ffmpeg: str, path: Path, kind: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if kind == "pop":
        source = "sine=frequency=880:sample_rate=48000:duration=0.13"
        filters = "afade=t=out:st=0.025:d=0.105,volume=0.75"
    else:
        source = "anoisesrc=color=white:sample_rate=48000:duration=0.42:amplitude=0.25"
        filters = "lowpass=f=1250,highpass=f=120,afade=t=in:st=0:d=0.04,afade=t=out:st=0.13:d=0.29,volume=0.48"
    run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", source,
         "-af", filters, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(path)])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Overwrite generated test assets and demo transcript")
    args = parser.parse_args()
    if not args.force:
        print("Refusing to overwrite the project timeline/assets without --force.", file=sys.stderr)
        return 2

    ffmpeg = require_binary("ffmpeg")
    espeak = shutil.which("espeak-ng") or shutil.which("espeak")
    data = update_timeline()
    for index in range(1, 5):
        draw_asset(index, ROOT / f"public/images/element-0{index}.png")
    create_sfx(ffmpeg, ROOT / "public/audio/sfx/pop.wav", "pop")
    create_sfx(ffmpeg, ROOT / "public/audio/sfx/whoosh.wav", "whoosh")
    create_narration(data, ffmpeg, espeak, ROOT / "public/audio/narration.wav")

    print("SMOKE TEST ASSETS: PASS")
    print(" - 4 transparent PNG assets: 900x1200 each")
    print(" - narration.wav: timeline-aligned smoke-test audio (Arabic TTS when voice data is available; otherwise voiced tone fallback)")
    print(" - pop.wav and whoosh.wav: generated with FFmpeg")
    print(" - timeline.json: placeholders replaced with Arabic demo text")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
