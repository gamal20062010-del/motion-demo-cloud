#!/usr/bin/env python3
"""Validate final MP4 with FFprobe and FFmpeg volumedetect."""
from __future__ import annotations
import argparse
import json
import re
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def require_binary(name: str) -> str:
    path = shutil.which(name)
    if not path: raise RuntimeError(f'Required executable not found in PATH: {name}')
    return path


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('video', nargs='?', default='out/final-video.mp4')
    parser.add_argument('--timeline', default='src/data/timeline.json')
    parser.add_argument('--report', default='out/render-validation.json')
    args = parser.parse_args()
    ffprobe, ffmpeg = require_binary('ffprobe'), require_binary('ffmpeg')
    video = (ROOT / args.video).resolve()
    timeline = json.loads((ROOT / args.timeline).read_text(encoding='utf-8'))
    if not video.is_file(): raise FileNotFoundError(f'Rendered video not found: {video}')
    project = timeline['project']
    expected_width, expected_height = int(project['width']), int(project['height'])
    expected_fps = Fraction(int(project['fps']), 1)
    expected_duration = float(project['durationSeconds'])
    expected_frames = int(project['durationFrames'])

    probe = run([ffprobe, '-v', 'error', '-count_frames', '-show_entries',
                 'format=duration,format_name,bit_rate:stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,nb_read_frames,sample_rate,channels,channel_layout,bit_rate',
                 '-of', 'json', str(video)])
    metadata: dict[str, Any] = json.loads(probe.stdout)
    streams = metadata.get('streams', [])
    video_stream = next((s for s in streams if s.get('codec_type') == 'video'), None)
    audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), None)
    if not video_stream: raise RuntimeError('FFprobe found no video stream')
    if not audio_stream: raise RuntimeError('FFprobe found no audio stream')

    actual_fps = Fraction(video_stream.get('avg_frame_rate', video_stream.get('r_frame_rate', '0/1')))
    actual_frames = int(video_stream.get('nb_read_frames') or 0)
    actual_duration = float(metadata.get('format', {}).get('duration', 0))
    actual_width, actual_height = int(video_stream.get('width', 0)), int(video_stream.get('height', 0))
    audio_rate, audio_channels = int(audio_stream.get('sample_rate', 0)), int(audio_stream.get('channels', 0))
    video_codec, audio_codec = video_stream.get('codec_name'), audio_stream.get('codec_name')

    checks = {
        'resolution': {'expected': f'{expected_width}x{expected_height}', 'actual': f'{actual_width}x{actual_height}', 'passed': (actual_width, actual_height) == (expected_width, expected_height)},
        'fps': {'expected': str(expected_fps), 'actual': str(actual_fps), 'passed': actual_fps == expected_fps},
        'frames': {'expected': expected_frames, 'actual': actual_frames, 'passed': actual_frames == expected_frames},
        'durationSeconds': {'expected': expected_duration, 'actual': actual_duration, 'passed': abs(actual_duration - expected_duration) <= (1/float(expected_fps))+0.02},
        'videoCodec': {'expected': 'h264', 'actual': video_codec, 'passed': video_codec == 'h264'},
        'audioCodec': {'expected': 'aac', 'actual': audio_codec, 'passed': audio_codec == 'aac'},
        'audioSampleRate': {'expected': 48000, 'actual': audio_rate, 'passed': audio_rate == 48000},
        'audioChannels': {'expected': 2, 'actual': audio_channels, 'passed': audio_channels == 2},
    }

    volume_result = subprocess.run([ffmpeg, '-hide_banner', '-i', str(video), '-vn', '-af', 'volumedetect', '-f', 'null', '-'],
                                   text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    mean_match = re.search(r'mean_volume:\s*(-?inf|-?[0-9.]+)\s*dB', volume_result.stderr, re.IGNORECASE)
    max_match = re.search(r'max_volume:\s*(-?inf|-?[0-9.]+)\s*dB', volume_result.stderr, re.IGNORECASE)
    if not mean_match or not max_match: raise RuntimeError('FFmpeg volumedetect did not return mean/max volume')
    mean_volume = -120.0 if mean_match.group(1).lower() == '-inf' else float(mean_match.group(1))
    max_volume = -120.0 if max_match.group(1).lower() == '-inf' else float(max_match.group(1))
    checks['audioPeakBelowClipping'] = {'expected': '<= 0 dBFS', 'actual': max_volume, 'passed': max_volume <= 0.0}

    errors = [name for name, check in checks.items() if not check['passed']]
    report = {
        'video': str(video.relative_to(ROOT)), 'passed': not errors, 'checks': checks,
        'audioVolumedetect': {'meanVolumeDbfs': mean_volume, 'maxVolumeDbfs': max_volume},
        'errors': errors, 'ffprobe': metadata,
        'watermark': {'expected': False, 'sourceCompositionHasWatermark': False},
    }
    report_path = (ROOT / args.report).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'checks':checks,
                      'audioVolumedetect':report['audioVolumedetect'],'errors':errors},ensure_ascii=False,indent=2))
    if errors: return 1
    print(f'Validation report: {report_path}')
    return 0

if __name__ == '__main__':
    try: raise SystemExit(main())
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
