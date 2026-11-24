# Archive audit process

The files in `archive-parts/` and `production-parts/` are compressed transport chunks consumed by the production GitHub Actions workflow. They are not source files that should be deleted merely because the same project also exists in the repository tree.

The workflow `.github/workflows/archive-audit.yml` reconstructs both archives in a temporary runner directory, validates their Base64 and XZ/TAR structure, rejects unsafe archive paths and special entries, and compares the extracted file trees with the checked-in `Arabic-Kinetic-Video-v2/` directory using SHA-256 hashes.

The audit is read-only. It publishes a Markdown and JSON report as a GitHub Actions artifact. Its purpose is to determine which archive files are identical, different, missing, or archive-only before any packaging changes are proposed.

Do not remove either archive or change the production workflow's extraction sequence until the comparison has been reviewed and a clean-render test has confirmed that the direct source tree can replace the reconstructed inputs.
