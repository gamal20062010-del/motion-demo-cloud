# Archive audit status

The Base64 chunk sets reconstruct into readable XZ/TAR archives and passed structural checks. The audit is read-only and does not alter the checked-in project.

## Independent archive comparisons

Against the checked-in `Arabic-Kinetic-Video-v2/` project:

- Base archive: 43 tar entries; 17 files byte-identical, 10 changed, 23 current files absent from the archive, and no archive-only files.
- Production overlay: 25 tar entries / 16 files; 13 files byte-identical, 3 changed, 34 current files absent from the overlay, and no archive-only files.
- The three overlay differences are `README.md`, `public/audio/narration.txt`, and `src/data/timeline.json`.

## Simulated production extraction

The audit simulates the historical workflow accurately: copy the checked-out project, overlay the base archive, then overlay the production archive. In that effective result, 47 of the 50 tracked project files remain byte-identical to the checked-in project. The only three differences are:

- `README.md`: the legacy overlay refers to `abaya-master.png`; the checked-in master image is `abaya-master.webp`.
- `public/audio/narration.txt`: rewritten by `scripts/generate_narration.py` from the approved timeline narration text.
- `src/data/timeline.json`: the overlay omits generated word timing / narration segment metadata; the narration script regenerates these fields, and the production workflow applies the explicit scene-four position/scale adjustment.

The simulation confirms that the extraction does not delete current files missing from the archives, because the workflow overlays archives onto an existing checkout rather than extracting into an empty directory.

## Direct-source render verification

The newer `.github/workflows/render-direct.yml` test ran the production pipeline from the checked-in source tree without extracting either archive. It generated the abaya image variants, Edge TTS narration and word timings, Pop/Whoosh effects, mixed audio, and final MP4. Timeline validation and final FFprobe / audio-level validation both passed.

The active `.github/workflows/render.yml` has now been switched to this direct-source process. The legacy archive chunks are retained for audit / rollback only; deleting them is a separate retention decision.
