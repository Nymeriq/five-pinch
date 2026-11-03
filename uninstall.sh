#!/usr/bin/env bash
set -euo pipefail
if [[ $(id -u) == 0 ]]; then
    echo 'Run as your own user, without sudo.' >&2
    exit 1
fi
uuid='five-pinch@local.codex'
dest="${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/$uuid"
if [[ ! -d $dest || -L $dest ]]; then
    echo 'No manual Five Pinch installation found.'
    exit 0
fi
gnome-extensions disable "$uuid"
# Reset only our settings and Shell membership as the current user.
/usr/bin/python3 -I "$(dirname "$0")/packaging/five-pinch-reset.py"
# Remove only the known extension, preserving other extensions.
/usr/bin/python3 - "$dest" <<'PY'
import json, pathlib, shutil, sys
p = pathlib.Path(sys.argv[1])
if p.name != 'five-pinch@local.codex' or json.loads((p/'metadata.json').read_text())['uuid'] != p.name:
    raise SystemExit('Unexpected installation path')
shutil.rmtree(p)
PY
echo 'Five Pinch removed. Your Five Pinch settings were reset; other extensions were not changed. Log out and back in.'
