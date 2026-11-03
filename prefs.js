// SPDX-License-Identifier: MIT
import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';
import Gio from 'gi://Gio';
import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

export default class FivePinchPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
        const signals = [];
        window.set_default_size(520, 540);
        window.set_search_enabled(false);
        Gtk.IconTheme.get_for_display(window.get_display()).add_search_path(`${this.path}/icons`);
        const page = new Adw.PreferencesPage({title: 'Five Pinch', icon_name: 'io.github.Nymeriq.FivePinch'});
        window.add(page);

        const toggle = (key, title) => {
            const row = new Adw.SwitchRow({title});
            settings.bind(key, row, 'active', Gio.SettingsBindFlags.DEFAULT);
            return row;
        };
        const choice = (key, title, options) => {
            const values = options.map(([value]) => value);
            const row = new Adw.ComboRow({title,
                model: Gtk.StringList.new(options.map(([, label]) => label)),
                selected: Math.max(0, values.indexOf(settings.get_string(key)))});
            row.connect('notify::selected', () => {
                if (row.selected < values.length)
                    settings.set_string(key, values[row.selected]);
            });
            signals.push(settings.connect(`changed::${key}`, () => {
                row.selected = Math.max(0, values.indexOf(settings.get_string(key)));
            }));
            return row;
        };
        const gestures = new Adw.PreferencesGroup();
        page.add(gestures);
        gestures.add(toggle('enabled', 'Enable gestures'));
        const actions = [
            ['disabled', 'Off'], ['diagnostic', 'Detect only'],
            ['apps', 'Open app grid'], ['apps-close', 'Close app grid'],
            ['overview', 'Open overview'], ['hide', 'Close overview'],
        ];
        gestures.add(choice('pinch-in', 'Pinch in', actions));
        gestures.add(choice('pinch-out', 'Pinch out', actions));
        gestures.add(choice('sensitivity', 'Sensitivity', [
            ['original', 'Original'], ['balanced', 'Balanced'], ['relaxed', 'Sensitive'],
        ]));

        const advancedGroup = new Adw.PreferencesGroup();
        const advanced = new Adw.ExpanderRow({title: 'Advanced'});
        advancedGroup.add(advanced);
        page.add(advancedGroup);
        const device = new Adw.EntryRow({title: 'Touchpad'});
        device.get_delegate().set_placeholder_text('/dev/input/event7');
        device.set_tooltip_text('Leave empty for automatic selection.');
        settings.bind('device-path', device, 'text', Gio.SettingsBindFlags.DEFAULT);
        advanced.add_row(device);
        advanced.add_row(toggle('protect-pinch-tail', 'Swipe protection'));
        advanced.add_row(toggle('protect-rinertia', 'rinertia protection'));

        const diagnosticsGroup = new Adw.PreferencesGroup();
        const diagnostics = new Adw.ExpanderRow({title: 'Diagnostics'});
        diagnosticsGroup.add(diagnostics);
        page.add(diagnosticsGroup);
        for (const [key, title] of [['status', 'Recognizer'], ['last-event', 'Last gesture'], ['tail-status', 'Protection']]) {
            const row = new Adw.ActionRow({title, subtitle_selectable: true});
            settings.bind(key, row, 'subtitle', Gio.SettingsBindFlags.GET);
            diagnostics.add_row(row);
        }
        window.connect('close-request', () => {
            for (const id of signals)
                settings.disconnect(id);
            return false;
        });
    }
}
