OPTIONAL ORIGINAL NARRATION INPUT

Place one voice file inside this folder using one of these names:
  narration.wav
  narration.mp3
  narration.m4a

When a narration file exists, the renderer uses that exact recording as the voice track.
It does not generate a replacement voice or change the speaker's pitch. The export applies
only a light loudness/true-peak delivery adjustment.

EDITING RULES

Copy scenes.example.json to scenes.json and edit each caption's:
  start, end, caption

Visual settings:
  visual: book_quill, lantern, or river
  palette: rose, lavender, sky, cream, mint, peach, or aqua
  topic: a short description of the current spoken subject

The illustration remains on screen across consecutive captions for the same subject.
It does not enter or exit on every sentence. A short cross-fade occurs only when the
visual subject changes. There are no talking cartoon characters in this version.

Optional custom transparent PNGs can be placed in assets/cutouts using:
  book_quill.png, lantern.png, river.png
If absent, the engine draws original transparent illustrations locally.

Time values are seconds from the beginning of the narration.

PRIVACY NOTE:
The GitHub repository is public. Any narration file committed to it becomes public.
Change the repository to Private before uploading private, personal, or rights-restricted audio.
If no narration file is present, the workflow uses Edge TTS for the built-in demonstration lines.
