#!/usr/bin/env python3
"""Strict validator for the six-scene 670-frame abaya production timeline."""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = re.compile(r"\{\{[^{}]+\}\}")
EXPECTED_SCENES = [
    ('scene-01-intro', 0, 105),
    ('scene-02-decoration', 120, 204),
    ('scene-03-simple', 210, 294),
    ('scene-04-qualities', 300, 474),
    ('scene-05-transparency', 480, 555),
    ('scene-06-closing', 570, 670),
]
EXPECTED_TEXT = 'العباءة إنما جعلت للستر ولم تجعل للزينة، لا يكون فيها زركشة ولا فيها تطريز، وإنما تكون سادة لا تلفت النظر، وتكون أيضاً ضافية، تكون ساترة وتكون فضفاضة وواسعة، ليست عباءة شفافة واسمها عباءة وهي لا تستر، هذا تلاعب.'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeline', default='src/data/timeline.json')
    args = parser.parse_args()
    path = (ROOT / args.timeline).resolve()
    data: dict[str, Any] = json.loads(path.read_text(encoding='utf-8'))
    project = data['project']
    fps, total = int(project['fps']), int(project['durationFrames'])
    errors: list[str] = []

    if (int(project['width']), int(project['height'])) != (1080, 1920): errors.append('Expected 1080x1920 portrait dimensions')
    if fps != 30: errors.append('Expected 30 FPS')
    if total != 670: errors.append(f'Expected exactly 670 frames, found {total}')
    if abs(float(project['durationSeconds']) - total/fps) > 1e-6: errors.append('durationSeconds must equal durationFrames / FPS')
    if data.get('narrationText') != EXPECTED_TEXT: errors.append('Narration text does not exactly match the approved transcript')
    if project.get('palette') != {'background':'#FADAD8','primaryText':'#171717','secondaryText':'#171717','accent':'#C94F76','sticker':'#C94F76','onElementText':'#FFFFFF'}:
        errors.append('Palette does not match the approved background/text/accent/white values')
    if project.get('watermark', {}).get('enabled') is not False: errors.append('Watermark must remain disabled')

    scenes = data.get('scenes', [])
    if len(scenes) != len(EXPECTED_SCENES): errors.append(f'Expected six scenes, found {len(scenes)}')
    palette = project.get('palette', {})

    def check_color(value: Any, location: str) -> None:
        if isinstance(value, str) and value.startswith('$palette.'):
            key = value[len('$palette.'):]
            if key not in palette: errors.append(f'Unknown palette token at {location}: {value}')

    def check_text(value: Any, location: str) -> None:
        if isinstance(value, str) and PLACEHOLDER.search(value): errors.append(f'Placeholder remains at {location}')

    visible_vertical = []
    previous_end = 0
    for index, (scene, expected) in enumerate(zip(scenes, EXPECTED_SCENES)):
        scene_id, expected_start, expected_end = expected
        start, end = int(scene['startFrame']), int(scene['endFrame'])
        if scene.get('id') != scene_id or (start, end) != (expected_start, expected_end):
            errors.append(f'Scene {index+1} range/id mismatch: got {scene.get("id")} [{start},{end}), expected {scene_id} [{expected_start},{expected_end})')
        if start < previous_end: errors.append(f'Scene {scene_id} overlaps the preceding scene')
        if not (0 <= start < end <= total): errors.append(f'Scene {scene_id} has invalid range')
        previous_end = end
        if not isinstance(scene.get('stickerEvents'), list): errors.append(f'{scene_id} must contain stickerEvents array')
        check_color(scene.get('background'), f'{scene_id}.background')
        vertical = scene.get('verticalText', {})
        if vertical.get('visible'):
            visible_vertical.append(scene_id)
            check_text(vertical.get('text'), f'{scene_id}.verticalText.text')
        if scene_id == 'scene-03-simple' and (not vertical.get('visible') or vertical.get('color') != '$palette.onElementText'):
            errors.append('The vertical white text must appear in scene 3 only')
        if scene_id != 'scene-03-simple' and vertical.get('visible'):
            errors.append(f'Vertical text must be hidden in {scene_id}')

        element = scene.get('mainElement', {})
        for src in [element.get('src')] + [e.get('src') for e in element.get('imageEvents', [])]:
            if not src: continue
            asset_path = ROOT / 'public' / src.lstrip('/')
            if not asset_path.is_file(): errors.append(f'Missing image asset: public/{src}')
        for image_event in element.get('imageEvents', []):
            if not (start <= int(image_event['startFrame']) < end): errors.append(f'Image swap outside scene in {scene_id}: {image_event.get("id")}')

        for word in scene.get('wordEvents', []):
            check_text(word.get('text'), f'{scene_id}.{word.get("id")}.text')
            check_color(word.get('color'), f'{scene_id}.{word.get("id")}.color')
            ws, we = int(word['startFrame']), int(word['endFrame'])
            if not (start <= ws < end): errors.append(f'Word {word.get("id")} starts outside its scene')
            if we <= ws or we > end: errors.append(f'Word {word.get("id")} has invalid endFrame')
            if not word.get('maxWidth') or word.get('textAlign') not in ('left','center','right'):
                errors.append(f'Word {word.get("id")} must define maxWidth and textAlign')

        for sticker in scene.get('stickerEvents', []):
            check_color(sticker.get('color'), f'{scene_id}.{sticker.get("id")}.color')
            if sticker.get('entry', {}).get('type') != 'spring-pop': errors.append(f'Sticker {sticker.get("id")} must use spring-pop')
            ss, se = int(sticker['startFrame']), int(sticker['endFrame'])
            if not (start <= ss < end) or se <= ss or se > end: errors.append(f'Sticker {sticker.get("id")} has invalid frame range')
        for event in scene.get('sfxEvents', []):
            if not (start <= int(event['atFrame']) < end): errors.append(f'SFX {event.get("id")} starts outside its scene')
            if not (0.15 <= float(event.get('volume', 0)) <= 0.25): errors.append(f'SFX {event.get("id")} gain must be 15%-25%')

    if visible_vertical != ['scene-03-simple']:
        errors.append(f'Vertical text must be visible in scene 3 only; found {visible_vertical}')
    if scenes and scenes[-1]['mainElement'].get('opacity', {}).get('keyframes', [])[-1:]:
        last_opacity = scenes[-1]['mainElement']['opacity']['keyframes'][-1]['value']
        if abs(float(last_opacity) - 0.40) > 1e-8: errors.append('Scene 6 final opacity must hold at 0.40')
    else:
        errors.append('Scene 6 must define opacity keyframes ending at 0.40')

    required_assets = [
        'public/images/element-01.png','public/images/element-02.png','public/images/element-03.png','public/images/element-04.png',
        'public/audio/narration.wav','public/audio/sfx/pop.wav','public/audio/sfx/whoosh.wav',
        'public/fonts/NotoSansArabic/NotoSansArabic[wdth,wght].ttf',
        'public/fonts/NotoNaskhArabic/NotoNaskhArabic[wght].ttf',
    ]
    for rel in required_assets:
        if not (ROOT / rel).is_file(): errors.append(f'Required asset missing: {rel}')

    timings = data.get('wordTimings', [])
    if not timings: errors.append('No WordBoundary word-level timings found; run generate_narration.py first')
    else:
        last = -1
        for item in timings:
            start_frame, end_frame = int(item['startFrame']), int(item['endFrame'])
            if not item.get('text'): errors.append('Empty text in word timing record')
            if start_frame < last: errors.append('Word timings are not monotonically ordered')
            if not (0 <= start_frame < end_frame <= total): errors.append(f'Word timing out of bounds: {item}')
            last = start_frame

    if errors:
        print('TIMELINE VALIDATION: FAIL', file=sys.stderr)
        for error in errors: print(f' - {error}', file=sys.stderr)
        return 1
    print(f'TIMELINE VALIDATION: PASS — 6 scenes, 670 frames at 30 FPS, {len(timings)} Edge TTS word timings, 4 image states.')
    return 0

if __name__ == '__main__':
    try: raise SystemExit(main())
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
