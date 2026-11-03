#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bounded read-only touchpad + libinput + actual extension-state recording.

No keyboard capture, grabs, injected events or settings changes. libinput here
has its OWN context, so its events are not proof of Mutter's exact event stream.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import selectors
import signal
import struct
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'reader'))
from detector import Detector
from service import Touchpad, find_device

EVENT = struct.Struct('@llHHi')


def capture(output, stop_file, seconds, shell_trace=False):
    output.mkdir(parents=True, exist_ok=False)
    os.chmod(output, 0o700)
    pad = Touchpad(find_device())
    selector = selectors.DefaultSelector()
    children = []
    stop = False
    frames = 0
    profiles = {p: Detector(p) for p in ('original', 'balanced', 'relaxed')}
    ready = False
    pending = b''
    trace_settings = None
    trace_previous = None
    buffers = {}
    started = time.monotonic()
    log_path = output / 'events.jsonl'
    log = log_path.open('x', buffering=1)
    os.chmod(log_path, 0o600)

    def write(source, **fields):
        log.write(json.dumps({'source': source, 'observed_us': time.monotonic_ns() // 1000,
                              **fields}, ensure_ascii=False) + '\n')

    def request_stop(*_args):
        nonlocal stop
        stop = True

    def launch(name, command):
        child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        os.set_blocking(child.stdout.fileno(), False)
        children.append((name, child))
        buffers[name] = b''
        selector.register(child.stdout, selectors.EVENT_READ, name)
        write('process-start', name=name, command=command)

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, request_stop)
    try:
        write('metadata', utc=datetime.now(timezone.utc).isoformat(), device=pad.path,
              name=pad.name, identity=pad.identity, slots=pad.slot,
              x_axis=pad.x, y_axis=pad.y, coordinate_mode=pad.coordinate_mode,
              stop_file=str(stop_file), maximum_seconds=seconds,
              note='libinput-debug is a separate context, not the compositor stream; settings-watch is actual extension state.')
        for name, command in [
                ('initial-settings', ['dconf', 'dump', '/org/gnome/shell/extensions/five-pinch/']),
                ('extension-info', ['gnome-extensions', 'info', 'five-pinch@local.codex']),
                ('libinput-version', ['libinput', '--version'])]:
            result = subprocess.run(command, capture_output=True, text=True, timeout=8)
            write(name, text=result.stdout, error=result.stderr, returncode=result.returncode)
        launch('settings-watch', ['stdbuf', '-oL', '-eL', 'dconf', 'watch',
                                 '/org/gnome/shell/extensions/five-pinch/'])
        launch('libinput-debug', ['stdbuf', '-oL', '-eL', 'libinput', 'debug-events',
                                 '--device', pad.path, '--verbose'])
        if shell_trace:
            from gi.repository import Gio
            schema_dir = '/usr/share/gnome-shell/extensions/five-pinch@local.codex/schemas'
            source = Gio.SettingsSchemaSource.new_from_directory(schema_dir,
                Gio.SettingsSchemaSource.get_default(), False)
            schema = source.lookup('org.gnome.shell.extensions.five-pinch', False)
            if not schema or not schema.has_key('diagnostic-logging'):
                raise RuntimeError('Shell trace requires the 0.6.4 diagnostic build and logout/login first.')
            launch('shell-trace', ['journalctl', '--user', '-f', '-n', '0', '-o', 'cat',
                                  '--grep=FIVE_PINCH_TRACE'])
            trace_settings = Gio.Settings.new_full(schema, None, None)
            trace_previous = trace_settings.get_user_value('diagnostic-logging')
            trace_settings.set_boolean('diagnostic-logging', True)
            Gio.Settings.sync()
            write('shell-trace-enabled', previous=None if trace_previous is None else trace_previous.unpack())
        selector.register(pad.fd, selectors.EVENT_READ, 'raw-touchpad')
        print(f'RECORDING: {log_path.resolve()}', flush=True)
        print('Reproduce the pinch-out -> unwanted swipe. Stop with Ctrl+C, or:', flush=True)
        print(f'touch {stop_file}', flush=True)
        print(f'Automatic stop after {seconds:g} seconds. Only the selected touchpad is read.', flush=True)
        while not stop and not stop_file.exists() and time.monotonic() - started < seconds:
            for key, _ in selector.select(.1):
                name = key.data
                fd = key.fileobj if isinstance(key.fileobj, int) else key.fileobj.fileno()
                data = os.read(fd, EVENT.size * 256 if name == 'raw-touchpad' else 65536)
                if not data:
                    selector.unregister(key.fileobj)
                    write('stream-closed', name=name)
                    if name in ('raw-touchpad', 'libinput-debug', 'settings-watch'):
                        raise RuntimeError(f'Required diagnostic stream closed: {name}')
                    continue
                if name != 'raw-touchpad':
                    buffers[name] += data
                    while b'\n' in buffers[name]:
                        line, buffers[name] = buffers[name].split(b'\n', 1)
                        write(name, text=line.decode(errors='replace'))
                    continue
                pending += data
                while len(pending) >= EVENT.size:
                    sec, usec, kind, code, value = EVENT.unpack_from(pending)
                    pending = pending[EVENT.size:]
                    if kind == 0 and code == 3:
                        write('data-loss', reason='SYN_DROPPED')
                        raise RuntimeError('SYN_DROPPED; capture is incomplete')
                    if kind == 3:
                        pad.state.abs(code, value)
                    elif kind == 1 and code in (272, 273, 274):
                        if value:
                            pad.buttons.add(code)
                        else:
                            pad.buttons.discard(code)
                    elif kind == 0 and code == 0:
                        points = pad.state.points()
                        event_us = sec * 1000000 + usec
                        write('raw-frame', event_us=event_us, points=points,
                              contacts=None if points is None else len(points), clicked=bool(pad.buttons))
                        frames += 1
                        if points is None:
                            ready = False
                            for d in profiles.values():
                                d.clear()
                            continue
                        if not ready:
                            ready = not points and not pad.buttons
                            continue
                        for profile, detector in profiles.items():
                            result = detector.frame(event_us / 1e6, points, bool(pad.buttons))
                            if result:
                                write('offline-candidate', profile=profile, event_us=event_us, candidate=result)
        write('summary', frames=frames, elapsed_s=round(time.monotonic() - started, 3),
              stop_reason='signal' if stop else 'stop-file' if stop_file.exists() else 'time-limit')
    except Exception as exc:
        write('error', message=str(exc))
        raise
    finally:
        if trace_settings is not None:
            if trace_previous is None:
                trace_settings.reset('diagnostic-logging')
            else:
                trace_settings.set_value('diagnostic-logging', trace_previous)
            Gio.Settings.sync()
            write('shell-trace-restored')
        for name, child in children:
            if child.poll() is None:
                child.terminate()
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
            remainder = buffers.get(name, b'') + (child.stdout.read() or b'')
            if remainder:
                write(name, text=remainder.decode(errors='replace'), final=True)
            child.stdout.close()
        selector.close()
        pad.close()
        log.close()
        print(f'RECORDING STOPPED: {log_path.resolve()} ({frames} frames)', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--stop-file', required=True, type=Path)
    parser.add_argument('--seconds', type=float, default=600)
    parser.add_argument('--shell-trace', action='store_true', help='Opt in to detailed Shell trace; requires diagnostic build 0.6.4')
    args = parser.parse_args()
    if not 0 < args.seconds <= 600:
        parser.error('duration must be between 0 and 600 seconds')
    capture(args.output, args.stop_file, args.seconds, args.shell_trace)
