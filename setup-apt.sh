#!/bin/sh
set -eu
if [ "$(id -u)" -ne 0 ]; then
    echo 'Run this setup script with sudo.' >&2
    exit 1
fi
for tool in curl gpg; do
    command -v "$tool" >/dev/null || { echo "Install $tool first." >&2; exit 1; }
done
base='https://nymeriq.github.io/five-pinch/apt'
expected='6E0C17BEEF0203BA1A0DBB9D91F383A58F9B9F97'
temp=$(mktemp -d)
trap 'rm -rf "$temp"' EXIT HUP INT TERM
mkdir -m 700 "$temp/gnupg"
curl --fail --silent --show-error --location "$base/five-pinch.gpg" -o "$temp/five-pinch.gpg"
actual=$(gpg --homedir "$temp/gnupg" --batch --with-colons --show-keys "$temp/five-pinch.gpg" 2>/dev/null | awk -F: '$1=="fpr" {print $10; exit}')
if [ "$actual" != "$expected" ]; then
    echo 'Repository signing-key fingerprint mismatch. Nothing installed.' >&2
    exit 1
fi
install -d -m 755 /etc/apt/keyrings /etc/apt/sources.list.d /etc/apt/preferences.d
install -m 644 "$temp/five-pinch.gpg" /etc/apt/keyrings/five-pinch.gpg
cat > /etc/apt/sources.list.d/five-pinch.sources <<'SOURCE'
Types: deb
URIs: https://nymeriq.github.io/five-pinch/apt
Suites: ./
Signed-By: /etc/apt/keyrings/five-pinch.gpg
SOURCE
cat > /etc/apt/preferences.d/five-pinch <<'PIN'
Package: five-pinch
Pin: release o=Nymeriq-Five-Pinch
Pin-Priority: 500

Package: *
Pin: release o=Nymeriq-Five-Pinch
Pin-Priority: -1
PIN
echo 'Five Pinch repository configured. Run: sudo apt update && sudo apt install five-pinch'
