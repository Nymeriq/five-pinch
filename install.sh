#!/usr/bin/env bash
set -euo pipefail
if [[ $(id -u) == 0 ]]; then
    echo 'Run as your own user, without sudo.' >&2
    exit 1
fi
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
uuid='five-pinch@local.codex'
if [[ ${XDG_SESSION_TYPE:-} != wayland ]]; then
    echo 'This installer requires a GNOME Wayland session.' >&2
    exit 1
fi
if ! gnome-shell --version | /usr/bin/grep -Eq 'GNOME Shell 50([. ]|$)'; then
    echo 'This release requires GNOME Shell 50.' >&2
    exit 1
fi
for tool in gnome-extensions glib-compile-schemas gsettings /usr/bin/python3; do
    command -v "$tool" >/dev/null
done
dest="${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/$uuid"
if [[ -e $dest ]]; then
    echo "Already installed: $dest. Remove the previous manual Five Pinch installation first." >&2
    exit 1
fi
# A missing/unready touchpad must not prevent installation on another machine.
if ! /usr/bin/python3 -I "$source_dir/reader/service.py" --probe; then
    echo 'Touchpad not ready yet; installation will continue. Check Settings after installation.'
fi
glib-compile-schemas --strict "$source_dir/schemas"
mkdir -p -- "$(dirname -- "$dest")"
stage=$(mktemp -d "$(dirname -- "$dest")/.five-pinch-stage.XXXXXX")
trap 'if [[ -n ${stage:-} && -d $stage ]]; then /usr/bin/python3 -c "import shutil,sys; shutil.rmtree(sys.argv[1])" "$stage"; fi' EXIT
for file in metadata.json extension.js prefs.js protocol.js pinchTailGuard.js rinertiaGuard.js LICENSE; do
    cp -- "$source_dir/$file" "$stage/$file"
done
mkdir -- "$stage/reader" "$stage/schemas"
cp -- "$source_dir/reader/service.py" "$source_dir/reader/detector.py" "$stage/reader/"
cp -- "$source_dir/schemas/"*.xml "$source_dir/schemas/gschemas.compiled" "$stage/schemas/"
mv -- "$stage" "$dest"
stage=''
gsettings --schemadir "$dest/schemas" set org.gnome.shell.extensions.five-pinch enabled false
echo 'Five Pinch installed with recognition disabled. Select actions in Settings.'
if gnome-extensions info "$uuid" >/dev/null 2>&1; then
    gnome-extensions enable "$uuid"
    gnome-extensions prefs "$uuid"
else
    echo 'Log out and back in, then enable Five Pinch in the Extensions app.'
fi
