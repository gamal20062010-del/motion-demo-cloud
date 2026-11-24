#!/usr/bin/env python3
"""Generate clean short Pop/Whoosh SFX WAV assets with FFmpeg lavfi."""
from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'public' / 'audio' / 'sfx'


def main() -> int:
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise RuntimeError('ffmpeg is required to generate SFX.')
    OUT.mkdir(parents=True, exist_ok=True)
    pop = OUT / 'pop.wav'
    whoosh = OUT / 'whoosh.wav'

    # Soft, short tonal pop with a quick transient and a gentle high-frequency roll-off.
    subprocess.run([
        ffmpeg, '-y', '-hide_banner', '-loglevel', 'error',
        '-f', 'lavfi', '-i', 'sine=frequency=760:sample_rate=48000:duration=0.14',
        '-af', 'highpass=f=180,lowpass=f=6200,afade=t=in:st=0:d=0.008,afade=t=out:st=0.025:d=0.115,volume=0.78',
        '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', str(pop)
    ], check=True)

    # A restrained airy sweep; final mix gain is normalized to 20% of the narration mean level.
    subprocess.run([
        ffmpeg, '-y', '-hide_banner', '-loglevel', 'error',
        '-f', 'lavfi', '-i', 'anoisesrc=color=white:amplitude=0.32:sample_rate=48000:duration=0.42',
        '-af', 'highpass=f=520,lowpass=f=6800,afade=t=in:st=0:d=0.08,afade=t=out:st=0.18:d=0.24,volume=0.72',
        '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', str(whoosh)
    ], check=True)

    for path in (pop, whoosh):
        if not path.exists() or path.stat().st_size < 1000:
            raise RuntimeError(f'SFX was not generated correctly: {path}')
        print(f'SFX generated: {path.relative_to(ROOT)} ({path.stat().st_size} bytes)')
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
