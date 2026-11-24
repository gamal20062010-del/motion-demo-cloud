# Historical archive reconstruction

The earlier production workflow used two ordered extraction operations:

1. Extract `packages/archive-parts/` into the repository root.
2. Extract `packages/production-parts/` and copy its `production/` directory over `Arabic-Kinetic-Video-v2/`.

That packaging process has been retired from the active production render workflow. The active workflow now builds directly from the checked-in `Arabic-Kinetic-Video-v2/` source tree.

The original archives remain in the repository temporarily as historical rollback material. Their integrity and contents can be reviewed using `.github/workflows/archive-audit.yml`; do not reintroduce archive extraction into the active rendering path.
