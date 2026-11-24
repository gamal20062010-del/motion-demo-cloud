from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from validate_timeline_generic import validate_timeline


class GenericTimelineValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp.name)
        (self.project_root / "public" / "images").mkdir(parents=True)
        (self.project_root / "public" / "audio").mkdir(parents=True)
        (self.project_root / "public" / "images" / "main.png").write_bytes(b"image")
        (self.project_root / "public" / "audio" / "narration.wav").write_bytes(b"audio")
        (self.project_root / "public" / "audio" / "pop.wav").write_bytes(b"sfx")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_timeline(self) -> dict:
        return {
            "project": {
                "name": "generic-example",
                "width": 720,
                "height": 1280,
                "fps": 25,
                "durationFrames": 50,
                "durationSeconds": 2.0,
                "palette": {"background": "#ffffff", "accent": "#ff0000"},
            },
            "audio": {"narration": {"src": "audio/narration.wav", "volume": 1.0}},
            "assets": {"sfx": {"pop": "audio/pop.wav"}},
            "scenes": [
                {
                    "id": "opening",
                    "startFrame": 0,
                    "endFrame": 25,
                    "mainElement": {
                        "src": "images/main.png",
                        "size": {"width": 300, "height": 500},
                        "position": {"x": 360, "y": 640},
                        "imageEvents": [
                            {"id": "swap", "startFrame": 20, "src": "images/main.png"}
                        ],
                    },
                    "wordEvents": [
                        {
                            "id": "title",
                            "text": "مرحبا",
                            "startFrame": 1,
                            "endFrame": 15,
                        }
                    ],
                    "stickerEvents": [
                        {
                            "id": "spark",
                            "startFrame": 12,
                            "endFrame": 20,
                            "type": "emoji",
                        }
                    ],
                    "sfxEvents": [
                        {
                            "id": "pop-at-open",
                            "name": "pop",
                            "atFrame": 2,
                            "volume": 0.2,
                        }
                    ],
                },
                {
                    "id": "closing",
                    "startFrame": 25,
                    "endFrame": 50,
                    "mainElement": {
                        "src": "images/main.png",
                        "size": {"width": 300, "height": 500},
                        "position": {"x": 360, "y": 640},
                    },
                },
            ],
            "wordTimings": [
                {"index": 1, "text": "مرحبا", "startFrame": 1, "endFrame": 15}
            ],
        }

    def test_accepts_generic_timeline_with_non_abaya_specs(self) -> None:
        timeline = self.make_timeline()
        errors, counts = validate_timeline(timeline, self.project_root)
        self.assertEqual(errors, [])
        self.assertEqual(counts["scenes"], 2)
        self.assertEqual(counts["word_events"], 1)
        self.assertEqual(counts["sticker_events"], 1)
        self.assertEqual(counts["sfx_events"], 1)

    def test_rejects_overlapping_scenes(self) -> None:
        timeline = self.make_timeline()
        timeline["scenes"][1]["startFrame"] = 24
        errors, _ = validate_timeline(timeline, self.project_root)
        self.assertTrue(any("overlaps" in error for error in errors))

    def test_rejects_events_outside_their_scene(self) -> None:
        timeline = self.make_timeline()
        timeline["scenes"][0]["wordEvents"][0]["startFrame"] = 26
        errors, _ = validate_timeline(timeline, self.project_root)
        self.assertTrue(any("wordEvents[0].startFrame" in error for error in errors))

    def test_rejects_path_traversal_for_assets(self) -> None:
        timeline = self.make_timeline()
        timeline["scenes"][0]["mainElement"]["src"] = "../private.png"
        errors, _ = validate_timeline(timeline, self.project_root)
        self.assertTrue(any("escapes the public/" in error for error in errors))

    def test_rejects_unknown_palette_tokens(self) -> None:
        timeline = self.make_timeline()
        timeline["scenes"][0]["background"] = "$palette.missing"
        errors, _ = validate_timeline(timeline, self.project_root)
        self.assertTrue(any("Unknown palette token" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
