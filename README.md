# Motion Demo Cloud

Arabic-first motion-graphics experiments and automated video-rendering pipelines.

**Current status:** an active prototype / production demo, not yet a released general-purpose video framework. The repository currently contains an earlier Python renderer and a newer Remotion-based Arabic kinetic-typography project. This preparation branch documents the current system and fixes a CI serialization issue without moving or deleting existing project files.

## What is here

The current Remotion project demonstrates:

- Arabic right-to-left (RTL) kinetic typography with scene-based timelines.
- Word-level narration timing generated from Edge TTS `WordBoundary` events.
- Animated visual elements and scene transitions driven by a JSON timeline.
- Narration and synchronized Pop / Whoosh sound effects.
- Vertical 9:16 rendering at 1080 × 1920 and 30 frames per second.
- TypeScript, timeline, and rendered-video validation using Remotion, FFmpeg, and FFprobe.

The current abaya example uses six scenes and a 670-frame timeline. Those values, its transcript, and parts of its validation are example-specific; they should not be treated as universal engine limits.

## Repository map

| Path | Purpose |
| --- | --- |
| `Arabic-Kinetic-Video-v2/` | Current Remotion + React + TypeScript production demonstration. |
| `Arabic-Kinetic-Video-v2/src/data/timeline.json` | Scene, text, element, and timing data for the abaya example. |
| `Arabic-Kinetic-Video-v2/src/components/` | Reusable rendering components and timeline utilities. |
| `Arabic-Kinetic-Video-v2/scripts/` | Narration generation, image variants, SFX generation, audio mixing, and validation. |
| `Arabic-Kinetic-Video-v2/public/` | Fonts, image assets, narration, timing data, and sound effects used by the example. |
| `scripts/build_demo.py` | Earlier standalone Python-based demo renderer. |\n| `.github/workflows/fetch_istiftah_audio.yml` | Optional manual source-audio acquisition utility. It requires an explicit authorization confirmation and is not part of the video renderer. |
| `assets/` | Example scene data and instructions for supplying narration to the earlier renderer. |
| `packages/archive-parts/`, `packages/production-parts/` | Legacy Base64 snapshots retained for audit / rollback; the active render workflow no longer consumes them. |

## Run the Remotion example locally

Requirements:

- Node.js 20 or newer.
- Python 3.12 or newer.
- FFmpeg and FFprobe (the GitHub Actions workflow prepares portable binaries).
- Network access when generating Edge TTS narration. The checked-in Noto Arabic fonts are used directly.

From the repository root:

```bash
cd Arabic-Kinetic-Video-v2
python -m pip install -r requirements.txt
npm ci
python scripts/create_abaya_variants.py
python scripts/generate_narration.py --voice ar-SA-HamedNeural --rate=-6%
python scripts/generate_sfx.py
npm run check-timeline
npm run mix-audio
npm run render
npm run validate
```

The rendered video is written to `Arabic-Kinetic-Video-v2/out/final-video.mp4`. Validation reports are written under `out/`.

To open Remotion Studio instead of rendering:

```bash
npm run studio
```

## Automated rendering

The active production workflow is:

`.github/workflows/render.yml`

It runs on manual dispatch, pull requests, and selected source changes. It builds directly from the checked-in `Arabic-Kinetic-Video-v2/` directory: installs locked dependencies, verifies the checked-in Arabic fonts and master image, generates image variants, narration and word-boundary timings, generates sound effects, validates the timeline, renders the MP4, validates the result, and uploads a GitHub Actions artifact.

A separate `.github/workflows/ci.yml` runs read-only pull-request checks for timeline JSON parsing, the current example timeline validator, locked dependency installation, and TypeScript type-checking. The production workflow also runs as a full end-to-end test on pull requests.

Generated MP4/audio/report files are uploaded as artifacts; the workflow does not commit generated outputs back into the source branch. The old Base64 archives are retained for audit and rollback only and are no longer required by the active production render workflow.

## Important accuracy notes

- The current abaya demonstration uses Edge TTS voice `ar-SA-HamedNeural`; it is **not** an original recording of a human speaker or a Sheikh.
- Word-level timing is generated from Edge TTS boundary metadata. It is not a forced alignment of an unrelated recording.
- `Arabic-Kinetic-Video-v2/scripts/validate_timeline.py` currently validates the specific abaya example. A reusable engine release needs a separate general-purpose timeline validator.
- The project contains both a prior Python demo and the newer Remotion demonstration. They have not yet been consolidated into one public API or one unified command-line interface.

## Licensing and asset provenance

There is currently no repository-level `LICENSE` file. Until a license is selected and added, do not assume that the public visibility of this repository grants permission to reuse, redistribute, or modify its code or bundled creative assets.

See [ASSET_PROVENANCE.md](ASSET_PROVENANCE.md) for the recorded origin of the abaya image, derived image variants, fonts, narration, and sound effects. Third-party dependencies retain their own licenses. The optional source-audio acquisition workflow is gated by a manual authorization confirmation; source recordings and transcripts must not be redistributed without permission.

## العربية

هذا المستودع مساحة عمل لتجارب إنتاج فيديوهات الموشن جرافيك العربية آليًا. يضم حاليًا مسارين: نموذجًا برمجيًا أقدم باستخدام Python، ومشروعًا أحدث باستخدام Remotion وReact وTypeScript. يركز المشروع الأحدث على الكتابة العربية من اليمين إلى اليسار، وتحريك الكلمات وفق التوقيت اللفظي، وتحريك العناصر البصرية، ومزامنة المؤثرات الصوتية، ثم تصيير الفيديو والتحقق منه داخل GitHub Actions.

المشروع ما زال نموذجًا تطبيقيًا قيد التهيئة، وليس إطارًا عامًا مكتملًا. لا يوجد حتى الآن ملف ترخيص على مستوى المستودع؛ لذلك لا ينبغي اعتبار إتاحته للعامة إذنًا تلقائيًا بإعادة استخدام جميع الشيفرات أو الأصول. راجع ملف [مصدر الأصول](ASSET_PROVENANCE.md) وملف [جاهزية الإصدار مفتوح المصدر](docs/OPEN_SOURCE_READINESS.md).
