#!/usr/bin/env bash
set -euo pipefail
rm -f "$HOME/.local/bin/feather-player"
rm -rf "$HOME/.local/share/feather-player"
printf 'Feather Player app files removed. Your library in ~/.config/feather-player was kept.\n'
printf 'To remove that library too, delete ~/.config/feather-player yourself.\n'
