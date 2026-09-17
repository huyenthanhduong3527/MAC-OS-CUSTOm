import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';

// Safe fire-and-forget process spawn (strictly non-blocking)
function spawn(argv) {
    try {
        const proc = new Gio.Subprocess({
            argv: argv,
            flags: Gio.SubprocessFlags.NONE,
        });
        proc.init(null);
    } catch (e) {
        console.error(`[macOS Menu Bar] spawn error: ${e}`);
    }
}

// 100% Asynchronous subprocess execution (never blocks GNOME Shell main loop)
function spawnOutputAsync(argv) {
    return new Promise((resolve) => {
        try {
            const proc = new Gio.Subprocess({
                argv: argv,
                flags: Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_MERGE,
            });
            proc.init(null);
            proc.communicate_utf8_async(null, null, (p, res) => {
                try {
                    const [, stdout] = p.communicate_utf8_finish(res);
                    resolve(stdout ? stdout.trim() : '');
                } catch (e) {
                    resolve('');
                }
            });
        } catch (e) {
            resolve('');
        }
    });
}

// Dynamic discovery of Dynamic Island main.py path
function getDynamicIslandPath() {
    const HOME = GLib.get_home_dir();
    const candidates = [
        `${HOME}/Dynamic_island/main.py`,
        `${HOME}/Dynamic_Island/main.py`,
        `${HOME}/.local/share/dynamic-island/main.py`,
    ];
    for (const p of candidates) {
        if (GLib.file_test(p, GLib.FileTest.EXISTS)) {
            return p;
        }
    }
    return `${HOME}/Dynamic_island/main.py`;
}

function runDynamicIsland(args) {
    const script = getDynamicIslandPath();
    spawn(['python3', script, ...args]);
}

// ─── Ultra-Fast Non-Blocking System State Readers ─────────────

function getBatteryInfoFast() {
    try {
        const [okCap, capContent] = GLib.file_get_contents('/sys/class/power_supply/BAT0/capacity');
        if (okCap && capContent) {
            const cap = parseInt(new TextDecoder().decode(capContent).trim()) || 100;
            let icon = 'battery-full-symbolic';
            if (cap < 20) icon = 'battery-caution-symbolic';
            else if (cap < 50) icon = 'battery-low-symbolic';
            else if (cap < 85) icon = 'battery-good-symbolic';
            return { icon: icon, label: `${cap}%` };
        }
    } catch (e) {}
    return { icon: 'battery-level-100-charged-symbolic', label: '100%' };
}

function getWifiInfoFast() {
    try {
        const [ok, contents] = GLib.file_get_contents('/proc/net/wireless');
        if (ok && contents) {
            const text = new TextDecoder().decode(contents);
            const lines = text.split('\n');
            for (let i = 2; i < lines.length; i++) {
                const parts = lines[i].trim().split(/\s+/);
                if (parts.length >= 3) {
                    const qual = parseFloat(parts[2].replace('.', '')) || 0;
                    if (qual >= 60) return { icon: 'network-wireless-signal-excellent-symbolic' };
                    if (qual >= 40) return { icon: 'network-wireless-signal-good-symbolic' };
                    if (qual >= 20) return { icon: 'network-wireless-signal-ok-symbolic' };
                    return { icon: 'network-wireless-signal-weak-symbolic' };
                }
            }
        }
    } catch (e) {}
    return { icon: 'network-wireless-signal-excellent-symbolic' };
}

function getBluetoothInfoFast() {
    try {
        const hasBt = GLib.file_test('/sys/class/bluetooth', GLib.FileTest.EXISTS);
        return { icon: hasBt ? 'bluetooth-active-symbolic' : 'bluetooth-disabled-symbolic' };
    } catch (e) {
        return { icon: 'bluetooth-disabled-symbolic' };
    }
}

