# Archive audit status

The first two-tree audit confirmed both XZ/TAR archives are readable and their Base64 chunks reconstruct successfully.

Preliminary comparisons against the checked-in `Arabic-Kinetic-Video-v2/` directory:

- Base archive: 43 tar entries; 17 files byte-identical to current files, 10 changed, and 23 current files absent from the archive.
- Production overlay: 25 tar entries / 16 files; 13 byte-identical, 3 changed, and 34 current files absent from the overlay.
- The overlay's changed files are `README.md`, `public/audio/narration.txt`, and `src/data/timeline.json`.

These independent comparisons do not by themselves establish which files the production render ultimately uses. The render workflow extracts the base archive first and applies the production overlay second. The archive audit is being extended to simulate that exact sequence before a source-of-truth decision is made.
