OPTIONAL ORIGINAL NARRATION INPUT

Place one voice file inside this folder using one of these names:
  narration.wav
  narration.mp3
  narration.m4a

When a narration file exists, the renderer uses that exact recording as the voice track.
It does not generate a replacement voice or change the speaker's pitch. The export applies
only a light loudness/true-peak delivery adjustment.

For custom caption timing, copy scenes.example.json to scenes.json and edit each scene's:
  start, end, caption, visual, palette, side

Allowed visual values: book_quill, lantern, river
Allowed palette values: rose, lavender, sky, cream, mint, peach, aqua
Time values are in seconds from the beginning of the narration.

Optional custom transparent PNGs can be placed in assets/cutouts using the names:
  book_quill.png, lantern.png, river.png
When these PNGs are absent, the engine draws original transparent vector illustrations locally.

PRIVACY NOTE:
The current GitHub repository is public. Any narration file committed to it becomes public.
Change the repository to Private before uploading private, personal, or rights-restricted audio.
If no narration file is present, the workflow uses Edge TTS for the built-in demonstration lines.