// ─── 1. Apple Logo Menu () ──────────────────────────────────
const AppleMenu = GObject.registerClass(
class AppleMenu extends PanelMenu.Button {
    _init(extensionPath) {
        super._init(0.0, 'Apple Menu');
        this.add_style_class_name('mac-apple-btn');

        let iconActor = null;
        try {
            const file = Gio.File.new_for_path(`${extensionPath}/apple-symbolic.svg`);
            if (file.query_exists(null)) {
                iconActor = new St.Icon({
                    gicon: new Gio.FileIcon({ file }),
                    style_class: 'mac-apple-icon',
                    icon_size: 15,
                    y_align: Clutter.ActorAlign.CENTER,
                });
            }
        } catch (e) {}

        if (!iconActor) {
            iconActor = new St.Label({
                text: '',
                y_align: Clutter.ActorAlign.CENTER,
            });
        }
        this.add_child(iconActor);
        this._buildMenu();
    }

    _buildMenu() {
        this.menu.box.add_style_class_name('mac-popup-menu');
        this._addItem('About This Mac', () => spawn(['gnome-control-center', 'system']));
        this._addItem('System Settings…', () => spawn(['gnome-control-center']));
        this._addItem('App Store…', () => spawn(['snap-store']));
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._addItem('🌗 Chuyển Giao diện Sáng / Tối', () => runDynamicIsland(['theme']));
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._addItem('Force Quit…', () => spawn(['xkill']));
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._addItem('Sleep', () => spawn(['systemctl', 'suspend']));
        this._addItem('Restart…', () => spawn(['gnome-session-quit', '--reboot']));
        this._addItem('Shut Down…', () => spawn(['gnome-session-quit', '--power-off']));
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._addItem('Lock Screen', () => spawn(['loginctl', 'lock-session']));
        this._addItem('Log Out…', () => spawn(['gnome-session-quit', '--logout']));
    }

    _addItem(title, callback) {
        const item = new PopupMenu.PopupMenuItem(title);
        item.add_style_class_name('mac-popup-item');
        item.connect('activate', callback);
        this.menu.addMenuItem(item);
    }
});

// ─── 2. Active Application Menu (Bold App Name) ───────────────
const ActiveAppMenu = GObject.registerClass(
class ActiveAppMenu extends PanelMenu.Button {
    _init() {
        super._init(0.0, 'Active App Menu');
        this.add_style_class_name('mac-app-title-btn');

        const label = new St.Label({
            text: 'Dynamic Island',
            style_class: 'mac-app-title-label',
            y_align: Clutter.ActorAlign.CENTER,
        });
        this.add_child(label);

        this.menu.box.add_style_class_name('mac-popup-menu');
        this._addItem('About Dynamic Island', () => runDynamicIsland(['tab', 'settings']));
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._addItem('Preferences…', () => runDynamicIsland(['tab', 'settings']));
        this._addItem('Toggle Dynamic Island Hub', () => runDynamicIsland(['toggle']));
        this._addItem('System Vitals Hub', () => runDynamicIsland(['tab', 'vitals']));
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._addItem('Hide Dynamic Island', () => runDynamicIsland(['collapse']));
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._addItem('Quit Dynamic Island', () => runDynamicIsland(['quit']));
    }

    _addItem(title, callback) {
        const item = new PopupMenu.PopupMenuItem(title);
        item.add_style_class_name('mac-popup-item');
        item.connect('activate', callback);
        this.menu.addMenuItem(item);
    }
});

// ─── 3. Global Menu Buttons (File, Edit, View, …) ────────────
const MacMenuButton = GObject.registerClass(
class MacMenuButton extends PanelMenu.Button {
    _init(title, items) {
        super._init(0.0, title);
        this.add_style_class_name('mac-menu-item');

        const label = new St.Label({
            text: title,
            y_align: Clutter.ActorAlign.CENTER,
        });
        this.add_child(label);

        this.menu.box.add_style_class_name('mac-popup-menu');
        for (const it of items) {
            if (it === null) {
                this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            } else {
                const item = new PopupMenu.PopupMenuItem(it.label);
                item.add_style_class_name('mac-popup-item');
                if (it.callback) {
                    item.connect('activate', it.callback);
                }
                this.menu.addMenuItem(item);
            }
        }
    }
});

