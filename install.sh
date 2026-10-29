#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${HOME}/.local/share/SPECS"
BIN_DIR="${HOME}/.local/bin"

mkdir -p "$APP_DIR" "$BIN_DIR"
install -m 755 "$SOURCE_DIR/main.py" "$APP_DIR/main.py"
cat > "$BIN_DIR/SPECS" <<EOF
#!/usr/bin/env bash
exec python3 "${APP_DIR}/main.py" "\$@"
EOF
chmod 755 "$BIN_DIR/SPECS"

printf '\nSPECS Player installed.\n'
printf '1) Install playback/search tools: sudo apt update && sudo apt install mpv yt-dlp fzf\n'
printf '2) Install fzf for keyboard-driven fuzzy song selection (optional but recommended).\n'
printf '3) Ensure ~/.local/bin is in PATH. If needed, restart your terminal.\n'
printf '4) Run: SPECS\n'
printf '\nYour favorites and history will be stored in ~/.config/SPECS/library.json\n'
