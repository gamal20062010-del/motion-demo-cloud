# Arabic Kinetic Video v2 — Smoke Test Package

The complete Remotion project is stored as a compressed `tar.xz` archive encoded into ordered text chunks under `packages/archive-parts/part-01.b64` through `part-14.b64`. This transport avoids committing generated build output or binary files through the GitHub text-content interface.

The workflow in `../.github/workflows/render.yml` reassembles and extracts the archive, downloads the Noto Sans Arabic and Noto Naskh Arabic variable fonts from Google Fonts, installs a portable FFmpeg binary through `imageio-ffmpeg`, generates temporary geometric images/audio and a sample Arabic timeline, then runs `npm install`, TypeScript checking, Remotion rendering and FFprobe/volumedetect validation. The generated MP4 and JSON reports are published as a GitHub Actions artifact.

The generated test assets are for pipeline validation only. The smoke-test narration uses a synthetic tone audio track so the pipeline does not depend on system speech packages. Replace the sample content and generated media with approved production assets before publishing any real video.

A small smoke-test override at `packages/overrides/global.css` uses relative `public/fonts` asset URLs compatible with the Remotion Webpack bundler. The workflow applies this override after downloading the font files.