// ─── 4. Center Dynamic Island Capsule ────────────────────────
const CenterIslandWidget = GObject.registerClass(
class CenterIslandWidget extends PanelMenu.Button {
    _init() {
        super._init(0.5, 'Dynamic Island Center Capsule');
        this.add_style_class_name('mac-center-island-container');

        const box = new St.BoxLayout({
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'mac-center-island-pill',
        });

        this._iconLabel = new St.Label({
            text: '🏝️',
            style_class: 'mac-center-island-icon',
            y_align: Clutter.ActorAlign.CENTER,
        });
        box.add_child(this._iconLabel);

        this._statusLabel = new St.Label({
            text: 'Dynamic Island',
            style_class: 'mac-center-island-text',
            y_align: Clutter.ActorAlign.CENTER,
        });
        box.add_child(this._statusLabel);

        this.add_child(box);

        this.connect('clicked', () => {
            runDynamicIsland(['toggle']);
        });

        this._buildMenu();
    }

    _buildMenu() {
        this.menu.box.add_style_class_name('mac-popup-menu');
        this._addItem('🎵  Trình phát nhạc', () => runDynamicIsland(['tab', 'media']));
        this._addItem('⚡  Tài nguyên hệ thống (Vitals)', () => runDynamicIsland(['tab', 'vitals']));
        this._addItem('🎛️  Bảng điều khiển nhanh (Controls)', () => runDynamicIsland(['tab', 'controls']));
        this._addItem('⏱️  Đồng hồ đếm giờ & Pomodoro', () => runDynamicIsland(['tab', 'timer']));
        this._addItem('🔔  Thông báo hệ thống (Notifications)', () => runDynamicIsland(['tab', 'notifs']));
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._addItem('🌗  Chuyển Giao diện Sáng / Tối', () => runDynamicIsland(['theme']));
        this._addItem('⚙️  Cài đặt Dynamic Island…', () => runDynamicIsland(['tab', 'settings']));
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._addItem('Bung mở Hub', () => runDynamicIsland(['expand']));
        this._addItem('Thu nhỏ viên thuốc', () => runDynamicIsland(['collapse']));
    }

    _addItem(title, callback) {
        const item = new PopupMenu.PopupMenuItem(title);
        item.add_style_class_name('mac-popup-item');
        item.connect('activate', callback);
        this.menu.addMenuItem(item);
    }
});

