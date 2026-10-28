import importlib.util
import unittest
from unittest.mock import patch
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "main.py"
spec = importlib.util.spec_from_file_location("feather_player_main", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class TestHelpers(unittest.TestCase):
    def test_format_duration(self):
        self.assertEqual(module.format_duration(0), "0:00")
        self.assertEqual(module.format_duration(207), "3:27")
        self.assertEqual(module.format_duration(3661), "1:01:01")
        self.assertEqual(module.format_duration(None), "LIVE/unknown")

    def test_normalize_song(self):
        song = module.normalize_song({"id": "abc123", "title": "Song", "duration": 123, "channel": "Artist"})
        self.assertEqual(song["url"], "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(song["title"], "Song")
        self.assertEqual(song["duration"], 123)
        self.assertEqual(song["uploader"], "Artist")

    def test_normalize_skips_missing_url_and_id(self):
        self.assertIsNone(module.normalize_song({"title": "No usable URL"}))

    def test_valid_http_url(self):
        self.assertTrue(module.valid_http_url("https://youtube.com/watch?v=abc"))
        self.assertTrue(module.valid_http_url("http://example.com/audio.mp3"))
        self.assertFalse(module.valid_http_url("not a url"))
        self.assertFalse(module.valid_http_url("file:///tmp/song.mp3"))

    def test_parse_selection(self):
        self.assertEqual(module.FeatherPlayer._parse_selection("1,3,3", 4), [0, 2])
        self.assertEqual(module.FeatherPlayer._parse_selection("2", 4), [1])
        self.assertEqual(module.FeatherPlayer._parse_selection("0", 4), [])
        self.assertEqual(module.FeatherPlayer._parse_selection("a", 4), [])
        self.assertEqual(module.FeatherPlayer._parse_selection("5", 4), [])

    def test_fzf_picker_maps_selected_lines_back_to_songs(self):
        songs = [
            {"title": "Blue", "url": "https://example.com/1", "duration": 200, "uploader": "Artist One"},
            {"title": "Green", "url": "https://example.com/2", "duration": 180, "uploader": "Artist Two"},
        ]
        completed = module.subprocess.CompletedProcess(
            args=["fzf"], returncode=0,
            stdout="2\tGreen\t3:00\tArtist Two\n", stderr="",
        )
        with patch.object(module.shutil, "which", return_value="/usr/bin/fzf"), \
             patch.object(module.subprocess, "run", return_value=completed) as run:
            selected = module.FeatherPlayer._fzf_pick(songs)

        self.assertEqual(selected, [songs[1]])
        self.assertIn("--multi", run.call_args.args[0])
        self.assertIn("Blue", run.call_args.kwargs["input"])

    def test_fzf_picker_falls_back_when_fzf_is_missing(self):
        with patch.object(module.shutil, "which", return_value=None):
            self.assertIsNone(module.FeatherPlayer._fzf_pick([{"title": "Blue"}]))


if __name__ == "__main__":
    unittest.main()
