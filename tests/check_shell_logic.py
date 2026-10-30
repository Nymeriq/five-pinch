"""Run the unchanged extension logic in GJS with mock Shell UI/session objects.

This checks dispatch and cleanup, not a live GNOME Shell installation.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='five-pinch-gjs-') as name:
    target = Path(name)
    source = (root / 'extension.js').read_text()
    source = source.replace("import Clutter from 'gi://Clutter';", "const Clutter = {EventType: {KEY_PRESS: 1}, EVENT_PROPAGATE: 0};")
    source = source.replace("'resource:///org/gnome/shell/ui/main.js'", "'./main.js'")
    source = source.replace("import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';", "class Extension {}")
    (target / 'extension.js').write_text(source)
    (target / 'protocol.js').write_text((root / 'protocol.js').read_text())
    (target / 'main.js').write_text('''
export const sessionMode = {isLocked: false, isGreeter: false, hasOverview: true};
export const actions = [];
export const overview = {dash: {showAppsButton: {checked: false}}, showApps() {actions.push('apps');},
    show() {actions.push('overview');}, hide() {actions.push('hide');}};
''')
    (target / 'test.js').write_text('''
import GLib from 'gi://GLib';
import FivePinch from './extension.js';
import * as Main from './main.js';
let checks = 0;
function check(value) { checks++; if (!value) throw new Error(`Check ${checks} failed`); }
const extension = new FivePinch();
const values = {enabled: true, 'pinch-in': 'apps', 'pinch-out': 'hide'};
extension._alive = true;
extension._settings = {get_boolean(k) {return values[k];}, get_string(k) {return values[k] ?? '';},
    set_string(k, v) {values[k] = v;}};
extension._session = {g_name_owner: ':1.1', get_cached_property(k) {
    return {deep_unpack() {return k === 'Active';}};
}};
extension._sleeping = false;
extension._pauseUntil = 0;
extension._lastAction = 0;
extension._serial = 0;
const run = {sequence: 0};
const candidate = sequence => ({type: 'pinch', direction: 'in', sequence,
    monotonic_us: GLib.get_monotonic_time()});
check(extension._permitted());
extension._message(run, candidate(1));
check(Main.actions.join() === 'apps');
extension._lastAction = 0;
extension._message(run, candidate(1));
check(Main.actions.length === 1); // Replay cannot execute twice.
Main.sessionMode.isLocked = true;
extension._message(run, candidate(2));
check(Main.actions.length === 1);
Main.sessionMode.isLocked = false;
values['pinch-in'] = 'diagnostic';
extension._message(run, candidate(3));
check(Main.actions.length === 1);
values['pinch-in'] = 'disabled';
extension._lastAction = 0;
extension._message(run, candidate(4));
check(Main.actions.length === 1);
values['pinch-in'] = 'apps';
extension._sleeping = true;
extension._lastAction = 0;
extension._message(run, candidate(5));
check(Main.actions.length === 1);
extension._sleeping = false;
extension._session.g_name_owner = null;
check(!extension._permitted());
extension._session.g_name_owner = ':1.1';
values.enabled = false;
check(!extension._permitted());
values.enabled = true;
values['pinch-out'] = 'apps-close';
extension._lastAction = 0;
Main.overview.dash.showAppsButton.checked = true;
extension._message(run, {...candidate(6), direction: 'out'});
check(Main.actions.join() === 'apps,hide');
extension._lastAction = 0;
Main.overview.dash.showAppsButton.checked = false;
extension._message(run, {...candidate(7), direction: 'out'});
check(Main.actions.join() === 'apps,hide'); // Window overview is left alone.
values['pinch-out'] = 'hide';
extension._lastAction = 0;
extension._message(run, {...candidate(8), direction: 'out'});
check(Main.actions.join() === 'apps,hide,hide'); // Existing hide action still works.
let killed = 0, cancelled = 0;
const pipe = {close_async(_p, _c, callback) {callback(this, {});}, close_finish() {}};
extension._run = {cancel: {cancel() {cancelled++;}},
    process: {force_exit() {killed++;}}, input: pipe, output: pipe};
extension._stop();
extension._stop();
check(killed === 1 && cancelled === 1 && extension._run === null);
print(`${checks} Shell logic checks passed (mock UI/session)`);
''')
    subprocess.run(['gjs', '-m', str(target / 'test.js')], check=True)
