# SPECS Player

**A small terminal music player for Linux Mint and other Linux distributions.**

Feather uses Python's standard library for its menu and library, `yt-dlp` to search YouTube, and `mpv` to play audio. It does not need a browser window, Electron, a database, or Python packages.

## Features

- Search YouTube and fuzzy-filter the first 10 results with an interactive `fzf` picker (keyboard navigation and optional multi-select).
- Falls back to a numbered list if `fzf` is unavailable.
- Play a URL supported by `mpv`/`yt-dlp`.
- Build a queue and play it as an `mpv` playlist.
- Save favorites and keep the 50 most recent history entries.
- Remove queue items, remove favorites, clear lists, or replay tracks.
- Diagnostics screen and friendly missing-dependency messages.
- Local JSON library; no account or API key required.

## Requirements

- Python 3.10 or newer
- `mpv`
- `yt-dlp`
- `fzf` (recommended for the interactive fuzzy picker; optional because a numbered fallback is included)
- Internet connection for online search/playback

No third-party Python libraries are needed.

## Install on Linux Mint

Open a terminal in this folder and run:

```bash
sudo apt update
sudo apt install mpv yt-dlp fzf
./install.sh
```

Then launch it:

```bash
SPECS
```

If `SPECS: command not found` appears, ensure `~/.local/bin` is in your `PATH`, then restart the terminal. You can also run the app directly with `python3 main.py` from this folder.

### If YouTube search or playback stops working

YouTube changes its systems occasionally, and old `yt-dlp` releases can stop working. Check its version:

```bash
yt-dlp --version
```

If the version supplied by your distribution is too old, install/update `yt-dlp` using `pipx` (rather than mixing packages into system Python):

```bash
sudo apt install pipx
pipx ensurepath
pipx install yt-dlp
```

If it is already installed with pipx, update it with `pipx upgrade yt-dlp`. Restart the terminal after updating.

## Use

1. Run `SPECS`.
2. Choose **Search YouTube** and enter a search term. In the `fzf` picker, type to filter, use the arrow keys to move, press `Enter` to choose, or use `Tab` to select multiple tracks. Press `Esc` to go back.
3. Pick **Play now**, **Add to queue**, or **Favorite**.
4. Use the Queue menu to play or remove queued items.
5. While `mpv` is playing, its terminal keyboard controls are available. Press `q` in `mpv` to stop playback and return to Feather.

The exact playback controls depend on your `mpv` configuration; by default, `Space` toggles pause and `q` quits.

## Files and privacy

- App: `~/.local/share/SPECS/`
- Command: `~/.local/bin/SPECS`
- Favorites/history: `~/.config/SPECS/library.json`

Search and playback requests go to YouTube through `yt-dlp`/`mpv`. Feather does not make an account or upload your local favorites/history.

## Uninstall

From this folder, run:

```bash
./uninstall.sh
```

This removes the installed app but keeps your library file. Delete `~/.config/SPECS` yourself only if you also want to remove favorites and history.

## Troubleshooting

- Run `SPECS`, choose **Diagnostics**, and verify both tools show `found`.
- If search returns no results, try updating `yt-dlp` and checking your internet connection.
- If playback fails, test the URL directly with `mpv --no-video 'URL'`.

## Version

`1.1.0` — adds an interactive `fzf` song picker with multi-select and a numbered fallback.
