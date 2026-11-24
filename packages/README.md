# Legacy archive snapshots

The files in `archive-parts/` and `production-parts/` are retained Base64-encoded XZ/TAR snapshots from the earlier packaging workflow. They are **not** used by the active production render workflow.

The production pipeline now checks out and builds directly from `Arabic-Kinetic-Video-v2/`. The archive files remain temporarily as historical rollback and audit material while the source tree and direct-source render are reviewed.

Use `.github/workflows/archive-audit.yml` to verify the archive chunks and compare their contents with the checked-in project. That workflow is read-only and publishes its report as an artifact.

Do not add a dependency on these snapshots to the active render workflow. Decide separately whether the legacy files should be deleted from the repository in a later cleanup change.
