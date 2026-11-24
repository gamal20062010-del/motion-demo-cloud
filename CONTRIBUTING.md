# Contributing

Thank you for helping improve Motion Demo Cloud. The repository currently contains a working Arabic Remotion production example and an earlier Python renderer. The Remotion project remains the primary production path; changes should avoid breaking the existing abaya example while making the reusable parts easier to configure.

## Development environment

For `Arabic-Kinetic-Video-v2/`:

- Node.js 20 or newer.
- Python 3.12 or newer.
- FFmpeg and FFprobe available on `PATH`.
- Network access for Edge TTS narration generation.

The Noto Sans Arabic and Noto Naskh Arabic font files and their OFL notices are checked into the project. Do not replace them with unlicensed font files.

## Install

From the repository root:

```bash
cd Arabic-Kinetic-Video-v2
python -m pip install -r requirements.txt
npm ci
```

## Validate changes

Run these before opening a pull request:

```bash
npm test
npm run check-timeline
npx tsc --noEmit
```

The timeline checks have two layers:

- `scripts/validate_timeline_generic.py` checks the common JSON timeline structure, frame bounds, event timing, palette references, and referenced public assets.
- `scripts/validate_timeline.py` is the stricter abaya-example profile. It enforces the approved transcript, six-scene timing, visual states, and narration requirements for the current production demo.

The Python unit tests for the generic validator are under `tests/`.

## Build the current production example

```bash
python scripts/create_abaya_variants.py
python scripts/generate_narration.py --voice ar-SA-HamedNeural --rate=-6%
python scripts/generate_sfx.py
npm run check-timeline
npm run mix-audio
npm run render
npm run validate
```

Edge TTS requires network access. The generated word timing is based on Edge TTS `WordBoundary` metadata; do not describe it as forced alignment against a separate original recording.

## Rendering and generated files

The root workflow `.github/workflows/render.yml` builds from the checked-in project source and uploads the MP4, reports, and generated assets as a GitHub Actions artifact. It does not commit generated media back to the source branch.

Do not add a workflow step that pushes generated audio, video, or reports into a source branch unless there is a clearly documented reason and a separate review of that behavior.

## Preserve existing behavior

Changes to the timeline, components, or audio pipeline should preserve:

- Arabic RTL shaping and rendering.
- Word-level narration timing.
- Element and sticker motion driven by the timeline.
- Scene transition timing.
- Sound-effect synchronization and mix-level validation.
- Final MP4 resolution, frame rate, frame count, codecs, and audio checks.

When changing an existing behavior, update or add a test that demonstrates the intended behavior.

## Assets, audio, and licensing

Before contributing an image, font, recording, transcript, music track, sound effect, or other third-party asset:

1. Record its creator / upstream source and a stable source URL.
2. Record the applicable license or written permission.
3. Confirm that the license permits the intended modification and distribution.
4. Preserve required attribution and license notices.
5. Do not commit private recordings, credentials, personal information, or files that you are not authorized to share.

The optional Sheikh-audio acquisition workflow requires a manual authorization confirmation. That confirmation is not a substitute for checking the actual rights and terms for the source material.

A repository-level software license has not yet been selected. Until one is added, do not assume that the public visibility of the repository grants reuse rights to its code or bundled creative assets. See `ASSET_PROVENANCE.md` and `docs/OPEN_SOURCE_READINESS.md`.

## Pull requests

Keep pull requests focused. Include:

- What changed and why.
- Which validator or tests were run.
- Whether the change affects narration timing, the timeline format, assets, or rendering output.
- A GitHub Actions artifact or screenshots for meaningful visual changes, when available.

Do not merge a draft preparation pull request or publish a release tag until its remaining licensing and asset-audit requirements have been resolved.
