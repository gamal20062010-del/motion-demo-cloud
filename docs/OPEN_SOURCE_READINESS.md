# Open-source release readiness

This checklist describes the current state of the repository and the remaining work required before calling it a general-purpose open-source video engine.

## Completed in this preparation branch

- [x] Create an isolated release-preparation branch; keep `main` and `integrate/arabic-kinetic-video-v2` unchanged.
- [x] Fix the production workflow's JSON serialization terminator. The timeline writer now appends an actual line-feed character rather than the literal two-character sequence `\\n`.
- [x] Use `npm ci` in the production workflow so installation follows the checked-in lockfile.
- [x] Correct the abaya README reference from `abaya-master.png` to the actual `abaya-master.webp` file.
- [x] Add a root project overview and record the known provenance of the current creative assets.

## Required before a tagged public release

- [ ] Select and add a repository-level software license. No license has been added in this branch because the choice affects reuse rights and must be explicit.
- [ ] Audit all bundled assets and dependencies, including audio, fonts, images, npm packages, and Python packages; retain upstream notices.
- [ ] Replace the Base64 archive chunks under `packages/archive-parts/` and `packages/production-parts/` with normal, reviewable source files. The current workflow depends on these archives to reconstruct and overlay the project.
- [ ] Consolidate the production and smoke-test workflows. GitHub Actions only discovers workflows under the repository-root `.github/workflows/`; the copy under `Arabic-Kinetic-Video-v2/.github/workflows/` is nested and is not an active repository workflow in that location.
- [ ] Stop committing generated MP4/audio/report outputs to the source branch by default; publish them as workflow artifacts or release assets instead.
- [ ] Separate reusable engine code from the abaya-specific example, transcript, image assets, and fixed scene assumptions.
- [ ] Generalize timeline validation. The current validator contains assumptions about the six-scene, 670-frame abaya example.
- [ ] Add automated tests for Arabic RTL layout, word-boundary timing, timeline interpolation, scene transitions, audio offsets/mixing, and output validation.
- [ ] Add contributor guidance, support policy, and a documented configuration format for new video projects.
- [ ] Verify that a clean checkout can build the demo without relying on archive reconstruction or previously generated files.

## Design constraints to preserve

The refactor must retain the behaviors already implemented and relied on by the project:

- Arabic RTL typography and shaping.
- Word-level timing derived from narration boundary metadata.
- Animated icons / visual elements synchronized to the current spoken segment.
- Scene and element animation controlled by timeline data.
- Sound-effect timing and mixing relative to narration.
- Cloud rendering through GitHub Actions and Remotion.
- Final MP4 validation with FFprobe and audio-level checks.

Do not remove a feature merely to simplify the folder structure. First establish a test that captures the current behavior, then move or generalize the implementation.

## Release decision

This branch is a preparation step, not a release declaration. Do not publish a version tag or describe the repository as a licensed open-source project until the license and asset audit are complete and a clean-build workflow passes.
