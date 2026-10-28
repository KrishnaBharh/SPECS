#!/usr/bin/env python3
"""Feather Player: a small terminal music player for Linux.

Uses Python's standard library, yt-dlp for YouTube search, and mpv for playback.
No Python packages are required.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

APP_NAME = "Feather Player"
APP_VERSION = "1.1.0"
CONFIG_DIR = Path.home() / ".config" / "feather-player"
LIBRARY_FILE = CONFIG_DIR / "library.json"
MAX_HISTORY = 50
SEARCH_RESULTS = 10


def format_duration(seconds: Any) -> str:
    """Convert a duration in seconds to M:SS or H:MM:SS."""
    if not isinstance(seconds, (int, float)) or seconds < 0:
        return "LIVE/unknown"
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def normalize_song(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Convert yt-dlp search JSON into the small shape Feather stores."""
    video_id = entry.get("id")
    url = entry.get("webpage_url") or entry.get("original_url")
    if not url and video_id:
        url = f"https://www.youtube.com/watch?v={video_id}"
    if not url:
        return None

    title = str(entry.get("title") or "Untitled")
    duration = entry.get("duration")
    if not isinstance(duration, (int, float)):
        duration = None
    uploader = entry.get("uploader") or entry.get("channel") or "Unknown artist/channel"
    return {
        "title": title,
        "url": str(url),
        "duration": duration,
        "uploader": str(uploader),
    }


