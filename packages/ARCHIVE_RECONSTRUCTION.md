# Effective reconstruction comparison

The production workflow performs two ordered operations:

1. Extract `archive-parts/` into the repository root.
2. Extract `production-parts/` and copy its `production/` directory over `Arabic-Kinetic-Video-v2/`.

The order matters because files in the base archive can overwrite newer tracked files before the production overlay is applied. The archive audit therefore compares not only each archive independently, but also a temporary simulation of this exact two-stage reconstruction against the checked-in project.

This file documents the comparison method. Do not replace the production workflow with direct checked-in sources until the simulated result has been reviewed and a direct-source render has passed.
