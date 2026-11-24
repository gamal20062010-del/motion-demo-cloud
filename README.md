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
| `scripts/build_demo.py` | Earlier standalone Python-based demo renderer. |
| `assets/` | Example scene data and instructions for supplying narration to the earlier renderer. |
| `packages/archive-parts/`, `packages/production-parts/` | Transitional Base64 archive chunks currently consumed by the production workflow. These are a packaging workaround, not the intended long-term source layout. |

## Run the Remotion example locally

Requirements:

- Node.js 20 or newer.
- Python 3.12 or newer.
- FFmpeg and FFprobe (the GitHub Actions workflow prepares portable binaries).
- Network access when generating Edge TTS narration or downloading fonts.

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

It runs on manual dispatch and on selected changes to the production branch. It reconstructs the current project from the transitional archive chunks, installs dependencies, generates narration and word timings, produces visual variants and sound effects, validates the timeline, renders the MP4, validates the result, and uploads a GitHub Actions artifact.

The generated artifact is the intended way to retrieve the final video from a workflow run. The current workflow also commits generated outputs back to its source branch; separating generated media from source control remains an open cleanup item. The archive reconstruction and duplicate workflow arrangement are also scheduled for simplification.

## Important accuracy notes

- The current abaya demonstration uses Edge TTS voice `ar-SA-HamedNeural`; it is **not** an original recording of a human speaker or a Sheikh.
- Word-level timing is generated from Edge TTS boundary metadata. It is not a forced alignment of an unrelated recording.
- `Arabic-Kinetic-Video-v2/scripts/validate_timeline.py` currently validates the specific abaya example. A reusable engine release needs a separate general-purpose timeline validator.
- The project contains both a prior Python demo and the newer Remotion demonstration. They have not yet been consolidated into one public API or one unified command-line interface.

## Licensing and asset provenance

There is currently no repository-level `LICENSE` file. Until a license is selected and added, do not assume that the public visibility of this repository grants permission to reuse, redistribute, or modify its code or bundled creative assets.

See [ASSET_PROVENANCE.md](ASSET_PROVENANCE.md) for the recorded origin of the abaya image, derived image variants, fonts, narration, and sound effects. Third-party dependencies retain their own licenses.

## العربية

هذا المستودع مساحة عمل لتجارب إنتاج فيديوهات الموشن جرافيك العربية آليًا. يضم حاليًا مسارين: نموذجًا برمجيًا أقدم باستخدام Python، ومشروعًا أحدث باستخدام Remotion وReact وTypeScript. يركز المشروع الأحدث على الكتابة العربية من اليمين إلى اليسار، وتحريك الكلمات وفق التوقيت اللفظي، وتحريك العناصر البصرية، ومزامنة المؤثرات الصوتية، ثم تصيير الفيديو والتحقق منه داخل GitHub Actions.

المشروع ما زال نموذجًا تطبيقيًا قيد التهيئة، وليس إطارًا عامًا مكتملًا. لا يوجد حتى الآن ملف ترخيص على مستوى المستودع؛ لذلك لا ينبغي اعتبار إتاحته للعامة إذنًا تلقائيًا بإعادة استخدام جميع الشيفرات أو الأصول. راجع ملف [مصدر الأصول](ASSET_PROVENANCE.md) وملف [جاهزية الإصدار مفتوح المصدر](docs/OPEN_SOURCE_READINESS.md).