def valid_http_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class FeatherPlayer:
    def __init__(self) -> None:
        self.library = self._load_library()
        self.queue: list[dict[str, Any]] = []

    @staticmethod
    def _empty_library() -> dict[str, list[dict[str, Any]]]:
        return {"favorites": [], "history": []}

    def _load_library(self) -> dict[str, list[dict[str, Any]]]:
        try:
            if LIBRARY_FILE.exists():
                data = json.loads(LIBRARY_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return {
                        "favorites": data.get("favorites", []) if isinstance(data.get("favorites", []), list) else [],
                        "history": data.get("history", []) if isinstance(data.get("history", []), list) else [],
                    }
        except (OSError, json.JSONDecodeError):
            print(f"Warning: couldn't read your library at {LIBRARY_FILE}. Starting with an empty one.")
        return self._empty_library()

    def _save_library(self) -> None:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            temp_file = LIBRARY_FILE.with_suffix(".json.tmp")
            temp_file.write_text(json.dumps(self.library, indent=2, ensure_ascii=False), encoding="utf-8")
            temp_file.replace(LIBRARY_FILE)
        except OSError as exc:
            print(f"Couldn't save your library: {exc}")

    @staticmethod
    def _dependency(command: str, purpose: str) -> bool:
        if shutil.which(command):
            return True
        print(f"Missing dependency: {command} ({purpose}).")
        print("On Linux Mint, try: sudo apt update && sudo apt install mpv yt-dlp")
        print("If the yt-dlp package is too old, install a newer version with pipx.")
        return False

    @staticmethod
    def _line() -> None:
        print("─" * 54)

    @staticmethod
    def _song_label(song: dict[str, Any], number: int | None = None) -> str:
        duration = format_duration(song.get("duration"))
        title = str(song.get("title", "Untitled")).replace("\n", " ")
        uploader = str(song.get("uploader", "Unknown artist/channel")).replace("\n", " ")
        prefix = f"{number:>2}. " if number is not None else "    "
        return f"{prefix}{title[:64]}  [{duration}]\n    {uploader[:62]}"

    def _search_youtube(self, query: str) -> list[dict[str, Any]]:
        if not self._dependency("yt-dlp", "YouTube search"):
            return []
        command = [
            "yt-dlp", "--flat-playlist", "--dump-json", "--no-warnings",
            "--ignore-errors", f"ytsearch{SEARCH_RESULTS}:{query}",
        ]
        print("Searching YouTube…")
        try:
            result = subprocess.run(command, text=True, capture_output=True, timeout=60, check=False)
        except subprocess.TimeoutExpired:
            print("Search timed out. Try a shorter query or check your connection.")
            return []
        except OSError as exc:
            print(f"Couldn't start yt-dlp: {exc}")
            return []

        songs: list[dict[str, Any]] = []
        for line in result.stdout.splitlines():
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            song = normalize_song(raw)
            if song:
                songs.append(song)

        if not songs:
            detail = result.stderr.strip().splitlines()
            print("No results found.")
            if detail:
                print(f"yt-dlp: {detail[-1][:240]}")
                print("If YouTube changed, update yt-dlp and try again.")
        return songs

    @staticmethod
    def _parse_selection(value: str, maximum: int) -> list[int]:
        """Parse a 1-based selection such as '2' or '1,3,4'."""
        picked: list[int] = []
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            if not part.isdigit():
                return []
            index = int(part)
            if not 1 <= index <= maximum:
                return []
            if index - 1 not in picked:
                picked.append(index - 1)
        return picked

    @staticmethod
    def _fzf_pick(songs: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
        """Open an interactive fzf picker; return None when fzf cannot be used."""
        fzf = shutil.which("fzf")
        if not fzf or not songs:
            return None

        # Keep a stable numeric ID as the first hidden field. The visible fields
        # are title, duration, and channel; the ID maps selections back to songs.
        rows: list[str] = []
        for index, song in enumerate(songs, start=1):
            title = str(song.get("title", "Untitled"))
            uploader = str(song.get("uploader", "Unknown artist/channel"))
            title = " ".join(title.replace("\t", " ").replace("\r", " ").replace("\n", " ").split())
            uploader = " ".join(uploader.replace("\t", " ").replace("\r", " ").replace("\n", " ").split())
            duration = format_duration(song.get("duration"))
            rows.append(f"{index}\t{title}\t{duration}\t{uploader}")

        command = [
            fzf,
            "--multi",
            "--height=80%",
            "--layout=reverse",
            "--border=rounded",
            "--prompt=🎧 Tracks > ",
            "--header=Type to filter  •  TAB select multiple  •  ENTER confirm  •  ESC back",
            r"--delimiter=\t",
            "--with-nth=2..4",
            "--nth=2,4",
            "--cycle",
            "--info=inline",
            "--bind=ctrl-a:select-all,ctrl-d:deselect-all",
        ]
        try:
            result = subprocess.run(
                command,
                input="\n".join(rows) + "\n",
                text=True,
                capture_output=True,
                check=False,
            )
        except OSError:
            return None

        # fzf returns 1 for no match and 130 when cancelled with Esc/Ctrl-C.
        if result.returncode in {1, 130}:
            return []
        if result.returncode != 0:
            return None

        chosen: list[dict[str, Any]] = []
        for line in result.stdout.splitlines():
            try:
                index = int(line.split("\t", 1)[0]) - 1
            except (ValueError, IndexError):
                continue
            if 0 <= index < len(songs) and songs[index] not in chosen:
                chosen.append(songs[index])
        return chosen

    def _choose_song(self, songs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not songs:
            return []

        # Prefer the keyboard-driven fuzzy picker. Fall back to the numbered
        # interface on systems without fzf, or if fzf itself fails to launch.
        selected = self._fzf_pick(songs)
        if selected is not None:
            return selected

        print("\nfzf isn't available, so using the basic numbered list instead.")
        self._line()
        for i, song in enumerate(songs, start=1):
            print(self._song_label(song, i))
        self._line()
        answer = input("Choose track number(s), or b to go back: ").strip().lower()
        if answer in {"b", "back", "q", ""}:
            return []
        indexes = self._parse_selection(answer, len(songs))
        if not indexes:
            print("That selection doesn't match the list.")
            return []
        return [songs[i] for i in indexes]

    def _add_to_history(self, songs: list[dict[str, Any]]) -> None:
        # Keep newest first and avoid a pile of identical consecutive entries.
        for song in reversed(songs):
            self.library["history"] = [item for item in self.library["history"] if item.get("url") != song.get("url")]
            self.library["history"].insert(0, song.copy())
        self.library["history"] = self.library["history"][:MAX_HISTORY]
        self._save_library()

    def _add_favorites(self, songs: list[dict[str, Any]]) -> None:
        added = 0
        favorite_urls = {item.get("url") for item in self.library["favorites"]}
        for song in songs:
            if song.get("url") not in favorite_urls:
                self.library["favorites"].append(song.copy())
                favorite_urls.add(song.get("url"))
                added += 1
        self._save_library()
        print(f"Saved {added} favorite{'s' if added != 1 else ''}.")

    def _remove_favorite(self, song: dict[str, Any]) -> None:
        self.library["favorites"] = [item for item in self.library["favorites"] if item.get("url") != song.get("url")]
        self._save_library()
        print("Removed from favorites.")

    def _add_queue(self, songs: list[dict[str, Any]]) -> None:
        self.queue.extend(song.copy() for song in songs)
        print(f"Added {len(songs)} track(s). Queue: {len(self.queue)} track(s).")

    def _play(self, songs: list[dict[str, Any]], from_queue: bool = False) -> None:
        if not songs:
            print("Nothing to play.")
            return
        if not self._dependency("mpv", "audio playback"):
            return
        urls = [str(song.get("url", "")) for song in songs if valid_http_url(str(song.get("url", "")))]
        if not urls:
            print("No valid playback URLs in this selection.")
            return
        print("\nStarting playback. Use mpv's keyboard controls while it plays; press q in mpv to stop.\n")
        command = [
            "mpv", "--no-video", "--title=Feather Player",
            "--ytdl-format=bestaudio/best", "--term-osd=auto", *urls,
        ]
        try:
            self._add_to_history(songs)
            result = subprocess.run(command, check=False)
            if result.returncode not in (0, 1):
                print(f"mpv exited with code {result.returncode}. Check the URL and your mpv/yt-dlp versions.")
        except OSError as exc:
            print(f"Couldn't start mpv: {exc}")
        if from_queue:
            # The queue is consumed after launching its playlist.
            self.queue.clear()

    def search_menu(self) -> None:
        query = input("Search YouTube: ").strip()
        if not query:
            return
        songs = self._search_youtube(query)
        selected = self._choose_song(songs)
        if not selected:
            return
        self._song_actions(selected)

    def direct_url_menu(self) -> None:
        url = input("Paste a direct audio/video URL: ").strip()
        if not valid_http_url(url):
            print("Please enter a valid http:// or https:// URL.")
            return
        host = urlparse(url).netloc
        song = {"title": f"Direct link ({host})", "url": url, "duration": None, "uploader": host}
        self._song_actions([song])

    def _song_actions(self, songs: list[dict[str, Any]]) -> None:
        print("\n" + ", ".join(song.get("title", "Untitled")[:42] for song in songs))
        print("[p] Play now   [a] Add to queue   [f] Favorite   [b] Back")
        action = input("Action: ").strip().lower()
        if action == "p":
            self._play(songs)
        elif action == "a":
            self._add_queue(songs)
        elif action == "f":
            self._add_favorites(songs)
        elif action not in {"b", "", "q"}:
            print("Unknown action.")

    def queue_menu(self) -> None:
        while True:
            print(f"\nQueue ({len(self.queue)} track(s))")
            self._line()
            if not self.queue:
                print("Your queue is empty.")
                return
            for i, song in enumerate(self.queue, start=1):
                print(self._song_label(song, i))
            self._line()
            print("[p] Play queue   [r] Remove track   [c] Clear queue   [b] Back")
            action = input("Action: ").strip().lower()
            if action == "p":
                self._play(self.queue.copy(), from_queue=True)
                return
            if action == "r":
                value = input("Track number to remove: ").strip()
                indexes = self._parse_selection(value, len(self.queue))
                if indexes:
                    for index in sorted(indexes, reverse=True):
                        del self.queue[index]
                    print("Removed.")
                else:
                    print("Invalid track number.")
            elif action == "c":
                self.queue.clear()
                print("Queue cleared.")
                return
            elif action in {"b", "", "q"}:
                return
            else:
                print("Unknown action.")

    def _saved_list_menu(self, kind: str) -> None:
        while True:
            songs = self.library.get(kind, [])
            heading = "Favorites" if kind == "favorites" else "Recent history"
            print(f"\n{heading} ({len(songs)} track(s))")
            self._line()
            if not songs:
                print("Nothing saved here yet.")
                return
            for i, song in enumerate(songs, start=1):
                print(self._song_label(song, i))
            self._line()
            choices = "[number] Select   [c] Clear history" if kind == "history" else "[number] Select   [c] Clear favorites"
            print(choices + "   [b] Back")
            value = input("Choice: ").strip().lower()
            if value in {"b", "", "q"}:
                return
            if value == "c":
                confirm = input(f"Clear all {heading.lower()}? Type y to confirm: ").strip().lower()
                if confirm == "y":
                    self.library[kind] = []
                    self._save_library()
                continue
            selected = self._parse_selection(value, len(songs))
            if not selected:
                print("Invalid selection.")
                continue
            chosen = [songs[index] for index in selected]
            if kind == "favorites":
                print("[p] Play   [a] Add to queue   [r] Remove favorite   [b] Back")
                action = input("Action: ").strip().lower()
                if action == "p":
                    self._play(chosen)
                elif action == "a":
                    self._add_queue(chosen)
                elif action == "r":
                    for song in chosen:
                        self._remove_favorite(song)
            else:
                self._song_actions(chosen)

    def diagnose(self) -> None:
        print(f"{APP_NAME} {APP_VERSION}")
        print(f"Python: {sys.version.split()[0]}")
        print(f"mpv: {'found' if shutil.which('mpv') else 'MISSING'}")
        print(f"yt-dlp: {'found' if shutil.which('yt-dlp') else 'MISSING'}")
        print(f"Library: {LIBRARY_FILE}")
        print(f"Favorites: {len(self.library['favorites'])} | History: {len(self.library['history'])}")

    def run(self) -> None:
        while True:
            print("\nSPECS")
            print("─" * 54)
            print(" 1. Search YouTube")
            print(" 2. Play a URL")
            print(f" 3. Queue ({len(self.queue)})")
            print(f" 4. Favorites ({len(self.library['favorites'])})")
            print(f" 5. Recent history ({len(self.library['history'])})")
            print(" 6. Diagnostics")
            print(" 0. Exit")
            try:
                choice = input("\nfeather > ").strip().lower()
            except EOFError:
                print()
                return
            if choice == "1":
                self.search_menu()
            elif choice == "2":
                self.direct_url_menu()
            elif choice == "3":
                self.queue_menu()
            elif choice == "4":
                self._saved_list_menu("favorites")
            elif choice == "5":
                self._saved_list_menu("history")
            elif choice == "6":
                self.diagnose()
            elif choice in {"0", "q", "quit", "exit"}:
                print("Feather Player closing. Keep your ears happy.")
                return
            else:
                print("Choose one of the menu numbers.")


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {"--version", "-v"}:
        print(f"{APP_NAME} {APP_VERSION}")
        return 0
    if len(sys.argv) > 1 and sys.argv[1] in {"--help", "-h"}:
        print("Usage: feather-player [--help | --version]\n\nRun with no arguments to open the interactive player.")
        return 0
    try:
        FeatherPlayer().run()
        return 0
    except KeyboardInterrupt:
        print("\nFeather Player closed.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
