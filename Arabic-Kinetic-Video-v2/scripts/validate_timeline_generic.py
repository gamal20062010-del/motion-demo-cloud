#!/usr/bin/env python3
"""Generic structural validator for Remotion JSON video timelines.

This validator deliberately avoids example-specific assumptions such as scene
count, transcript wording, exact dimensions, or a fixed color palette.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PALETTE_TOKEN = re.compile(r"^\$palette\.([A-Za-z0-9_-]+)$")
PLACEHOLDER = re.compile(r"\{\{[^{}]*\}\}")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _frame(value: Any, location: str, errors: list[str]) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool):
        errors.append(f"{location} must be an integer frame number")
        return None
    return value


def _check_public_asset(
    project_root: Path,
    relative_path: Any,
    location: str,
    errors: list[str],
) -> None:
    if not isinstance(relative_path, str) or not relative_path.strip():
        errors.append(f"{location} must contain a non-empty public asset path")
        return

    public_root = (project_root / "public").resolve()
    candidate = (public_root / relative_path.lstrip("/\\")).resolve()

    if not candidate.is_relative_to(public_root):
        errors.append(f"{location} escapes the public/ asset directory: {relative_path}")
    elif not candidate.is_file():
        errors.append(f"Missing asset at {location}: public/{relative_path.lstrip('/\\')}")


def _validate_palette_tokens(value: Any, palette: dict[str, Any], location: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            _validate_palette_tokens(child, palette, f"{location}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_palette_tokens(child, palette, f"{location}[{index}]", errors)
    elif isinstance(value, str):
        token = PALETTE_TOKEN.fullmatch(value)
        if token and token.group(1) not in palette:
            errors.append(f"Unknown palette token at {location}: {value}")
        if PLACEHOLDER.search(value):
            errors.append(f"Unresolved template placeholder at {location}")


def validate_timeline(data: Any, project_root: Path) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    counts = {"scenes": 0, "word_events": 0, "sticker_events": 0, "sfx_events": 0, "word_timings": 0}

    if not isinstance(data, dict):
        return ["Timeline root must be a JSON object"], counts

    project = data.get("project")
    if not isinstance(project, dict):
        return ["project must be a JSON object"], counts

    width, height = project.get("width"), project.get("height")
    fps, total_frames = project.get("fps"), project.get("durationFrames")
    if not isinstance(width, int) or isinstance(width, bool) or width <= 0:
        errors.append("project.width must be a positive integer")
    if not isinstance(height, int) or isinstance(height, bool) or height <= 0:
        errors.append("project.height must be a positive integer")
    if not _is_number(fps) or fps <= 0:
        errors.append("project.fps must be a positive number")
    if not isinstance(total_frames, int) or isinstance(total_frames, bool) or total_frames <= 0:
        errors.append("project.durationFrames must be a positive integer")

    if _is_number(fps) and fps > 0 and isinstance(total_frames, int) and not isinstance(total_frames, bool):
        duration = project.get("durationSeconds")
        expected_duration = total_frames / fps
        if not _is_number(duration) or abs(duration - expected_duration) > (1 / fps) + 1e-6:
            errors.append("project.durationSeconds must match durationFrames / fps within one frame")

    palette = project.get("palette", {})
    if not isinstance(palette, dict):
        errors.append("project.palette must be an object when supplied")
        palette = {}

    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes must be a non-empty array")
        scenes = []

    counts["scenes"] = len(scenes)
    seen_scene_ids: set[str] = set()
    previous_start = -1
    previous_end = 0

    for index, scene in enumerate(scenes):
        location = f"scenes[{index}]"
        if not isinstance(scene, dict):
            errors.append(f"{location} must be an object")
            continue

        scene_id = scene.get("id")
        if not isinstance(scene_id, str) or not scene_id.strip():
            errors.append(f"{location}.id must be a non-empty string")
            scene_id = f"index-{index}"
        elif scene_id in seen_scene_ids:
            errors.append(f"Duplicate scene id: {scene_id}")
        seen_scene_ids.add(scene_id)

        start = _frame(scene.get("startFrame"), f"{location}.startFrame", errors)
        end = _frame(scene.get("endFrame"), f"{location}.endFrame", errors)
        if start is None or end is None:
            continue
        if start < 0 or end <= start:
            errors.append(f"{scene_id} has an invalid frame interval [{start}, {end})")
        if isinstance(total_frames, int) and not isinstance(total_frames, bool) and end > total_frames:
            errors.append(f"{scene_id} ends after project.durationFrames")
        if start < previous_start:
            errors.append(f"Scenes are not ordered by startFrame at {scene_id}")
        if start < previous_end:
            errors.append(f"{scene_id} overlaps the preceding scene")
        previous_start, previous_end = start, max(previous_end, end)

        element = scene.get("mainElement")
        if not isinstance(element, dict):
            errors.append(f"{scene_id}.mainElement must be an object")
            element = {}
        _check_public_asset(project_root, element.get("src"), f"{scene_id}.mainElement.src", errors)

        element_size = element.get("size")
        if not isinstance(element_size, dict):
            errors.append(f"{scene_id}.mainElement.size must be an object")
        else:
            for dimension in ("width", "height"):
                value = element_size.get(dimension)
                if not _is_number(value) or value <= 0:
                    errors.append(f"{scene_id}.mainElement.size.{dimension} must be positive")

        image_events = element.get("imageEvents", [])
        if not isinstance(image_events, list):
            errors.append(f"{scene_id}.mainElement.imageEvents must be an array")
            image_events = []
        for event_index, event in enumerate(image_events):
            event_location = f"{scene_id}.mainElement.imageEvents[{event_index}]"
            if not isinstance(event, dict):
                errors.append(f"{event_location} must be an object")
                continue
            frame = _frame(event.get("startFrame"), f"{event_location}.startFrame", errors)
            if frame is not None and not (start <= frame < end):
                errors.append(f"{event_location}.startFrame must be inside its scene")
            _check_public_asset(project_root, event.get("src"), f"{event_location}.src", errors)

        for collection_name, count_name in (("wordEvents", "word_events"), ("stickerEvents", "sticker_events")):
            events = scene.get(collection_name, [])
            if not isinstance(events, list):
                errors.append(f"{scene_id}.{collection_name} must be an array")
                continue
            counts[count_name] += len(events)
            for event_index, event in enumerate(events):
                event_location = f"{scene_id}.{collection_name}[{event_index}]"
                if not isinstance(event, dict):
                    errors.append(f"{event_location} must be an object")
                    continue
                event_id = event.get("id")
                if not isinstance(event_id, str) or not event_id.strip():
                    errors.append(f"{event_location}.id must be a non-empty string")
                if collection_name == "wordEvents":
                    if not isinstance(event.get("text"), str) or not event["text"].strip():
                        errors.append(f"{event_location}.text must be a non-empty string")
                event_start = _frame(event.get("startFrame"), f"{event_location}.startFrame", errors)
                event_end = _frame(event.get("endFrame"), f"{event_location}.endFrame", errors)
                if event_start is not None and not (start <= event_start < end):
                    errors.append(f"{event_location}.startFrame must be inside its scene")
                if event_end is not None and not (start < event_end <= end):
                    errors.append(f"{event_location}.endFrame must be inside or at the end of its scene")
                if event_start is not None and event_end is not None and event_end <= event_start:
                    errors.append(f"{event_location} has an empty or reversed frame interval")

        sfx_events = scene.get("sfxEvents", [])
        if not isinstance(sfx_events, list):
            errors.append(f"{scene_id}.sfxEvents must be an array")
            sfx_events = []
        counts["sfx_events"] += len(sfx_events)
        sfx_assets = data.get("assets", {}).get("sfx", {}) if isinstance(data.get("assets"), dict) else {}
        for event_index, event in enumerate(sfx_events):
            event_location = f"{scene_id}.sfxEvents[{event_index}]"
            if not isinstance(event, dict):
                errors.append(f"{event_location} must be an object")
                continue
            at_frame = _frame(event.get("atFrame"), f"{event_location}.atFrame", errors)
            if at_frame is not None and not (start <= at_frame < end):
                errors.append(f"{event_location}.atFrame must be inside its scene")
            source = event.get("src")
            if not source and isinstance(sfx_assets, dict):
                source = sfx_assets.get(event.get("name"))
            if source:
                _check_public_asset(project_root, source, f"{event_location}.src", errors)
            else:
                errors.append(f"{event_location} has no resolvable sound-effect asset")
            volume = event.get("volume", 1.0)
            if not _is_number(volume) or not (0 <= volume <= 1):
                errors.append(f"{event_location}.volume must be between 0 and 1")

    _validate_palette_tokens(data, palette, "timeline", errors)

    audio = data.get("audio", {})
    if audio is not None and not isinstance(audio, dict):
        errors.append("audio must be an object when supplied")
        audio = {}
    if isinstance(audio, dict):
        narration = audio.get("narration")
        if narration is not None:
            if not isinstance(narration, dict):
                errors.append("audio.narration must be an object")
            else:
                source = narration.get("src")
                if source:
                    _check_public_asset(project_root, source, "audio.narration.src", errors)
                if isinstance(total_frames, int) and not isinstance(total_frames, bool):
                    for key in ("startFrame", "endFrame"):
                        if key in narration:
                            frame = _frame(narration[key], f"audio.narration.{key}", errors)
                            if frame is not None and not (0 <= frame <= total_frames):
                                errors.append(f"audio.narration.{key} is outside the project")
                volume = narration.get("volume", 1.0)
                if not _is_number(volume) or not (0 <= volume <= 1):
                    errors.append("audio.narration.volume must be between 0 and 1")

    assets = data.get("assets", {})
    if assets is not None and not isinstance(assets, dict):
        errors.append("assets must be an object when supplied")
        assets = {}
    if isinstance(assets, dict):
        main_frames = assets.get("mainElementFrames", [])
        if main_frames is not None:
            if not isinstance(main_frames, list):
                errors.append("assets.mainElementFrames must be an array")
            else:
                for asset_index, source in enumerate(main_frames):
                    _check_public_asset(project_root, source, f"assets.mainElementFrames[{asset_index}]", errors)

    timings = data.get("wordTimings", [])
    if timings is not None:
        if not isinstance(timings, list):
            errors.append("wordTimings must be an array")
        else:
            counts["word_timings"] = len(timings)
            previous_word_start = -1
            for index, item in enumerate(timings):
                location = f"wordTimings[{index}]"
                if not isinstance(item, dict):
                    errors.append(f"{location} must be an object")
                    continue
                if not isinstance(item.get("text"), str) or not item["text"].strip():
                    errors.append(f"{location}.text must be a non-empty string")
                word_start = _frame(item.get("startFrame"), f"{location}.startFrame", errors)
                word_end = _frame(item.get("endFrame"), f"{location}.endFrame", errors)
                if word_start is not None:
                    if word_start < previous_word_start:
                        errors.append("wordTimings must be ordered by startFrame")
                    previous_word_start = word_start
                    if word_start < 0 or (isinstance(total_frames, int) and word_start >= total_frames):
                        errors.append(f"{location}.startFrame is outside the project")
                if word_end is not None and isinstance(total_frames, int) and (word_end <= 0 or word_end > total_frames):
                    errors.append(f"{location}.endFrame is outside the project")
                if word_start is not None and word_end is not None and word_end <= word_start:
                    errors.append(f"{location} has an empty or reversed frame interval")

    return errors, counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", default="src/data/timeline.json")
    args = parser.parse_args()

    timeline_path = (ROOT / args.timeline).resolve()
    if not timeline_path.is_file():
        print(f"Timeline file not found: {timeline_path}", file=sys.stderr)
        return 2

    try:
        data = json.loads(timeline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read valid timeline JSON: {exc}", file=sys.stderr)
        return 2

    errors, counts = validate_timeline(data, ROOT)
    if errors:
        print("GENERIC TIMELINE VALIDATION: FAIL", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1

    project = data["project"]
    print(
        "GENERIC TIMELINE VALIDATION: PASS — "
        f"{counts['scenes']} scenes, {project['width']}x{project['height']} at {project['fps']} FPS, "
        f"{counts['word_events']} word events, {counts['sticker_events']} stickers, "
        f"{counts['sfx_events']} SFX cues, {counts['word_timings']} word timings."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