// ─── 5. Right Status Tray & Clock ───────────────────────────
const MacStatusTray = GObject.registerClass(
class MacStatusTray extends PanelMenu.Button {
    _init() {
        super._init(0.0, 'macOS Status Tray');
        this.add_style_class_name('mac-tray-container');

        // Clean BoxLayout without spacing property in JS (handled by CSS)
        this.containerBox = new St.BoxLayout({
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'mac-status-box',
        });
        this.add_child(this.containerBox);

        this._icons = {};
        this._isUpdating = false;

        // 1. Instant zero-delay UI setup with native icons
        this._createIcons();
        this._startClock();

        // 2. Set instant fast initial state without executing any slow process
        this._applyFastStatus();

        // 3. Delay initial background async refresh by 2s after login to guarantee zero startup lag
        this._initTimer = GLib.timeout_add_seconds(GLib.PRIORITY_LOW, 2, () => {
            this._refreshStatusesAsync();
            this._refreshWeatherAsync();
            this._initTimer = null;
            return GLib.SOURCE_REMOVE;
        });

        // 4. Subsequent periodic updates every 10 seconds at low priority
        this._statusTimer = GLib.timeout_add_seconds(GLib.PRIORITY_LOW, 10, () => {
            this._refreshStatusesAsync();
            return GLib.SOURCE_CONTINUE;
        });

        // 5. Weather update every 15 minutes
        this._weatherTimer = GLib.timeout_add_seconds(GLib.PRIORITY_LOW, 900, () => {
            this._refreshWeatherAsync();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _createIcons() {
        // 1. Live Weather Widget (Icon + Temp)
        this._icons.weatherBtn = new St.Button({
            style_class: 'mac-tray-icon-btn mac-weather-btn',
            reactive: true,
            can_focus: true,
            y_align: Clutter.ActorAlign.CENTER,
        });
        const weatherBox = new St.BoxLayout({ y_align: Clutter.ActorAlign.CENTER });
        this._icons.weatherIcon = new St.Icon({
            icon_name: 'weather-clear-symbolic',
            icon_size: 13,
            style_class: 'mac-tray-icon',
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._icons.weatherLabel = new St.Label({
            text: '29°C',
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'mac-weather-label',
        });
        weatherBox.add_child(this._icons.weatherIcon);
        weatherBox.add_child(this._icons.weatherLabel);
        this._icons.weatherBtn.set_child(weatherBox);
        this._icons.weatherBtn.connect('clicked', () => spawn(['gnome-weather']));
        this.containerBox.add_child(this._icons.weatherBtn);

        // 2. Music Player Pill
        this._icons.music = this._addIconButton(
            'emblem-music-symbolic', 14,
            () => runDynamicIsland(['tab', 'media'])
        );

        // 3. Timer Shortcut
        this._icons.timer = this._addIconButton(
            'alarm-symbolic', 14,
            () => runDynamicIsland(['tab', 'timer'])
        );

        // 4. System Vitals
        this._icons.vitals = this._addIconButton(
            'utilities-system-monitor-symbolic', 14,
            () => runDynamicIsland(['tab', 'vitals'])
        );

        // 5. Battery Icon + Label
        this._icons.battery = this._addIconButton(
            'battery-level-100-charged-symbolic', 14,
            () => spawn(['gnome-control-center', 'power'])
        );
        this._icons.batteryLabel = new St.Label({
            text: '100%',
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'mac-tray-label',
        });
        this.containerBox.add_child(this._icons.batteryLabel);

        // 6. Volume Control
        this._icons.volume = this._addIconButton(
            'audio-volume-high-symbolic', 14,
            () => runDynamicIsland(['tab', 'controls'])
        );

        // 7. Wi-Fi
        this._icons.wifi = this._addIconButton(
            'network-wireless-signal-excellent-symbolic', 14,
            () => spawn(['gnome-control-center', 'wifi'])
        );

        // 8. Bluetooth
        this._icons.bluetooth = this._addIconButton(
            'bluetooth-active-symbolic', 14,
            () => spawn(['gnome-control-center', 'bluetooth'])
        );

        // 9. Notification Bell
        this._icons.notification = this._addIconButton(
            'notification-symbolic', 14,
            () => runDynamicIsland(['tab', 'notifs'])
        );

        // 10. Dark / Light Theme Toggle (Chuyển giao diện Sáng / Tối)
        this._icons.theme = this._addIconButton(
            'weather-clear-night-symbolic', 14,
            () => this._toggleTheme()
        );

        // 11. Control Center (macOS Two-Slider Icon)
        this._icons.controlCenter = this._addIconButton(
            'open-menu-symbolic', 14,
            () => {
                if (Main.panel.statusArea.quickSettings?.menu) {
                    Main.panel.statusArea.quickSettings.menu.toggle();
                } else {
                    runDynamicIsland(['tab', 'controls']);
                }
            }
        );

        // 11. Date & Time
        this.clockLabel = new St.Label({
            text: this._getFormattedTime(),
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'mac-clock-btn',
            reactive: true,
            can_focus: true,
        });
        this.clockLabel.connect('button-press-event', () => {
            if (Main.panel.statusArea.dateMenu?.menu) {
                Main.panel.statusArea.dateMenu.menu.toggle();
            }
            return Clutter.EVENT_STOP;
        });
        this.containerBox.add_child(this.clockLabel);

        // 12. Spotlight Search
        this._icons.search = this._addIconButton(
            'system-search-symbolic', 14,
            () => {
                spawn(['ulauncher-toggle']);
                GLib.timeout_add(GLib.PRIORITY_DEFAULT, 100, () => {
                    if (!Main.overview.visible) Main.overview.show();
                    return GLib.SOURCE_REMOVE;
                });
            }
        );
    }

    _addIconButton(iconName, size, onClick) {
        const btn = new St.Button({
            style_class: 'mac-tray-icon-btn',
            reactive: true,
            can_focus: true,
            y_align: Clutter.ActorAlign.CENTER,
        });
        const icon = new St.Icon({
            icon_name: iconName,
            icon_size: size,
            style_class: 'mac-tray-icon',
            y_align: Clutter.ActorAlign.CENTER,
        });
        btn.set_child(icon);
        btn._stIcon = icon;
        if (onClick) {
            btn.connect('clicked', onClick);
        }
        this.containerBox.add_child(btn);
        return btn;
    }

    _applyFastStatus() {
        const bat = getBatteryInfoFast();
        if (this._icons.battery?._stIcon) this._icons.battery._stIcon.icon_name = bat.icon;
        if (this._icons.batteryLabel) this._icons.batteryLabel.set_text(bat.label);

        const wifi = getWifiInfoFast();
        if (this._icons.wifi?._stIcon) this._icons.wifi._stIcon.icon_name = wifi.icon;

        const bt = getBluetoothInfoFast();
        if (this._icons.bluetooth?._stIcon) this._icons.bluetooth._stIcon.icon_name = bt.icon;

        this._updateThemeIcon(this._isDarkMode());
    }

    _isDarkMode() {
        try {
            const settings = new Gio.Settings({ schema_id: 'org.gnome.desktop.interface' });
            return settings.get_string('color-scheme') === 'prefer-dark';
        } catch (e) {
            return false;
        }
    }

    _toggleTheme() {
        try {
            const settings = new Gio.Settings({ schema_id: 'org.gnome.desktop.interface' });
            const isDark = settings.get_string('color-scheme') === 'prefer-dark';
            const newScheme = isDark ? 'default' : 'prefer-dark';
            settings.set_string('color-scheme', newScheme);

            const HOME = GLib.get_home_dir();
            const targetTheme = isDark ? 'MacTahoe-Light' : 'MacTahoe-Dark';
            if (GLib.file_test(`${HOME}/.themes/${targetTheme}`, GLib.FileTest.EXISTS)) {
                settings.set_string('gtk-theme', targetTheme);
            }
            this._updateThemeIcon(!isDark);
        } catch (e) {
            console.error(`[macOS Menu Bar] theme toggle error: ${e}`);
        }
    }

    _updateThemeIcon(isDark) {
        if (this._icons.theme?._stIcon) {
            this._icons.theme._stIcon.icon_name = isDark
                ? 'weather-clear-symbolic'       // Sun icon: click to switch to light
                : 'weather-clear-night-symbolic'; // Moon icon: click to switch to dark
        }
    }

    async _refreshStatusesAsync() {
        if (this._isUpdating) return;
        this._isUpdating = true;

        try {
            this._applyFastStatus();
            this._updateThemeIcon(this._isDarkMode());

            // Volume update via async non-blocking command
            const out = await spawnOutputAsync(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@']);
            if (out && this._icons.volume?._stIcon) {
                const muted = out.includes('[MUTED]');
                const m = out.match(/Volume:\s+([\d.]+)/);
                const vol = m ? Math.round(parseFloat(m[1]) * 100) : 50;
                if (muted || vol === 0) this._icons.volume._stIcon.icon_name = 'audio-volume-muted-symbolic';
                else if (vol < 34) this._icons.volume._stIcon.icon_name = 'audio-volume-low-symbolic';
                else if (vol < 67) this._icons.volume._stIcon.icon_name = 'audio-volume-medium-symbolic';
                else this._icons.volume._stIcon.icon_name = 'audio-volume-high-symbolic';
            }
        } catch (e) {
            console.error(`[macOS Menu Bar] async refresh error: ${e}`);
        } finally {
            this._isUpdating = false;
        }
    }

    async _refreshWeatherAsync() {
        try {
            const wttr = await spawnOutputAsync(['curl', '-s', '--max-time', '2', 'wttr.in/?format=%c%t']);
            if (wttr && this._icons.weatherLabel) {
                const clean = wttr.replace(/\+/g, '').trim();
                if (clean && clean.length <= 10) {
                    this._icons.weatherLabel.set_text(clean);
                }
            }
        } catch (e) {}
    }

    _getFormattedTime() {
        const now = GLib.DateTime.new_now_local();
        const dayNames = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];
        const dayOfWeek = dayNames[now.get_day_of_week() % 7];
        const month = String(now.get_month()).padStart(2, '0');
        const day = String(now.get_day_of_month()).padStart(2, '0');

        let hour = now.get_hour();
        const minute = String(now.get_minute()).padStart(2, '0');
        const ampm = hour >= 12 ? 'PM' : 'AM';
        hour = hour % 12 || 12;

        return `${dayOfWeek} ${day}/${month}  ${hour}:${minute} ${ampm}`;
    }

    _startClock() {
        this._clockTimer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1, () => {
            if (this.clockLabel) {
                this.clockLabel.set_text(this._getFormattedTime());
            }
            return GLib.SOURCE_CONTINUE;
        });
    }

    destroy() {
        if (this._clockTimer) {
            GLib.source_remove(this._clockTimer);
            this._clockTimer = null;
        }
        if (this._initTimer) {
            GLib.source_remove(this._initTimer);
            this._initTimer = null;
        }
        if (this._statusTimer) {
            GLib.source_remove(this._statusTimer);
            this._statusTimer = null;
        }
        if (this._weatherTimer) {
            GLib.source_remove(this._weatherTimer);
            this._weatherTimer = null;
        }
        super.destroy();
    }
});

// ─── 6. Main Extension Lifecycle ─────────────────────────────
export default class MacOSMenuBarExtension extends Extension {
    enable() {
        this._buttons = [];
        this._hiddenIndicators = [];
        const HOME = GLib.get_home_dir();

        // 1. Apple Logo Menu
        const extPath = this.path || `${HOME}/.local/share/gnome-shell/extensions/macos-menu-bar@Nguyenthanhtam`;
        const appleMenu = new AppleMenu(extPath);
        Main.panel.addToStatusArea('mac-apple-menu', appleMenu, 0, 'left');
        this._buttons.push('mac-apple-menu');

        // 2. Active App Title Menu (Dynamic Island)
        const appMenu = new ActiveAppMenu();
        Main.panel.addToStatusArea('mac-app-menu', appMenu, 1, 'left');
        this._buttons.push('mac-app-menu');

        // 3. Global Menus (File, Edit, View, Go, Window, Tools, Settings, Help, Search)
        const menus = [
            {
                title: 'File',
                items: [
                    { label: 'New Window', callback: () => spawn(['nautilus', '--new-window']) },
                    { label: 'New Terminal Tab', callback: () => spawn(['gnome-terminal']) },
                    null,
                    { label: 'Open Home Folder…', callback: () => spawn(['nautilus', HOME]) },
                    { label: 'Close Window', callback: () => spawn(['xdotool', 'getactivewindow', 'windowclose']) },
                ]
            },
            {
                title: 'Edit',
                items: [
                    { label: 'Undo', callback: () => spawn(['xdotool', 'key', 'ctrl+z']) },
                    { label: 'Redo', callback: () => spawn(['xdotool', 'key', 'ctrl+shift+z']) },
                    null,
                    { label: 'Cut', callback: () => spawn(['xdotool', 'key', 'ctrl+x']) },
                    { label: 'Copy', callback: () => spawn(['xdotool', 'key', 'ctrl+c']) },
                    { label: 'Paste', callback: () => spawn(['xdotool', 'key', 'ctrl+v']) },
                    { label: 'Select All', callback: () => spawn(['xdotool', 'key', 'ctrl+a']) },
                ]
            },
            {
                title: 'View',
                items: [
                    { label: 'Reload View', callback: () => spawn(['xdotool', 'key', 'F5']) },
                    null,
                    { label: 'Zoom In', callback: () => spawn(['xdotool', 'key', 'ctrl+plus']) },
                    { label: 'Zoom Out', callback: () => spawn(['xdotool', 'key', 'ctrl+minus']) },
                    { label: 'Actual Size', callback: () => spawn(['xdotool', 'key', 'ctrl+0']) },
                    null,
                    { label: 'Enter Full Screen', callback: () => spawn(['xdotool', 'key', 'F11']) },
                ]
            },
            {
                title: 'Go',
                items: [
                    { label: 'Home Folder', callback: () => spawn(['nautilus', HOME]) },
                    { label: 'Documents', callback: () => spawn(['nautilus', `${HOME}/Documents`]) },
                    { label: 'Downloads', callback: () => spawn(['nautilus', `${HOME}/Downloads`]) },
                    { label: 'Pictures', callback: () => spawn(['nautilus', `${HOME}/Pictures`]) },
                    null,
                    { label: 'Dynamic Island Project', callback: () => spawn(['nautilus', getDynamicIslandPath().replace('/main.py', '')]) },
                ]
            },
            {
                title: 'Window',
                items: [
                    { label: 'Minimize', callback: () => spawn(['xdotool', 'getactivewindow', 'windowminimize']) },
                    { label: 'Zoom (Toggle Maximize)', callback: () => spawn(['xdotool', 'key', 'super+Up']) },
                    null,
                    { label: 'Tile Window to Left', callback: () => spawn(['xdotool', 'key', 'super+Left']) },
                    { label: 'Tile Window to Right', callback: () => spawn(['xdotool', 'key', 'super+Right']) },
                    null,
                    { label: 'Bring All to Front', callback: () => spawn(['wmctrl', '-k', 'off']) },
                ]
            },
            {
                title: 'Tools',
                items: [
                    { label: 'Terminal', callback: () => spawn(['gnome-terminal']) },
                    { label: 'System Monitor', callback: () => spawn(['gnome-system-monitor']) },
                    { label: 'Capture Screenshot', callback: () => spawn(['gnome-screenshot', '-i']) },
                    null,
                    { label: 'Expand Dynamic Island Hub', callback: () => runDynamicIsland(['expand']) },
                    { label: 'Collapse Dynamic Island', callback: () => runDynamicIsland(['collapse']) },
                ]
            },
            {
                title: 'Settings',
                items: [
                    { label: 'Dynamic Island Settings…', callback: () => runDynamicIsland(['tab', 'settings']) },
                    { label: '🌗 Chuyển Giao diện Sáng / Tối', callback: () => runDynamicIsland(['theme']) },
                    null,
                    { label: 'Display Settings…', callback: () => spawn(['gnome-control-center', 'display']) },
                    { label: 'Sound Settings…', callback: () => spawn(['gnome-control-center', 'sound']) },
                    { label: 'Network Settings…', callback: () => spawn(['gnome-control-center', 'wifi']) },
                    { label: 'Bluetooth Settings…', callback: () => spawn(['gnome-control-center', 'bluetooth']) },
                    null,
                    { label: 'Extensions Manager…', callback: () => spawn(['com.mattjakeman.ExtensionManager']) },
                ]
            },
            {
                title: 'Help',
                items: [
                    { label: 'Dynamic Island Help', callback: () => runDynamicIsland(['tab', 'settings']) },
                    { label: 'GNOME Help', callback: () => spawn(['yelp']) },
                    { label: 'Keyboard Shortcuts', callback: () => spawn(['gnome-control-center', 'keyboard']) },
                    null,
                    { label: 'About macOS Menu Bar', callback: () => spawn(['zenity', '--info', '--text=macOS Tahoe / Sequoia Menu Bar for Ubuntu GNOME']) },
                ]
            },
            {
                title: 'Search',
                items: [
                    { label: 'Spotlight Search', callback: () => spawn(['ulauncher-toggle']) },
                    { label: 'Find Files…', callback: () => spawn(['nautilus']) },
                ]
            }
        ];

        let leftIdx = 2;
        for (const m of menus) {
            const btn = new MacMenuButton(m.title, m.items);
            const id = `mac-menu-${m.title.toLowerCase()}`;
            Main.panel.addToStatusArea(id, btn, leftIdx++, 'left');
            this._buttons.push(id);
        }

        // 4. Center Dynamic Island Capsule
        const centerIsland = new CenterIslandWidget();
        Main.panel.addToStatusArea('mac-center-island', centerIsland, 0, 'center');
        this._buttons.push('mac-center-island');

        // 5. Clear center space so Center Island sits cleanly in the center
        if (Main.panel.statusArea.dateMenu?.container) {
            Main.panel.statusArea.dateMenu.container.visible = false;
            this._hiddenIndicators.push('dateMenu');
        }

        // 6. Right Status Tray (with real system icons, ultra-fast & non-blocking)
        const rightTray = new MacStatusTray();
        Main.panel.addToStatusArea('mac-right-tray', rightTray, 0, 'right');
        this._buttons.push('mac-right-tray');
    }

    disable() {
        // Restore hidden indicators
        for (const id of this._hiddenIndicators) {
            if (Main.panel.statusArea[id]?.container) {
                Main.panel.statusArea[id].container.visible = true;
            }
        }
        this._hiddenIndicators = [];

        // Destroy added buttons
        for (const id of this._buttons) {
            if (Main.panel.statusArea[id]) {
                Main.panel.statusArea[id].destroy();
            }
        }
        this._buttons = [];
    }
}
