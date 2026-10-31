# APT repository

Five Pinch has a small signed package repository hosted on GitHub Pages:

`https://nymeriq.github.io/five-pinch/apt`

APT downloads a signed catalogue during `apt update`, compares package versions,
and downloads the selected `.deb` during installation/upgrade. Adding a catalogue
does not install Five Pinch or change gesture settings by itself.

## One-time setup

Download the setup script, inspect it if desired, then run it:

```bash
curl -fL https://nymeriq.github.io/five-pinch/setup-apt.sh -o /tmp/five-pinch-apt-setup.sh
sudo sh /tmp/five-pinch-apt-setup.sh
sudo apt update
sudo apt install five-pinch
```

`curl` and `gpg` must be installed. The setup checks the public-key fingerprint
before adding a dedicated keyring, a Deb822 source file and package pinning.
It grants this repository priority for `five-pinch` only; other package names
from the archive are pinned below installation priority.

Fingerprint: `6E0C17BEEF0203BA1A0DBB9D91F383A58F9B9F97`.
The archive key is separate from GitHub login credentials and expires in 2028;
maintainers must rotate it before expiry. Only its public half is published.

## Update

```bash
sudo apt update
sudo apt install --only-upgrade five-pinch
```

Ordinary `sudo apt upgrade` also includes available Five Pinch updates.
Log out and back in after upgrading so GNOME loads the new extension code.
Existing user gesture settings are retained.

## Revert or remove

Available versions can be listed with `apt-cache policy five-pinch`.
For example, while 0.4.0 remains in the archive:

```bash
sudo apt install --allow-downgrades five-pinch=0.4.0
```

To keep that version instead of upgrading it again, use `sudo apt-mark hold
five-pinch`; undo with `sudo apt-mark unhold five-pinch`.

To remove Five Pinch, disable it in Extensions first, then run `sudo apt remove
five-pinch` and log out/back in. Removing the program does not remove the source.
To unsubscribe from updates too, remove only these repository setup files:

```bash
sudo rm /etc/apt/sources.list.d/five-pinch.sources
sudo rm /etc/apt/preferences.d/five-pinch
sudo rm /etc/apt/keyrings/five-pinch.gpg
sudo apt update
```

## Publishing a future version

The `main` branch contains source. The `gh-pages` branch contains the public
catalogue and package files; Pages publishes its root directory. A new GitHub
Release alone does **not** update the APT catalogue.

1. Build and test the new `.deb` from `main`.
2. Check out `gh-pages` separately and retain its existing `apt/pool` files.
3. Run the builder from `main`, pointing output at that checkout's `apt` folder:

```bash
python3 packaging/build_apt_repo.py \
  --package /path/to/five-pinch_NEW_all.deb \
  --output /path/to/gh-pages-checkout/apt \
  --gnupg-home /path/to/private-signing-key-directory \
  --fingerprint 6E0C17BEEF0203BA1A0DBB9D91F383A58F9B9F97
```

4. Verify the signature and a clean isolated APT update/download.
5. Commit/push the public `gh-pages` files and wait for the Pages deployment.

Never commit/export the private signing key into either branch or a release.
Back up the private signing directory separately: it is needed for future
updates. The builder rejects package names other than `five-pinch` and refuses
to overwrite an existing package filename with different bytes. If package
contents change, use a new version/filename. Old package files are retained for
rollback. The catalogue's signature and checksums protect download integrity;
the scoped key and pinning avoid treating this as a general Ubuntu archive.
