#!/usr/bin/env bash
set -euo pipefail
rm -f "$HOME/.local/bin/SPECS"
rm -rf "$HOME/.local/share/SPECS"
printf 'SPECS Player app files removed. Your library in ~/.config/SPECS was kept.\n'
printf 'To remove that library too, delete ~/.config/SPECS yourself.\n'
