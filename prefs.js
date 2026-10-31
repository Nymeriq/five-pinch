// SPDX-License-Identifier: MIT
import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';
import Gio from 'gi://Gio';
import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class FivePinchPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        window.set_default_size(620, 600);
        const page = new Adw.PreferencesPage({title: 'Five Pinch', icon_name: 'input-touchpad-symbolic'});
        window.add(page);
        const group = new Adw.PreferencesGroup({title: 'Five-finger pinch',
            description: 'GNOME 50 / Wayland. Any touchpad may be tried; tested on MacBook Pro 2017 only. Lift all fingers between gestures.'});
        page.add(group);
        const enable = new Adw.SwitchRow({title: 'Enable recognition'});
        settings.bind('enabled', enable, 'active', Gio.SettingsBindFlags.DEFAULT);
        group.add(enable);
        const device = new Adw.EntryRow({title: 'Touchpad device (optional; blank = automatic)'});
        settings.bind('device-path', device, 'text', Gio.SettingsBindFlags.DEFAULT);
        group.add(device);
        const values = ['disabled', 'diagnostic', 'apps', 'apps-close', 'overview', 'hide'];
        const labels = ['Disabled', 'Detect only (no action)',
            'Open app grid', 'Close app grid',
            'Open overview', 'Close overview'];
        for (const [key, title] of [['pinch-in', 'Pinch in'], ['pinch-out', 'Pinch out']]) {
            const row = new Adw.ComboRow({title, model: Gtk.StringList.new(labels),
                selected: Math.max(0, values.indexOf(settings.get_string(key)))});
            row.connect('notify::selected', () => settings.set_string(key, values[row.selected] ?? 'disabled'));
            const id = settings.connect(`changed::${key}`, () => {
                row.selected = Math.max(0, values.indexOf(settings.get_string(key)));
            });
            window.connect('close-request', () => { settings.disconnect(id); return false; });
            group.add(row);
        }
        const statusGroup = new Adw.PreferencesGroup({title: 'Status'});
        page.add(statusGroup);
        for (const [key, title] of [['status', 'Recognizer'], ['last-event', 'Last gesture']]) {
            const row = new Adw.ActionRow({title, subtitle: settings.get_string(key)});
            settings.bind(key, row, 'subtitle', Gio.SettingsBindFlags.GET);
            statusGroup.add(row);
        }
        const note = new Adw.ActionRow({title: 'Getting started',
            subtitle: 'Start with Detect only. Recognition pauses when the session is locked or inactive. Pausing while typing is experimental; other gesture extensions may conflict.'});
        statusGroup.add(note);
    }
}
