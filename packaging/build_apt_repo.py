#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a signed flat APT repository. Signing keys are supplied externally."""
import argparse
from email.utils import formatdate
import gzip
import hashlib
from pathlib import Path
import shutil
import subprocess


def build(packages, output, homedir, fingerprint):
    output.mkdir(parents=True, exist_ok=True)
    pool = output / 'pool'
    pool.mkdir(exist_ok=True)
    for package in packages:
        name = subprocess.check_output(['dpkg-deb', '--field', str(package), 'Package'], text=True).strip()
        if name != 'five-pinch':
            raise ValueError('This archive only publishes five-pinch packages')
        dest = pool / package.name
        if dest.exists() and dest.read_bytes() != package.read_bytes():
            raise ValueError(f'Refusing to replace immutable package {dest.name}')
        if not dest.exists():
            shutil.copyfile(package, dest)
    result = subprocess.run(['dpkg-scanpackages', '--multiversion', 'pool', '/dev/null'],
                            cwd=output, capture_output=True, check=True)
    (output / 'Packages').write_bytes(result.stdout)
    (output / 'Packages.gz').write_bytes(gzip.compress(result.stdout, mtime=0))
    release = ('Origin: Nymeriq-Five-Pinch\nLabel: Five Pinch\nSuite: stable\n'
               'Codename: five-pinch\nDate: ' + formatdate(usegmt=True) + '\n'
               'Description: Five Pinch packages for GNOME 50 on Wayland\n')
    for algorithm, title in [('sha256', 'SHA256'), ('sha512', 'SHA512')]:
        release += title + ':\n'
        for file in ['Packages', 'Packages.gz']:
            contents = (output / file).read_bytes()
            release += f' {hashlib.new(algorithm, contents).hexdigest()} {len(contents):16d} {file}\n'
    (output / 'Release').write_text(release)
    command = ['gpg', '--homedir', str(homedir), '--batch', '--yes', '--local-user', fingerprint]
    subprocess.run(command + ['--clearsign', '--output', str(output / 'InRelease'), str(output / 'Release')], check=True)
    subprocess.run(command + ['--armor', '--detach-sign', '--output', str(output / 'Release.gpg'), str(output / 'Release')], check=True)
    public = subprocess.check_output(['gpg', '--homedir', str(homedir), '--batch', '--export', fingerprint])
    if not public:
        raise ValueError('Signing public key not found')
    (output / 'five-pinch.gpg').write_bytes(public)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', action='append', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--gnupg-home', required=True, type=Path)
    parser.add_argument('--fingerprint', required=True)
    args = parser.parse_args()
    build(args.package, args.output, args.gnupg_home, args.fingerprint)
