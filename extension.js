// SPDX-License-Identifier: MIT
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Clutter from 'gi://Clutter';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import {validCandidate} from './protocol.js';

export default class FivePinch extends Extension {
    enable() {
        this._alive = true;
        this._settings = this.getSettings();
        this._cancel = new Gio.Cancellable();
        this._session = null;
        this._sleeping = false;
        this._pauseUntil = 0;
        this._retryAt = 0;
        this._lastAction = 0;
        this._lastTick = GLib.get_monotonic_time();
        this._serial = 0;
        this._run = null;
        this._settingsSignal = this._settings.connect('changed', (_s, key) => {
            if (['enabled', 'pinch-in', 'pinch-out', 'device-path', 'sensitivity'].includes(key)) {
                this._stop();
                this._retryAt = 0;
                this._tick();
            }
        });
        this._modeSignal = Main.sessionMode.connect('updated', () => this._tick());
        // Observe key events only to pause recognition. Never record keys or stop propagation.
        this._keySignal = global.stage.connect('captured-event', (_stage, event) => {
            if (event.type() === Clutter.EventType.KEY_PRESS) {
                this._pauseUntil = GLib.get_monotonic_time() + 900000;
                this._stop();
            }
            return Clutter.EVENT_PROPAGATE;
        });
        this._sleepSignal = Gio.DBus.system.signal_subscribe(
            'org.freedesktop.login1', 'org.freedesktop.login1.Manager',
            'PrepareForSleep', '/org/freedesktop/login1', null,
            Gio.DBusSignalFlags.NONE, (_c, _s, _p, _i, _m, parameters) => {
                this._sleeping = parameters.deep_unpack()[0];
                this._stop();
                this._pauseUntil = GLib.get_monotonic_time() + 1000000;
                this._tick();
            });
        this._timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 250, () => {
            this._tick();
            return GLib.SOURCE_CONTINUE;
        });
        this._status('Checking session…');
        this._initSession();
    }

    _initSession() {
        const token = this._cancel;
        Gio.DBus.system.call('org.freedesktop.login1', '/org/freedesktop/login1',
            'org.freedesktop.login1.Manager', 'GetSession',
            new GLib.Variant('(s)', ['auto']), new GLib.VariantType('(o)'),
            Gio.DBusCallFlags.NONE, 3000, token, (connection, result) => {
                try {
                    const [path] = connection.call_finish(result).deep_unpack();
                    if (!this._alive || token !== this._cancel)
                        return;
                    Gio.DBusProxy.new_for_bus(Gio.BusType.SYSTEM,
                        Gio.DBusProxyFlags.NONE, null, 'org.freedesktop.login1',
                        path, 'org.freedesktop.login1.Session', token, (_source, res) => {
                            try {
                                const proxy = Gio.DBusProxy.new_for_bus_finish(res);
                                if (!this._alive || token !== this._cancel)
                                    return;
                                this._session = proxy;
                                this._sessionSignal = proxy.connect('g-properties-changed', () => this._tick());
                                this._ownerSignal = proxy.connect('notify::g-name-owner', () => this._tick());
                                this._tick();
                            } catch (e) {
                                if (this._alive && token === this._cancel)
                                    this._status(`Cannot verify session: ${e.message}`);
                            }
                        });
                } catch (e) {
                    if (this._alive && token === this._cancel)
                        this._status(`Cannot verify session: ${e.message}`);
                }
            });
    }

    _permitted() {
        return this._alive && this._settings.get_boolean('enabled') &&
            !Main.sessionMode.isLocked && !Main.sessionMode.isGreeter &&
            Main.sessionMode.hasOverview && !this._sleeping &&
            Boolean(this._session?.g_name_owner) &&
            this._session.get_cached_property('Active')?.deep_unpack() === true &&
            this._session.get_cached_property('LockedHint')?.deep_unpack() === false;
    }

    _tick() {
        if (!this._alive)
            return;
        const now = GLib.get_monotonic_time();
        if (now - this._lastTick > 1500000) {
            this._stop(); // No stale event after suspend or a stalled Shell.
            this._pauseUntil = now + 1000000;
        }
        this._lastTick = now;
        if (!this._permitted()) {
            this._stop();
            if (!this._settings.get_boolean('enabled'))
                this._status('Disabled.');
            else if (this._session)
                this._status('Paused: session locked or inactive.');
            return;
        }
        if (now < this._pauseUntil) {
            this._stop();
            this._status('Paused; lift all fingers.');
            return;
        }
        if (!this._run && now >= this._retryAt)
            this._start();
        if (this._run)
            this._pulse(this._run);
    }

    _start() {
        this._retryAt = GLib.get_monotonic_time() + 5000000;
        try {
            const process = Gio.Subprocess.new(
                ['/usr/bin/python3', '-I', `${this.path}/reader/service.py`,
                    '--sensitivity', this._settings.get_string('sensitivity'),
                    ...(this._settings.get_string('device-path') ? ['--device', this._settings.get_string('device-path')] : [])],
                Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_PIPE);
            const run = {process, input: process.get_stdin_pipe(),
                output: new Gio.DataInputStream({base_stream: process.get_stdout_pipe()}),
                cancel: new Gio.Cancellable(), writing: false, sequence: 0};
            this._run = run;
            this._status('Starting recognizer…');
            process.wait_async(null, (child, result) => {
                try { child.wait_finish(result); } catch (_) { /* already reaped */ }
                if (this._run === run) {
                    this._stop();
                    this._status('Recognizer stopped; retrying within 5 seconds.');
                    this._retryAt = GLib.get_monotonic_time() + 5000000;
                }
            });
            this._read(run);
        } catch (e) {
            this._status(`Cannot start: ${e.message}`);
        }
    }

    _pulse(run) {
        if (run.writing)
            return;
        run.writing = true;
        run.input.write_all_async(new TextEncoder().encode('run\n'),
            GLib.PRIORITY_DEFAULT, run.cancel, (stream, result) => {
                try { stream.write_all_finish(result); } catch (_) {
                    if (this._run === run)
                        this._stop();
                }
                run.writing = false;
            });
    }

    _read(run) {
        run.output.read_line_async(GLib.PRIORITY_DEFAULT, run.cancel, (stream, result) => {
            try {
                const [line] = stream.read_line_finish_utf8(result);
                if (this._run !== run)
                    return;
                if (line === null)
                    return; // wait_async reports termination.
                if (line.length > 1024)
                    throw new Error('Invalid reader message');
                this._message(run, JSON.parse(line));
                if (this._run === run)
                    this._read(run);
            } catch (e) {
                if (this._run === run) {
                    this._stop();
                    this._status(`Recognizer error: ${e.message}`);
                }
            }
        });
    }

    _message(run, message) {
        if (message.type === 'status') {
            this._status(String(message.message).slice(0, 240));
            return;
        }
        const now = GLib.get_monotonic_time();
        if (!validCandidate(message, now, run.sequence))
            return;
        run.sequence = message.sequence;
        if (!this._permitted() || now < this._pauseUntil || now - this._lastAction < 450000)
            return;
        this._lastAction = now;
        const action = this._settings.get_string(`pinch-${message.direction}`);
        this._settings.set_string('last-event',
            `${++this._serial}. ${message.direction === 'in' ? 'Pinch in' : 'Pinch out'} · ${action}`);
        switch (action) {
        case 'apps': Main.overview.showApps(); break;
        case 'apps-close':
            // Close the app grid to the desktop, but leave a window overview alone.
            if (Main.overview.dash?.showAppsButton?.checked)
                Main.overview.hide();
            break;
        case 'overview': Main.overview.show(); break;
        case 'hide': Main.overview.hide(); break;
        // disabled/diagnostic never perform a Shell action.
        }
    }

    _status(message) {
        if (this._settings && this._settings.get_string('status') !== message)
            this._settings.set_string('status', message);
    }

    _stop() {
        const run = this._run;
        this._run = null;
        if (run) {
            run.cancel.cancel();
            run.process.force_exit();
            run.input.close_async(GLib.PRIORITY_DEFAULT, null, (stream, result) => {
                try { stream.close_finish(result); } catch (_) { /* exited */ }
            });
            run.output.close_async(GLib.PRIORITY_DEFAULT, null, (stream, result) => {
                try { stream.close_finish(result); } catch (_) { /* exited */ }
            });
        }
    }

    disable() {
        this._alive = false;
        this._stop();
        this._cancel?.cancel();
        if (this._timer) GLib.source_remove(this._timer);
        if (this._sleepSignal) Gio.DBus.system.signal_unsubscribe(this._sleepSignal);
        if (this._modeSignal) Main.sessionMode.disconnect(this._modeSignal);
        if (this._keySignal) global.stage.disconnect(this._keySignal);
        if (this._sessionSignal) this._session.disconnect(this._sessionSignal);
        if (this._ownerSignal) this._session.disconnect(this._ownerSignal);
        if (this._settingsSignal) this._settings.disconnect(this._settingsSignal);
        this._status('Extension stopped.');
        this._settings = null;
        this._session = null;
        this._cancel = null;
        this._timer = this._sleepSignal = this._modeSignal = this._keySignal = 0;
        this._sessionSignal = this._ownerSignal = this._settingsSignal = 0;
    }
}
