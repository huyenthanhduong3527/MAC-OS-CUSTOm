import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import UPowerGlib from 'gi://UPowerGlib';
import Cairo from 'cairo';

function getAppLanguage() {
    try {
        const configPath = `${GLib.get_home_dir()}/.config/dynamic_island/config.json`;
        const file = Gio.File.new_for_path(configPath);
        if (file.query_exists(null)) {
            const [, contents] = file.load_contents(null);
            const data = JSON.parse(new TextDecoder().decode(contents));
            if (data && data.language) {
                // Settings may persist either a language id (zh) or a locale
                // (zh_CN.UTF-8).  The menu only needs the stable language id.
                const raw = String(data.language).trim().toLowerCase();
                const base = raw.split(/[_.-]/)[0];
                if (base === 'zh' || base === 'cmn') return 'zh';
                if (base === 'ja') return 'ja';
                if (base === 'vi') return 'vi';
                if (base === 'ko') return 'ko';
                if (base === 'fr') return 'fr';
                if (base === 'de') return 'de';
                if (base === 'es') return 'es';
                if (base === 'pt') return 'pt';
                if (base === 'ru') return 'ru';
                if (base === 'en') return 'en';
                return base || 'en';
            }
        }
    } catch (e) {}
    return 'en';
}

function shouldShowAppName() {
    try {
        const configPath = `${GLib.get_home_dir()}/.config/dynamic_island/config.json`;
        const file = Gio.File.new_for_path(configPath);
        if (file.query_exists(null)) {
            const [, contents] = file.load_contents(null);
            const data = JSON.parse(new TextDecoder().decode(contents));
            if (data && typeof data.menu_bar_show_app_name !== 'undefined') {
                return !!data.menu_bar_show_app_name;
            }
        }
    } catch (e) {}
    return false;
}

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

// Native Window Management (Mutter / Wayland)
function closeActiveWindow() {
    const win = global.display.focus_window;
    if (win) {
        win.delete(global.get_current_time());
    }
}

function forceQuitActiveWindow() {
    const win = global.display.focus_window;
    if (win) {
        win.kill();
    } else {
        spawn(['xkill']);
    }
}

function minimizeActiveWindow() {
    const win = global.display.focus_window;
    if (win) {
        win.minimize();
    }
}

function toggleFullscreenActiveWindow() {
    const win = global.display.focus_window;
    if (win) {
        if (win.is_fullscreen()) {
            win.unmake_fullscreen();
        } else {
            win.make_fullscreen();
        }
    }
}

function toggleMaximizeActiveWindow() {
    const win = global.display.focus_window;
    if (win) {
        if (win.get_maximized()) {
            win.unmaximize(Meta.MaximizeFlags.BOTH);
        } else {
            win.maximize(Meta.MaximizeFlags.BOTH);
        }
    }
}

function openTerminal() {
    const term = GLib.find_program_in_path('ptyxis') ||
                 GLib.find_program_in_path('x-terminal-emulator') ||
                 GLib.find_program_in_path('gnome-terminal') ||
                 'x-terminal-emulator';
    spawn([term]);
}

function openScreenshot() {
    if (Main.screenshotUI && typeof Main.screenshotUI.open === 'function') {
        Main.screenshotUI.open();
    } else if (typeof Main.openScreenshotUI === 'function') {
        Main.openScreenshotUI();
    } else {
        spawn(['gnome-screenshot', '-i']);
    }
}

function openSystemMonitor() {
    if (GLib.find_program_in_path('gnome-system-monitor')) {
        spawn(['gnome-system-monitor']);
    } else if (GLib.find_program_in_path('mission-center')) {
        spawn(['mission-center']);
    } else {
        runDynamicIsland(['tab', 'vitals']);
    }
}

let _virtualKeyboard = null;
function getVirtualKeyboard() {
    if (!_virtualKeyboard) {
        try {
            const seat = Clutter.get_default_backend().get_default_seat();
            if (seat && seat.create_virtual_device) {
                _virtualKeyboard = seat.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
            }
        } catch (e) {
            console.error(`[macOS Menu Bar] Virtual keyboard error: ${e}`);
        }
    }
    return _virtualKeyboard;
}

function sendKey(keyval, useCtrl = false, useShift = false) {
    GLib.timeout_add(GLib.PRIORITY_DEFAULT, 80, () => {
        try {
            const vk = getVirtualKeyboard();
            if (vk) {
                const now = global.get_current_time();
                if (useCtrl) vk.notify_keyval(now, Clutter.KEY_Control_L || 0xffe3, Clutter.KeyState.PRESSED);
                if (useShift) vk.notify_keyval(now, Clutter.KEY_Shift_L || 0xffe1, Clutter.KeyState.PRESSED);
                vk.notify_keyval(now, keyval, Clutter.KeyState.PRESSED);
                vk.notify_keyval(now + 10, keyval, Clutter.KeyState.RELEASED);
                if (useShift) vk.notify_keyval(now + 20, Clutter.KEY_Shift_L || 0xffe1, Clutter.KeyState.RELEASED);
                if (useCtrl) vk.notify_keyval(now + 20, Clutter.KEY_Control_L || 0xffe3, Clutter.KeyState.RELEASED);
            }
        } catch (e) {
            console.error(`[macOS Menu Bar] sendKey error: ${e}`);
        }
        return GLib.SOURCE_REMOVE;
    });
}

// Dynamic discovery of Dynamic Island main.py path
function getDynamicIslandPath() {
    const HOME = GLib.get_home_dir();
    const candidates = [
        `${HOME}/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/main.py`,
        `${HOME}/.local/share/dynamic-island/main.py`,
        `${HOME}/Dynamic_island/main.py`,
        `${HOME}/Dynamic_Island/main.py`,
    ];
    for (const p of candidates) {
        if (GLib.file_test(p, GLib.FileTest.EXISTS)) {
            return p;
        }
    }
    return `${HOME}/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/main.py`;
}

function runDynamicIsland(args) {
    const script = getDynamicIslandPath();
    spawn(['python3', script, ...args]);
}

const _uid = Date.now() + '_' + Math.floor(Math.random() * 10000);

// ─── 1. Apple Logo Menu () ──────────────────────────────────
const AppleMenu = GObject.registerClass(
{ GTypeName: `MacAppleMenu_${_uid}` },
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
        const lang = getAppLanguage();
        if (lang === 'ja') {
            this._addItem('このMacについて (Dynamic Island)', () => runDynamicIsland(['settings']));
            this._addItem('システム設定 (macOS Settings)…', () => runDynamicIsland(['settings']));
            this._addItem('コントロールセンター…', () => runDynamicIsland(['control-center']));
            this._addItem('AirDrop (ファイル共有)…', () => runDynamicIsland(['airdrop']));
            this._addItem('App Store…', () => runDynamicIsland(['appstore']));
            this._addItem('Spotlight検索…', () => runDynamicIsland(['spotlight']));
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addItem('外観モードを切り替え (ライト / ダーク)', () => runDynamicIsland(['theme']));
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addItem('強制終了…', () => forceQuitActiveWindow());
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addItem('スリープ', () => spawn(['systemctl', 'suspend']));
            this._addItem('再起動…', () => spawn(['gnome-session-quit', '--reboot']));
            this._addItem('システム終了…', () => spawn(['gnome-session-quit', '--power-off']));
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addItem('画面をロック', () => spawn(['loginctl', 'lock-session']));
            this._addItem('ログアウト…', () => spawn(['gnome-session-quit', '--logout']));
        } else if (lang === 'vi') {
            this._addItem('Giới thiệu Dynamic Island', () => runDynamicIsland(['settings']));
            this._addItem('Cài đặt hệ thống (macOS Settings)…', () => runDynamicIsland(['settings']));
            this._addItem('Trung tâm Điều khiển (Control Center)…', () => runDynamicIsland(['control-center']));
            this._addItem('AirDrop (Chia sẻ tệp)…', () => runDynamicIsland(['airdrop']));
            this._addItem('App Store…', () => runDynamicIsland(['appstore']));
            this._addItem('Tìm kiếm Spotlight (Spotlight Search)…', () => runDynamicIsland(['spotlight']));
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addItem('Chuyển Giao diện Sáng / Tối', () => runDynamicIsland(['theme']));
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addItem('Bắt buộc thoát (Force Quit)…', () => forceQuitActiveWindow());
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addItem('Ngủ (Sleep)', () => spawn(['systemctl', 'suspend']));
            this._addItem('Khởi động lại…', () => spawn(['gnome-session-quit', '--reboot']));
            this._addItem('Tắt máy…', () => spawn(['gnome-session-quit', '--power-off']));
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addItem('Khóa màn hình', () => spawn(['loginctl', 'lock-session']));
            this._addItem('Đăng xuất…', () => spawn(['gnome-session-quit', '--logout']));
        } else if (lang === 'zh') {
            this._addItem('关于 Dynamic Island', () => runDynamicIsland(['settings']));
            this._addItem('系统设置…', () => runDynamicIsland(['settings']));
            this._addItem('控制中心…', () => runDynamicIsland(['control-center']));
            this._addItem('隔空投送…', () => runDynamicIsland(['airdrop']));
            this._addItem('App Store…', () => runDynamicIsland(['appstore']));
            this._addItem('聚焦搜索 (Spotlight)…', () => runDynamicIsland(['spotlight']));
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addItem('切换浅色 / 深色外观', () => runDynamicIsland(['theme']));
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addItem('强制退出…', () => forceQuitActiveWindow());
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addItem('睡眠', () => spawn(['systemctl', 'suspend']));
            this._addItem('重新启动…', () => spawn(['gnome-session-quit', '--reboot']));
            this._addItem('关机…', () => spawn(['gnome-session-quit', '--power-off']));
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addItem('锁定屏幕', () => spawn(['loginctl', 'lock-session']));
            this._addItem('退出登录…', () => spawn(['gnome-session-quit', '--logout']));
        } else {
            this._addItem('About Dynamic Island', () => runDynamicIsland(['settings']));
            this._addItem('System Settings…', () => runDynamicIsland(['settings']));
            this._addItem('Control Center…', () => runDynamicIsland(['control-center']));
            this._addItem('AirDrop…', () => runDynamicIsland(['airdrop']));
            this._addItem('App Store…', () => runDynamicIsland(['appstore']));
            this._addItem('Spotlight Search…', () => runDynamicIsland(['spotlight']));
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addItem('Toggle Dark / Light Theme', () => runDynamicIsland(['theme']));
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addItem('Force Quit…', () => forceQuitActiveWindow());
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addItem('Sleep', () => spawn(['systemctl', 'suspend']));
            this._addItem('Restart…', () => spawn(['gnome-session-quit', '--reboot']));
            this._addItem('Shut Down…', () => spawn(['gnome-session-quit', '--power-off']));
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._addItem('Lock Screen', () => spawn(['loginctl', 'lock-session']));
            this._addItem('Log Out…', () => spawn(['gnome-session-quit', '--logout']));
        }
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
{ GTypeName: `MacActiveAppMenu_${_uid}` },
class ActiveAppMenu extends PanelMenu.Button {
    _init(language = 'en') {
        super._init(0.0, 'Active App Menu');
        this._language = language;
        this.add_style_class_name('mac-app-title-btn');

        this._box = new St.BoxLayout({
            style_class: 'mac-active-app-box',
            y_align: Clutter.ActorAlign.CENTER,
            x_align: Clutter.ActorAlign.START,
        });

        // Bold App Name Label (authentic macOS menu bar has no app icon)
        this._label = new St.Label({
            text: 'Finder',
            style_class: 'mac-app-title-label',
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._box.add_child(this._label);

        this.add_child(this._box);
        this.menu.box.add_style_class_name('mac-popup-menu');

        this._tracker = Shell.WindowTracker.get_default();
        this._focusAppSignal = this._tracker.connect('notify::focus-app', () => this._syncActiveApp());
        this._focusWinSignal = global.display.connect('notify::focus-window', () => this._syncActiveApp());

        this._syncActiveApp();
    }

    _syncActiveApp() {
        try {
            const win = global.display.focus_window;
            let app = null;

            if (win) {
                app = this._tracker.get_window_app(win);
            }
            if (!app) {
                app = this._tracker.focus_app;
            }

            let appName = 'Finder';

            if (app) {
                const name = app.get_name();
                if (name && name.trim()) {
                    appName = name.trim();
                }
            } else if (win) {
                const wmClass = win.get_wm_class ? win.get_wm_class() : null;
                const title = win.get_title ? win.get_title() : null;
                appName = wmClass || title || 'Finder';
            }

            if (appName.toLowerCase().includes('dynamic-island') || appName.toLowerCase().includes('main.py')) {
                appName = 'Dynamic Island';
            } else if (appName.toLowerCase().includes('desktopwidget') ||
                       appName.toLowerCase().includes('desktop-widget') ||
                       appName.toLowerCase().includes('widget')) {
                appName = 'Finder';
            }

            this._label.text = appName;

            this._rebuildMenu(appName, win, app);
        } catch (err) {
            console.error(`[macOS Menu Bar] ActiveAppMenu sync error: ${err}`);
        }
    }

    _rebuildMenu(appName, win, app) {
        this.menu.removeAll();

        const isVi = this._language === 'vi';
        const isJa = this._language === 'ja';
        const isZh = this._language === 'zh';

        const aboutText = isVi ? `Giới thiệu về ${appName}` : (isJa ? `${appName} について` : (isZh ? `关于 ${appName}` : `About ${appName}`));
        const hideText = isVi ? `Ẩn ${appName}` : (isJa ? `${appName} を隠す` : (isZh ? `隐藏 ${appName}` : `Hide ${appName}`));
        const hideOthersText = isVi ? 'Ẩn các ứng dụng khác' : (isJa ? 'ほかを隠す' : (isZh ? '隐藏其他' : 'Hide Others'));
        const showAllText = isVi ? 'Hiện tất cả' : (isJa ? 'すべてを表示' : (isZh ? '显示全部' : 'Show All'));
        const quitText = isVi ? `Thoát ${appName}` : (isJa ? `${appName} を終了` : (isZh ? `退出 ${appName}` : `Quit ${appName}`));

        // 1. About
        this._addItem(aboutText, () => {
            if (win && win.activate) win.activate(global.get_current_time());
        });

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // 2. Hide
        this._addItem(hideText, () => {
            if (win && win.minimize) win.minimize();
        });

        // 3. Hide Others
        this._addItem(hideOthersText, () => {
            try {
                const workspace = global.workspace_manager.get_active_workspace();
                const windows = workspace.list_windows();
                for (const w of windows) {
                    if (w !== win && !w.is_on_all_workspaces() && !w.is_override_redirect()) {
                        w.minimize();
                    }
                }
            } catch (e) {}
        });

        // 4. Show All
        this._addItem(showAllText, () => {
            try {
                const workspace = global.workspace_manager.get_active_workspace();
                const windows = workspace.list_windows();
                for (const w of windows) {
                    w.unminimize();
                }
            } catch (e) {}
        });

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // 5. Quit
        this._addItem(quitText, () => {
            if (win && win.delete) {
                win.delete(global.get_current_time());
            } else if (app && app.request_quit) {
                app.request_quit();
            }
        });
    }

    _addItem(title, callback) {
        const item = new PopupMenu.PopupMenuItem(title);
        item.add_style_class_name('mac-popup-item');
        item.connect('activate', callback);
        this.menu.addMenuItem(item);
    }

    destroy() {
        if (this._focusAppSignal) {
            try { this._tracker.disconnect(this._focusAppSignal); } catch (e) {}
            this._focusAppSignal = null;
        }
        if (this._focusWinSignal) {
            try { global.display.disconnect(this._focusWinSignal); } catch (e) {}
            this._focusWinSignal = null;
        }
        super.destroy();
    }
});

// ─── 3. Global Menu Buttons (File, Edit, View, …) ────────────
const MacMenuButton = GObject.registerClass(
{ GTypeName: `MacMenuButton_${_uid}` },
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
{ GTypeName: `MacCenterIslandWidget_${_uid}` },
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
            text: 'Island',
            style_class: 'mac-center-island-text',
            y_align: Clutter.ActorAlign.CENTER,
        });
        box.add_child(this._statusLabel);

        this.add_child(box);

        // Right-click directly toggles Dynamic Island, left-click opens the dropdown menu
        this.connect('button-press-event', (actor, event) => {
            if (event.get_button() === 3) {
                runDynamicIsland(['toggle']);
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });

        this._buildMenu();
    }

    _buildMenu() {
        this.menu.box.add_style_class_name('mac-popup-menu');
        this._addItem('Bật / Tắt Dynamic Island (Toggle)', () => runDynamicIsland(['toggle']));
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._addItem('Tìm kiếm Spotlight (Spotlight Search)…', () => runDynamicIsland(['spotlight']));
        this._addItem('Trình phát nhạc', () => runDynamicIsland(['tab', 'media']));
        this._addItem('Tài nguyên hệ thống (Vitals)', () => runDynamicIsland(['tab', 'vitals']));
        this._addItem('Bảng điều khiển nhanh (Controls)', () => runDynamicIsland(['tab', 'controls']));
        this._addItem('Đồng hồ đếm giờ & Pomodoro', () => runDynamicIsland(['tab', 'timer']));
        this._addItem('Thông báo hệ thống (Notifications)', () => runDynamicIsland(['tab', 'notifs']));
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._addItem('Chuyển Giao diện Sáng / Tối', () => runDynamicIsland(['theme']));
        this._addItem('Cài đặt hệ thống (macOS Settings)…', () => runDynamicIsland(['settings']));
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

// ─── 4.5. Custom Pixel-Perfect macOS Battery Widget ──────────
const MacBatteryWidget = GObject.registerClass(
{ GTypeName: `MacBatteryWidget_${_uid}` },
class MacBatteryWidget extends St.DrawingArea {
    _init() {
        super._init({
            style_class: 'mac-battery-drawing',
            width: 25,
            height: 12,
            y_align: Clutter.ActorAlign.CENTER,
            reactive: false,
        });
        this._pct = 100;
        this._isCharging = false;
        this._isCharged = true;
        this._isPresent = false;
        this._isHover = false;
    }

    updateState(pct, isCharging, isCharged, isPresent) {
        if (this._pct !== pct || this._isCharging !== isCharging ||
            this._isCharged !== isCharged || this._isPresent !== isPresent) {
            this._pct = pct;
            this._isCharging = isCharging;
            this._isCharged = isCharged;
            this._isPresent = isPresent;
            this.queue_repaint();
        }
    }

    setHover(hover) {
        if (this._isHover !== hover) {
            this._isHover = hover;
            this.queue_repaint();
        }
    }

    vfunc_repaint() {
        const cr = this.get_context();
        const [w, h] = this.get_surface_size();
        cr.setOperator(Cairo.Operator.CLEAR);
        cr.paint();
        cr.setOperator(Cairo.Operator.OVER);

        const scaleX = w > 0 ? w / 25.0 : 1.0;
        const scaleY = h > 0 ? h / 12.0 : 1.0;
        cr.scale(scaleX, scaleY);

        const alpha = this._isHover ? 1.0 : 0.78;

        const roundRect = (x, y, rw, rh, r) => {
            const rad = Math.min(r, rw / 2.0, rh / 2.0);
            cr.newSubPath();
            cr.arc(x + rw - rad, y + rad, rad, -Math.PI / 2, 0);
            cr.arc(x + rw - rad, y + rh - rad, rad, 0, Math.PI / 2);
            cr.arc(x + rad, y + rh - rad, rad, Math.PI / 2, Math.PI);
            cr.arc(x + rad, y + rad, rad, Math.PI, 3 * Math.PI / 2);
            cr.closePath();
        };

        // 1. Outer Battery Body
        const bx = 1.0, by = 1.0, bw = 19.5, bh = 10.0, br = 3.0;
        roundRect(bx, by, bw, bh, br);
        cr.setSourceRGBA(1.0, 1.0, 1.0, alpha);
        cr.setLineWidth(1.0);
        cr.stroke();

        // 2. Positive Terminal Cap
        const cx = bx + bw + 1.2, cy = by + 2.5, cw = 1.5, ch = 5.0, crRad = 0.75;
        roundRect(cx, cy, cw, ch, crRad);
        cr.setSourceRGBA(1.0, 1.0, 1.0, alpha);
        cr.fill();

        // 3. Inner Fill Bar
        const pad = 2.0;
        const ix = bx + pad, iy = by + pad;
        const maxIw = bw - (pad * 2.0);
        const ih = bh - (pad * 2.0);
        const ir = 1.6;

        const pct = Math.max(0, Math.min(100, this._pct));
        const fillW = pct >= 98 ? maxIw : Math.max(1.5, (pct / 100.0) * maxIw);

        if (this._isCharging || (this._isCharged && !this._isPresent)) {
            // Apple macOS Charging Green (#34c759)
            cr.setSourceRGBA(0.204, 0.780, 0.349, 1.0);
        } else if (pct <= 20) {
            // Apple macOS Low Battery Red (#ff3b30)
            cr.setSourceRGBA(1.0, 0.231, 0.188, 1.0);
        } else if (pct <= 35) {
            // Apple macOS Warning Amber (#ff9500)
            cr.setSourceRGBA(1.0, 0.584, 0.0, 1.0);
        } else {
            // Clean Crisp White
            cr.setSourceRGBA(1.0, 1.0, 1.0, 0.95);
        }

        roundRect(ix, iy, fillW, ih, ir);
        cr.fill();

        // 4. Sleek macOS Lightning Bolt when charging or AC connected
        if (this._isCharging || (this._isCharged && !this._isPresent)) {
            const centerX = bx + (bw / 2.0);
            const centerY = by + (bh / 2.0);

            cr.newSubPath();
            cr.moveTo(centerX + 0.6, centerY - 3.4);
            cr.lineTo(centerX - 2.4, centerY + 0.2);
            cr.lineTo(centerX - 0.2, centerY + 0.2);
            cr.lineTo(centerX - 0.6, centerY + 3.4);
            cr.lineTo(centerX + 2.4, centerY - 0.2);
            cr.lineTo(centerX + 0.2, centerY - 0.2);
            cr.closePath();

            // Contrast bolt: if fill covers the center, dark bolt; otherwise white
            if (fillW >= (centerX - ix + 2.0)) {
                cr.setSourceRGBA(0.08, 0.08, 0.10, 0.95);
            } else {
                cr.setSourceRGBA(1.0, 1.0, 1.0, 1.0);
            }
            cr.fill();
        }

        cr.$dispose();
    }
});

// ─── 5. Right Status Tray (Weather + Spotlight + Clock) ──────
const MacStatusTray = GObject.registerClass(
{ GTypeName: `MacStatusTray_${_uid}` },
class MacStatusTray extends PanelMenu.Button {
    _init(extensionPath) {
        super._init(0.0, 'macOS Status Tray');
        this.add_style_class_name('mac-tray-container');

        this._extensionPath = extensionPath || `${GLib.get_home_dir()}/.local/share/gnome-shell/extensions/macos-menu-bar@Nguyenthanhtam`;

        this.containerBox = new St.BoxLayout({
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'mac-status-box',
        });
        this.add_child(this.containerBox);

        this._icons = {};
        this._upowerClient = null;
        this._upowerDevice = null;
        this._upowerNotifyId = null;
        this._batteryPollTimer = null;

        // 1. Instant zero-delay UI setup with native icons
        this._createIcons();
        this._startClock();
        this._initBattery();

        // Real-time synchronization with Dynamic Island weather state
        this._setupWeatherMonitor();
        this._updateWeatherFromStateFile();

        // 2. Initial background weather refresh by 2s
        this._initTimer = GLib.timeout_add_seconds(GLib.PRIORITY_LOW, 2, () => {
            this._refreshWeatherAsync();
            this._initTimer = null;
            return GLib.SOURCE_REMOVE;
        });

        // 3. Weather update every 15 minutes
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
            track_hover: true,
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
            text: '--°C',
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'mac-weather-label',
        });
        weatherBox.add_child(this._icons.weatherIcon);
        weatherBox.add_child(this._icons.weatherLabel);
        this._icons.weatherBtn.set_child(weatherBox);

        const onWeatherClick = () => {
            runDynamicIsland(['weather-dialog']);
            return Clutter.EVENT_STOP;
        };
        this._icons.weatherBtn.connect('clicked', onWeatherClick);
        this._icons.weatherBtn.connect('button-press-event', onWeatherClick);
        this.containerBox.add_child(this._icons.weatherBtn);

        // 2. Battery Widget (macOS Percentage + Icon)
        this._icons.batteryBtn = new St.Button({
            style_class: 'mac-tray-icon-btn mac-battery-btn',
            reactive: true,
            can_focus: true,
            track_hover: true,
            y_align: Clutter.ActorAlign.CENTER,
        });
        this._icons.batteryBtn.accessible_name = 'Pin (Battery)';

        const batteryBox = new St.BoxLayout({
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'mac-battery-box',
        });

        this._icons.batteryLabel = new St.Label({
            text: '100%',
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'mac-battery-label',
        });

        this._icons.batteryIcon = new MacBatteryWidget();

        batteryBox.add_child(this._icons.batteryLabel);
        batteryBox.add_child(this._icons.batteryIcon);
        this._icons.batteryBtn.set_child(batteryBox);

        this._icons.batteryBtn.connect('notify::hover', () => {
            if (this._icons.batteryIcon && typeof this._icons.batteryIcon.setHover === 'function') {
                this._icons.batteryIcon.setHover(this._icons.batteryBtn.hover);
            }
        });

        this._icons.batteryBtn.connect('button-press-event', (actor, event) => {
            const btn = event.get_button();
            if (btn === 3) {
                runDynamicIsland(['settings', 'battery']);
                return Clutter.EVENT_STOP;
            } else if (btn === 1) {
                runDynamicIsland(['control-center']);
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;
        });
        this.containerBox.add_child(this._icons.batteryBtn);

        // 2b. Control Center Icon Button
        const ccBtn = this._addIconButton('control-center-symbolic', 14, () => {
            runDynamicIsland(['control-center']);
        }, 'Control Center');
        if (ccBtn) {
            ccBtn.add_style_class_name('mac-cc-btn');
            this.containerBox.add_child(ccBtn);
        }

        // 2c. macOS Spotlight Search Icon Button (Magnifying Glass)
        const spotlightBtn = this._addIconButton('system-search-symbolic', 14, () => {
            runDynamicIsland(['spotlight']);
        }, 'Spotlight Search');
        if (spotlightBtn) {
            spotlightBtn.add_style_class_name('mac-spotlight-btn');
            this.containerBox.add_child(spotlightBtn);
        }

        // 3. Date & Time (macOS Compact Style, toggles calendar)
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
    }

    _addIconButton(iconName, size, onClick, tooltipText = null) {
        const btn = new St.Button({
            style_class: 'mac-tray-icon-btn',
            reactive: true,
            can_focus: true,
            track_hover: true,
            y_align: Clutter.ActorAlign.CENTER,
        });
        if (tooltipText) {
            btn.accessible_name = tooltipText;
        }

        let icon = null;
        if (this._extensionPath) {
            const svgName = iconName.endsWith('.svg') ? iconName : `${iconName}.svg`;
            const svgFile = Gio.File.new_for_path(`${this._extensionPath}/${svgName}`);
            if (svgFile.query_exists(null)) {
                icon = new St.Icon({
                    gicon: new Gio.FileIcon({ file: svgFile }),
                    icon_size: size,
                    style_class: 'mac-tray-icon',
                    y_align: Clutter.ActorAlign.CENTER,
                });
            }
        }

        if (!icon) {
            icon = new St.Icon({
                icon_name: iconName,
                icon_size: size,
                style_class: 'mac-tray-icon',
                y_align: Clutter.ActorAlign.CENTER,
            });
        }

        btn.set_child(icon);
        btn._stIcon = icon;
        if (onClick) {
            btn.connect('clicked', () => {
                onClick();
            });
            btn.connect('button-press-event', (actor, event) => {
                const b = event.get_button();
                if (b === 1 || b === 3) {
                    onClick();
                    return Clutter.EVENT_STOP;
                }
                return Clutter.EVENT_PROPAGATE;
            });
        }
        this.containerBox.add_child(btn);
        return btn;
    }

    _getWeatherStateFile() {
        const home = GLib.get_home_dir();
        return Gio.File.new_for_path(`${home}/.config/dynamic_island/weather_state.json`);
    }

    _updateWeatherFromStateFile() {
        try {
            const file = this._getWeatherStateFile();
            if (!file.query_exists(null)) {
                return false;
            }
            file.load_contents_async(null, (f, res) => {
                try {
                    const [ok, contents] = f.load_contents_finish(res);
                    if (ok && contents) {
                        const decoder = new TextDecoder('utf-8');
                        const text = decoder.decode(contents);
                        const data = JSON.parse(text);
                        if (data && data.temp !== undefined) {
                            if (this._icons.weatherLabel) {
                                this._icons.weatherLabel.set_text(`${data.temp}°C`);
                            }
                            if (this._icons.weatherIcon && data.icon_symbolic) {
                                this._icons.weatherIcon.set_icon_name(data.icon_symbolic);
                            }
                        }
                    }
                } catch (err) {}
            });
            return true;
        } catch (e) {
            console.error(`[macOS Menu Bar] Error reading weather state: ${e}`);
        }
        return false;
    }

    _setupWeatherMonitor() {
        try {
            const file = this._getWeatherStateFile();
            this._weatherMonitor = file.monitor_file(Gio.FileMonitorFlags.NONE, null);
            this._weatherMonitor.connect('changed', (mon, f, other, eventType) => {
                if (eventType === Gio.FileMonitorEvent.CHANGES_DONE_HINT ||
                    eventType === Gio.FileMonitorEvent.CREATED ||
                    eventType === Gio.FileMonitorEvent.CHANGED) {
                    this._updateWeatherFromStateFile();
                }
            });
        } catch (e) {
            console.error(`[macOS Menu Bar] Error setting up weather monitor: ${e}`);
        }
    }

    async _refreshWeatherAsync() {
        // 1. Try reading directly from Dynamic Island's synchronized state file
        if (this._updateWeatherFromStateFile()) {
            return;
        }

        // 2. Fallback to wttr.in only if state file is not ready yet
        try {
            const proc = new Gio.Subprocess({
                argv: ['curl', '-s', '--max-time', '2', 'wttr.in/?format=%c%t'],
                flags: Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_MERGE,
            });
            proc.init(null);
            proc.communicate_utf8_async(null, null, (p, res) => {
                try {
                    const [, stdout] = p.communicate_utf8_finish(res);
                    if (stdout && this._icons.weatherLabel) {
                        const clean = stdout.replace(/\+/g, '').trim();
                        if (clean && clean.length <= 10) {
                            this._icons.weatherLabel.set_text(clean);
                        }
                    }
                } catch (e) {}
            });
        } catch (e) {}
    }

    _getFormattedTime() {
        const now = GLib.DateTime.new_now_local();
        const lang = getAppLanguage();
        const date = new Date(
            now.get_year(),
            now.get_month() - 1,
            now.get_day_of_month(),
            now.get_hour(),
            now.get_minute(),
        );

        // Intl supplies weekday/month names and ordering for every locale
        // supported by the user's language setting, including regional tags.
        try {
            return new Intl.DateTimeFormat(lang, {
                weekday: 'short',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                hour12: false,
            }).format(date);
        } catch (e) {
            return new Intl.DateTimeFormat('en', {
                weekday: 'short', month: 'short', day: 'numeric',
                hour: '2-digit', minute: '2-digit', hour12: false,
            }).format(date);
        }
    }

    _startClock() {
        this._clockTimer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1, () => {
            if (this.clockLabel) {
                this.clockLabel.set_text(this._getFormattedTime());
            }
            return GLib.SOURCE_CONTINUE;
        });
    }

    _initBattery() {
        try {
            this._upowerClient = new UPowerGlib.Client();
            this._upowerDevice = this._upowerClient.get_display_device();
            if (this._upowerDevice) {
                this._upowerNotifyId = this._upowerDevice.connect('notify', () => {
                    this._updateBattery();
                });
            }
        } catch (e) {
            console.error(`[macOS Menu Bar] UPower init error: ${e}`);
        }

        // Initial update
        this._updateBattery();

        // 30-second poll fallback
        this._batteryPollTimer = GLib.timeout_add_seconds(GLib.PRIORITY_LOW, 30, () => {
            this._updateBattery();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _updateBattery() {
        if (!this._icons.batteryLabel || !this._icons.batteryIcon) return;

        let pct = 100;
        let isCharging = false;
        let isCharged = true;
        let isPresent = false;

        if (this._upowerDevice) {
            try {
                isPresent = !!this._upowerDevice.is_present;
                const rawPct = this._upowerDevice.percentage;
                const state = this._upowerDevice.state;

                if (isPresent && rawPct > 0) {
                    pct = Math.round(rawPct);
                    isCharging = (state === UPowerGlib.DeviceState.CHARGING || state === 1);
                    isCharged = (state === UPowerGlib.DeviceState.FULLY_CHARGED || state === 4 || (pct >= 99 && isCharging));
                    if (state === UPowerGlib.DeviceState.DISCHARGING || state === 2) {
                        isCharging = false;
                        isCharged = false;
                    }
                } else {
                    // Desktop / VM on AC power
                    pct = 100;
                    isCharging = true;
                    isCharged = true;
                }
            } catch (e) {
                pct = 100;
                isCharging = true;
                isCharged = true;
            }
        }

        this._icons.batteryLabel.set_text(`${pct}%`);

        let tooltip = `Pin: ${pct}%`;
        if (!isPresent) {
            tooltip = `Nguồn điện: Bộ chuyển đổi nguồn AC (${pct}%)`;
        } else if (isCharging) {
            tooltip = `Pin: ${pct}% (Đang sạc)`;
        } else if (isCharged) {
            tooltip = `Pin: ${pct}% (Đã sạc đầy)`;
        } else {
            tooltip = `Pin: ${pct}% (Đang sử dụng pin)`;
        }
        if (this._icons.batteryBtn) {
            this._icons.batteryBtn.accessible_name = tooltip;
        }

        this._setBatteryIcon(pct, isCharging, isCharged, isPresent);
    }

    _setBatteryIcon(pct, isCharging, isCharged, isPresent) {
        if (this._icons.batteryIcon && typeof this._icons.batteryIcon.updateState === 'function') {
            this._icons.batteryIcon.updateState(pct, isCharging, isCharged, isPresent);
            return;
        }

        let targetName = 'mac-battery-charged-symbolic';
        let fallbackName = 'battery-level-100-charged-symbolic';

        if (!isPresent || isCharged) {
            targetName = 'mac-battery-charged-symbolic';
            fallbackName = 'battery-level-100-charged-symbolic';
        } else if (isCharging) {
            targetName = 'mac-battery-charging-symbolic';
            fallbackName = 'battery-level-90-charging-symbolic';
        } else {
            if (pct >= 85) {
                targetName = 'mac-battery-100-symbolic';
                fallbackName = 'battery-level-100-symbolic';
            } else if (pct >= 60) {
                targetName = 'mac-battery-80-symbolic';
                fallbackName = 'battery-level-80-symbolic';
            } else if (pct >= 35) {
                targetName = 'mac-battery-50-symbolic';
                fallbackName = 'battery-level-50-symbolic';
            } else {
                targetName = 'mac-battery-20-symbolic';
                fallbackName = 'battery-level-20-symbolic';
            }
        }

        let setFromSvg = false;
        if (this._extensionPath) {
            const svgFile = Gio.File.new_for_path(`${this._extensionPath}/${targetName}.svg`);
            if (svgFile.query_exists(null)) {
                this._icons.batteryIcon.set_gicon(new Gio.FileIcon({ file: svgFile }));
                setFromSvg = true;
            }
        }
        if (!setFromSvg) {
            this._icons.batteryIcon.set_icon_name(fallbackName);
        }
    }

    destroy() {
        if (this._upowerDevice && this._upowerNotifyId) {
            try {
                this._upowerDevice.disconnect(this._upowerNotifyId);
            } catch (e) {}
            this._upowerNotifyId = null;
        }
        this._upowerDevice = null;
        this._upowerClient = null;

        if (this._batteryPollTimer) {
            GLib.source_remove(this._batteryPollTimer);
            this._batteryPollTimer = null;
        }
        if (this._weatherMonitor) {
            this._weatherMonitor.cancel();
            this._weatherMonitor = null;
        }
        if (this._clockTimer) {
            GLib.source_remove(this._clockTimer);
            this._clockTimer = null;
        }
        if (this._initTimer) {
            GLib.source_remove(this._initTimer);
            this._initTimer = null;
        }
        if (this._weatherTimer) {
            GLib.source_remove(this._weatherTimer);
            this._weatherTimer = null;
        }
        super.destroy();
    }
});

// ─── 6. Extension Handler ────────────────────────────────────
export class MenuHandler {
    constructor(extension) {
        this.extension = extension;
        this._buttons = [];
        this._hiddenIndicators = [];
        this._origShowOsdWindow = null;
        this._language = 'en';
        this._languageMonitor = null;
        this._languageReloadScheduled = false;
    }

    enable() {
        const HOME = GLib.get_home_dir();
        this._language = getAppLanguage();

        // 0. Intercept GNOME Shell native OSD to suppress volume HUD
        // (Volume changes are already displayed on Dynamic Island pill)
        try {
            if (Main.osdWindowManager && !this._origShowOsdWindow) {
                this._origShowOsdWindow = Main.osdWindowManager._showOsdWindow;
                const self = this;
                Main.osdWindowManager._showOsdWindow = function(monitorIndex, icon, label, level, maxLevel) {
                    try {
                        const iconStr = icon ? (icon.to_string ? icon.to_string() : (icon.get_names ? icon.get_names().join(' ') : (icon.name || ''))) : '';
                        const lbl = (label || '').toString().toLowerCase();
                        if (iconStr.includes('audio') || iconStr.includes('volume') || lbl.includes('volume') || lbl.includes('audio')) {
                            // Suppress external volume HUD; Dynamic Island handles it!
                            if (this._osdWindows && this._osdWindows[monitorIndex]) {
                                this._osdWindows[monitorIndex].cancel();
                            }
                            return;
                        }
                    } catch (err) {
                        console.error(`[macOS Menu Bar] OSD intercept error: ${err}`);
                    }
                    return self._origShowOsdWindow.call(this, monitorIndex, icon, label, level, maxLevel);
                };
            }
        } catch (e) {
            console.error(`[macOS Menu Bar] Failed to hook OSD window manager: ${e}`);
        }

        // 0b. Hide default activities so Apple logo is cleanly placed at the very left
        if (Main.panel.statusArea.activities?.container) {
            Main.panel.statusArea.activities.container.visible = false;
            this._hiddenIndicators.push('activities');
        }

        // 0c. Keep macOS Desktop Widgets pinned to desktop below all application windows
        try {
            this._widgetMapSignal = global.window_manager.connect_after('map', (wm, actor) => {
                try {
                    const win = actor.meta_window || (actor.get_meta_window ? actor.get_meta_window() : null);
                    if (win) {
                        const wmClass = (win.get_wm_class ? win.get_wm_class() : '') || '';
                        const role = (win.get_role ? win.get_role() : '') || '';
                        if (wmClass.toLowerCase().includes('desktop-widget') ||
                            wmClass.toLowerCase().includes('desktopwidget') ||
                            role.toLowerCase().includes('desktop-widget')) {
                            win.lower();
                        }
                    }
                } catch (err) {}
            });
        } catch (e) {
            console.error(`[macOS Menu Bar] Failed to connect widget map signal: ${e}`);
        }

        // 1. Apple Logo Menu
        const extPath = this.extension.path || `${HOME}/.local/share/gnome-shell/extensions/macos-menu-bar@Nguyenthanhtam`;
        const appleMenu = new AppleMenu(extPath);
        Main.panel.addToStatusArea('mac-apple-menu', appleMenu, 0, 'left');
        this._buttons.push('mac-apple-menu');

        this._leftIdx = 1;

        // 2. Active Application Menu (Bold App Name) - hidden by default for clean menu bar
        this._showAppName = shouldShowAppName();
        if (this._showAppName) {
            const activeAppMenu = new ActiveAppMenu(this._language);
            Main.panel.addToStatusArea('mac-active-app', activeAppMenu, this._leftIdx++, 'left');
            this._buttons.push('mac-active-app');
        }

        // 3. Global Menus (File, Edit, View, Go, Tools, Help, Search)
        const lang = this._language;
        let menus = [];

        if (lang === 'ja') {
            menus = [
                {
                    id: 'file',
                    title: 'ファイル',
                    items: [
                        { label: '新規ウインドウ', callback: () => spawn(['nautilus', '--new-window']) },
                        { label: '新規ターミナルウインドウ', callback: () => openTerminal() },
                        { label: '新規テキスト書類', callback: () => spawn(['gnome-text-editor']) },
                        null,
                        { label: 'ファイルを開く…', callback: () => spawn(['zenity', '--file-selection']) },
                        { label: 'フォルダを開く…', callback: () => spawn(['nautilus', HOME]) },
                        null,
                        { label: 'ウインドウを閉じる', callback: () => closeActiveWindow() },
                        { label: 'ウインドウをしまう', callback: () => minimizeActiveWindow() },
                    ]
                },
                {
                    id: 'edit',
                    title: '編集',
                    items: [
                        { label: '取り消す', callback: () => sendKey(Clutter.KEY_z || 0x07a, true, false) },
                        { label: 'やり直す', callback: () => sendKey(Clutter.KEY_z || 0x07a, true, true) },
                        null,
                        { label: 'カット', callback: () => sendKey(Clutter.KEY_x || 0x078, true, false) },
                        { label: 'コピー', callback: () => sendKey(Clutter.KEY_c || 0x063, true, false) },
                        { label: 'ペースト', callback: () => sendKey(Clutter.KEY_v || 0x076, true, false) },
                        { label: 'すべてを選択', callback: () => sendKey(Clutter.KEY_a || 0x061, true, false) },
                    ]
                },
                {
                    id: 'view',
                    title: '表示',
                    items: [
                        { label: '再読み込み', callback: () => sendKey(Clutter.KEY_F5 || 0xffc2) },
                        null,
                        { label: '拡大', callback: () => sendKey(Clutter.KEY_plus || 0x02b, true, false) },
                        { label: '縮小', callback: () => sendKey(Clutter.KEY_minus || 0x02d, true, false) },
                        { label: '実際のサイズ (100%)', callback: () => sendKey(Clutter.KEY_0 || 0x030, true, false) },
                        null,
                        { label: 'フルスクリーンにする', callback: () => toggleFullscreenActiveWindow() },
                        { label: '最大化 / 元に戻す', callback: () => toggleMaximizeActiveWindow() },
                    ]
                },
                {
                    id: 'go',
                    title: '移動',
                    items: [
                        { label: 'ホーム', callback: () => spawn(['nautilus', HOME]) },
                        { label: 'デスクトップ', callback: () => spawn(['nautilus', `${HOME}/Desktop`]) },
                        { label: 'ダウンロード', callback: () => spawn(['nautilus', `${HOME}/Downloads`]) },
                        { label: '書類', callback: () => spawn(['nautilus', `${HOME}/Documents`]) },
                        { label: 'ピクチャ', callback: () => spawn(['nautilus', `${HOME}/Pictures`]) },
                        { label: 'ミュージック', callback: () => spawn(['nautilus', `${HOME}/Music`]) },
                        { label: 'ムービー', callback: () => spawn(['nautilus', `${HOME}/Videos`]) },
                        null,
                        { label: 'コンピュータ (Root)', callback: () => spawn(['nautilus', '/']) },
                        { label: 'ネットワーク', callback: () => spawn(['nautilus', 'network:///']) },
                        null,
                        { label: '最近使った項目', callback: () => spawn(['nautilus', 'recent:///']) },
                        { label: 'ゴミ箱', callback: () => spawn(['nautilus', 'trash:///']) },
                    ]
                },
                {
                    id: 'tools',
                    title: 'ツール',
                    items: [
                        { label: 'ターミナル (Ptyxis)', callback: () => openTerminal() },
                        { label: 'アクティビティモニタ (Vitals)', callback: () => openSystemMonitor() },
                        { label: 'テキストエディタ', callback: () => spawn(['gnome-text-editor']) },
                        { label: '計算機', callback: () => spawn(['gnome-calculator']) },
                        { label: 'スクリーンショット', callback: () => openScreenshot() },
                        { label: 'ディスク使用量', callback: () => spawn(['baobab']) },
                        { label: 'システム設定 (macOS Settings)…', callback: () => runDynamicIsland(['settings']) },
                        { label: 'AirDrop (ファイル共有)…', callback: () => runDynamicIsland(['airdrop']) },
                        null,
                        { label: 'Dynamic Islandを展開', callback: () => runDynamicIsland(['expand']) },
                        { label: 'システムリソース (Vitals)', callback: () => runDynamicIsland(['tab', 'vitals']) },
                        { label: 'コントロール (Controls)', callback: () => runDynamicIsland(['tab', 'controls']) },
                        { label: 'ミュージックプレーヤー', callback: () => runDynamicIsland(['tab', 'media']) },
                        { label: 'タイマー & ポモドーロ', callback: () => runDynamicIsland(['tab', 'timer']) },
                        { label: '天気の場所を設定…', callback: () => runDynamicIsland(['weather-dialog']) },
                        null,
                        { label: 'Dynamic Islandを折りたたむ', callback: () => runDynamicIsland(['collapse']) },
                    ]
                },
                {
                    id: 'help',
                    title: 'ヘルプ',
                    items: [
                        { label: 'Dynamic Islandの設定…', callback: () => runDynamicIsland(['settings']) },
                        { label: 'GNOME ヘルプ', callback: () => spawn(['yelp']) },
                        { label: 'キーボードショートカット', callback: () => spawn(['gnome-control-center', 'keyboard']) },
                        { label: 'ディスプレイ設定', callback: () => spawn(['gnome-control-center', 'display']) },
                        { label: 'サウンド設定', callback: () => spawn(['gnome-control-center', 'sound']) },
                        null,
                        { label: 'About macOS Menu Bar', callback: () => spawn(['zenity', '--info', '--title=macOS Menu Bar', '--text=macOS Sonoma/Sequoia Menu Bar for Ubuntu Linux\nDesign & integration by Thanh Tâm.']) },
                        { label: 'About Dynamic Island', callback: () => runDynamicIsland(['settings']) },
                    ]
                },
                {
                    id: 'search',
                    title: '検索',
                    items: [
                        { label: 'アプリを検索 (Spotlight)…', callback: () => runDynamicIsland(['spotlight']) },
                        { label: 'コントロールセンター…', callback: () => runDynamicIsland(['control-center']) },
                        { label: 'ファイル (Nautilus)', callback: () => spawn(['nautilus', HOME]) },
                        { label: 'Googleで検索', callback: () => spawn(['xdg-open', 'https://www.google.com']) },
                        null,
                        { label: 'macOS システム設定…', callback: () => runDynamicIsland(['settings']) },
                    ]
                }
            ];
        } else if (lang === 'vi') {
            menus = [
                {
                    id: 'file',
                    title: 'Tập tin',
                    items: [
                        { label: 'Cửa sổ mới', callback: () => spawn(['nautilus', '--new-window']) },
                        { label: 'Cửa sổ Terminal mới', callback: () => openTerminal() },
                        { label: 'Tệp văn bản mới', callback: () => spawn(['gnome-text-editor']) },
                        null,
                        { label: 'Mở tệp…', callback: () => spawn(['zenity', '--file-selection']) },
                        { label: 'Mở thư mục…', callback: () => spawn(['nautilus', HOME]) },
                        null,
                        { label: 'Đóng cửa sổ', callback: () => closeActiveWindow() },
                        { label: 'Thu nhỏ cửa sổ', callback: () => minimizeActiveWindow() },
                    ]
                },
                {
                    id: 'edit',
                    title: 'Sửa',
                    items: [
                        { label: 'Hoàn tác (Undo)', callback: () => sendKey(Clutter.KEY_z || 0x07a, true, false) },
                        { label: 'Làm lại (Redo)', callback: () => sendKey(Clutter.KEY_z || 0x07a, true, true) },
                        null,
                        { label: 'Cắt (Cut)', callback: () => sendKey(Clutter.KEY_x || 0x078, true, false) },
                        { label: 'Sao chép (Copy)', callback: () => sendKey(Clutter.KEY_c || 0x063, true, false) },
                        { label: 'Dán (Paste)', callback: () => sendKey(Clutter.KEY_v || 0x076, true, false) },
                        { label: 'Chọn tất cả', callback: () => sendKey(Clutter.KEY_a || 0x061, true, false) },
                    ]
                },
                {
                    id: 'view',
                    title: 'Xem',
                    items: [
                        { label: 'Tải lại', callback: () => sendKey(Clutter.KEY_F5 || 0xffc2) },
                        null,
                        { label: 'Phóng to', callback: () => sendKey(Clutter.KEY_plus || 0x02b, true, false) },
                        { label: 'Thu nhỏ', callback: () => sendKey(Clutter.KEY_minus || 0x02d, true, false) },
                        { label: 'Kích thước thực (100%)', callback: () => sendKey(Clutter.KEY_0 || 0x030, true, false) },
                        null,
                        { label: 'Toàn màn hình', callback: () => toggleFullscreenActiveWindow() },
                        { label: 'Phóng cực đại / Phục hồi', callback: () => toggleMaximizeActiveWindow() },
                    ]
                },
                {
                    id: 'go',
                    title: 'Đi',
                    items: [
                        { label: 'Trang chính (Home)', callback: () => spawn(['nautilus', HOME]) },
                        { label: 'Màn hình nền (Desktop)', callback: () => spawn(['nautilus', `${HOME}/Desktop`]) },
                        { label: 'Tải về (Downloads)', callback: () => spawn(['nautilus', `${HOME}/Downloads`]) },
                        { label: 'Tài liệu (Documents)', callback: () => spawn(['nautilus', `${HOME}/Documents`]) },
                        { label: 'Hình ảnh (Pictures)', callback: () => spawn(['nautilus', `${HOME}/Pictures`]) },
                        { label: 'Âm nhạc (Music)', callback: () => spawn(['nautilus', `${HOME}/Music`]) },
                        { label: 'Video', callback: () => spawn(['nautilus', `${HOME}/Videos`]) },
                        null,
                        { label: 'Máy vi tính (Root)', callback: () => spawn(['nautilus', '/']) },
                        { label: 'Máy chủ mạng', callback: () => spawn(['nautilus', 'network:///']) },
                        null,
                        { label: 'Tệp gần đây', callback: () => spawn(['nautilus', 'recent:///']) },
                        { label: 'Thùng rác', callback: () => spawn(['nautilus', 'trash:///']) },
                    ]
                },
                {
                    id: 'tools',
                    title: 'Công cụ',
                    items: [
                        { label: 'Terminal (Ptyxis)', callback: () => openTerminal() },
                        { label: 'Theo dõi hệ thống (Vitals)', callback: () => openSystemMonitor() },
                        { label: 'Trình soạn thảo văn bản', callback: () => spawn(['gnome-text-editor']) },
                        { label: 'Máy tính (Calculator)', callback: () => spawn(['gnome-calculator']) },
                        { label: 'Chụp ảnh & Ghi màn hình', callback: () => openScreenshot() },
                        { label: 'Phân tích bộ nhớ đĩa', callback: () => spawn(['baobab']) },
                        { label: 'Cài đặt hệ thống (macOS Settings)…', callback: () => runDynamicIsland(['settings']) },
                        { label: 'AirDrop (Chia sẻ tệp)…', callback: () => runDynamicIsland(['airdrop']) },
                        null,
                        { label: 'Bung mở Dynamic Island', callback: () => runDynamicIsland(['expand']) },
                        { label: 'Tài nguyên hệ thống (Vitals)', callback: () => runDynamicIsland(['tab', 'vitals']) },
                        { label: 'Bảng điều khiển (Controls)', callback: () => runDynamicIsland(['tab', 'controls']) },
                        { label: 'Trình phát nhạc', callback: () => runDynamicIsland(['tab', 'media']) },
                        { label: 'Đồng hồ đếm giờ & Pomodoro', callback: () => runDynamicIsland(['tab', 'timer']) },
                        { label: 'Cài đặt vị trí thời tiết…', callback: () => runDynamicIsland(['weather-dialog']) },
                        null,
                        { label: 'Ẩn Dynamic Island', callback: () => runDynamicIsland(['collapse']) },
                    ]
                },
                {
                    id: 'help',
                    title: 'Trợ giúp',
                    items: [
                        { label: 'Cài đặt Dynamic Island…', callback: () => runDynamicIsland(['settings']) },
                        { label: 'Trợ giúp GNOME', callback: () => spawn(['yelp']) },
                        { label: 'Phím tắt bàn phím', callback: () => spawn(['gnome-control-center', 'keyboard']) },
                        { label: 'Cài đặt hiển thị', callback: () => spawn(['gnome-control-center', 'display']) },
                        { label: 'Cài đặt âm thanh', callback: () => spawn(['gnome-control-center', 'sound']) },
                        null,
                        { label: 'Giới thiệu macOS Menu Bar', callback: () => spawn(['zenity', '--info', '--title=About macOS Menu Bar', '--text=macOS Sonoma/Sequoia Menu Bar for Ubuntu Linux\nDesign & integration by Thanh Tâm.']) },
                        { label: 'Giới thiệu Dynamic Island', callback: () => runDynamicIsland(['settings']) },
                    ]
                },
                {
                    id: 'search',
                    title: 'Tìm kiếm',
                    items: [
                        { label: 'Tìm kiếm ứng dụng (Spotlight)…', callback: () => runDynamicIsland(['spotlight']) },
                        { label: 'Trung tâm Điều khiển (Control Center)…', callback: () => runDynamicIsland(['control-center']) },
                        { label: 'Quản lý tệp (Nautilus)', callback: () => spawn(['nautilus', HOME]) },
                        { label: 'Tìm kiếm Google trên Web', callback: () => spawn(['xdg-open', 'https://www.google.com']) },
                        null,
                        { label: 'Cài đặt hệ thống macOS…', callback: () => runDynamicIsland(['settings']) },
                    ]
                }
            ];
        } else {
            menus = [
                {
                    id: 'file',
                    title: 'File',
                    items: [
                        { label: 'New Window', callback: () => spawn(['nautilus', '--new-window']) },
                        { label: 'New Terminal Window', callback: () => openTerminal() },
                        { label: 'New Text Document', callback: () => spawn(['gnome-text-editor']) },
                        null,
                        { label: 'Open File…', callback: () => spawn(['zenity', '--file-selection']) },
                        { label: 'Open Folder…', callback: () => spawn(['nautilus', HOME]) },
                        null,
                        { label: 'Close Window', callback: () => closeActiveWindow() },
                        { label: 'Minimize Window', callback: () => minimizeActiveWindow() },
                    ]
                },
                {
                    id: 'edit',
                    title: 'Edit',
                    items: [
                        { label: 'Undo', callback: () => sendKey(Clutter.KEY_z || 0x07a, true, false) },
                        { label: 'Redo', callback: () => sendKey(Clutter.KEY_z || 0x07a, true, true) },
                        null,
                        { label: 'Cut', callback: () => sendKey(Clutter.KEY_x || 0x078, true, false) },
                        { label: 'Copy', callback: () => sendKey(Clutter.KEY_c || 0x063, true, false) },
                        { label: 'Paste', callback: () => sendKey(Clutter.KEY_v || 0x076, true, false) },
                        { label: 'Select All', callback: () => sendKey(Clutter.KEY_a || 0x061, true, false) },
                    ]
                },
                {
                    id: 'view',
                    title: 'View',
                    items: [
                        { label: 'Reload View', callback: () => sendKey(Clutter.KEY_F5 || 0xffc2) },
                        null,
                        { label: 'Zoom In', callback: () => sendKey(Clutter.KEY_plus || 0x02b, true, false) },
                        { label: 'Zoom Out', callback: () => sendKey(Clutter.KEY_minus || 0x02d, true, false) },
                        { label: 'Actual Size (100%)', callback: () => sendKey(Clutter.KEY_0 || 0x030, true, false) },
                        null,
                        { label: 'Toggle Full Screen', callback: () => toggleFullscreenActiveWindow() },
                        { label: 'Maximize / Restore', callback: () => toggleMaximizeActiveWindow() },
                    ]
                },
                {
                    id: 'go',
                    title: 'Go',
                    items: [
                        { label: 'Home', callback: () => spawn(['nautilus', HOME]) },
                        { label: 'Desktop', callback: () => spawn(['nautilus', `${HOME}/Desktop`]) },
                        { label: 'Downloads', callback: () => spawn(['nautilus', `${HOME}/Downloads`]) },
                        { label: 'Documents', callback: () => spawn(['nautilus', `${HOME}/Documents`]) },
                        { label: 'Pictures', callback: () => spawn(['nautilus', `${HOME}/Pictures`]) },
                        { label: 'Music', callback: () => spawn(['nautilus', `${HOME}/Music`]) },
                        { label: 'Videos', callback: () => spawn(['nautilus', `${HOME}/Videos`]) },
                        null,
                        { label: 'Computer (Root)', callback: () => spawn(['nautilus', '/']) },
                        { label: 'Network Servers', callback: () => spawn(['nautilus', 'network:///']) },
                        null,
                        { label: 'Recent Files', callback: () => spawn(['nautilus', 'recent:///']) },
                        { label: 'Trash', callback: () => spawn(['nautilus', 'trash:///']) },
                    ]
                },
                {
                    id: 'tools',
                    title: 'Tools',
                    items: [
                        { label: 'Terminal (Ptyxis)', callback: () => openTerminal() },
                        { label: 'System Monitor (Vitals)', callback: () => openSystemMonitor() },
                        { label: 'Text Editor', callback: () => spawn(['gnome-text-editor']) },
                        { label: 'Calculator', callback: () => spawn(['gnome-calculator']) },
                        { label: 'Screenshot & Screen Recording', callback: () => openScreenshot() },
                        { label: 'Disk Usage Analyzer', callback: () => spawn(['baobab']) },
                        { label: 'System Settings (macOS Settings)…', callback: () => runDynamicIsland(['settings']) },
                        { label: 'AirDrop…', callback: () => runDynamicIsland(['airdrop']) },
                        null,
                        { label: 'Expand Dynamic Island', callback: () => runDynamicIsland(['expand']) },
                        { label: 'System Vitals', callback: () => runDynamicIsland(['tab', 'vitals']) },
                        { label: 'Control Center', callback: () => runDynamicIsland(['tab', 'controls']) },
                        { label: 'Music Player', callback: () => runDynamicIsland(['tab', 'media']) },
                        { label: 'Timer & Pomodoro', callback: () => runDynamicIsland(['tab', 'timer']) },
                        { label: 'Weather Location…', callback: () => runDynamicIsland(['weather-dialog']) },
                        null,
                        { label: 'Collapse Dynamic Island', callback: () => runDynamicIsland(['collapse']) },
                    ]
                },
                {
                    id: 'help',
                    title: 'Help',
                    items: [
                        { label: 'Dynamic Island Settings…', callback: () => runDynamicIsland(['settings']) },
                        { label: 'GNOME Help', callback: () => spawn(['yelp']) },
                        { label: 'Keyboard Shortcuts', callback: () => spawn(['gnome-control-center', 'keyboard']) },
                        { label: 'Display Settings', callback: () => spawn(['gnome-control-center', 'display']) },
                        { label: 'Sound Settings', callback: () => spawn(['gnome-control-center', 'sound']) },
                        null,
                        { label: 'About macOS Menu Bar', callback: () => spawn(['zenity', '--info', '--title=About macOS Menu Bar', '--text=macOS Sonoma/Sequoia Menu Bar for Ubuntu Linux\nDesign & integration by Thanh Tâm.']) },
                        { label: 'About Dynamic Island', callback: () => runDynamicIsland(['settings']) },
                    ]
                },
                {
                    id: 'search',
                    title: 'Search',
                    items: [
                        { label: 'Search Applications (Spotlight)…', callback: () => runDynamicIsland(['spotlight']) },
                        { label: 'Control Center…', callback: () => runDynamicIsland(['control-center']) },
                        { label: 'File Manager (Nautilus)', callback: () => spawn(['nautilus', HOME]) },
                        { label: 'Google Search on Web', callback: () => spawn(['xdg-open', 'https://www.google.com']) },
                        null,
                        { label: 'macOS System Settings…', callback: () => runDynamicIsland(['settings']) },
                    ]
                }
            ];
        }

        // The English menu definition above supplies all callbacks.  Translate
        // its visible labels for Chinese so zh_CN/zh_TW never fall through to
        // a mixed English bar.
        if (lang === 'zh') {
            const zh = {
                File: '文件', Edit: '编辑', View: '显示', Go: '前往',
                Tools: '工具', Help: '帮助', Search: '搜索',
                'New Window': '新建窗口', 'New Terminal Window': '新建终端窗口',
                'New Text Document': '新建文本文档', 'Open File…': '打开文件…',
                'Open Folder…': '打开文件夹…', 'Close Window': '关闭窗口',
                'Minimize Window': '最小化窗口', Undo: '撤销', Redo: '重做',
                Cut: '剪切', Copy: '拷贝', Paste: '粘贴', 'Select All': '全选',
                'Reload View': '重新加载', 'Zoom In': '放大', 'Zoom Out': '缩小',
                'Actual Size (100%)': '实际大小 (100%)', 'Toggle Full Screen': '进入全屏',
                'Maximize / Restore': '最大化 / 还原', Home: '主文件夹', Desktop: '桌面',
                Downloads: '下载', Documents: '文稿', Pictures: '图片', Music: '音乐',
                Videos: '影片', 'Computer (Root)': '电脑 (根目录)', 'Network Servers': '网络',
                'Recent Files': '最近使用', Trash: '废纸篓',
                'Terminal (Ptyxis)': '终端 (Ptyxis)', 'System Monitor (Vitals)': '活动监视器',
                'Text Editor': '文本编辑器', Calculator: '计算器',
                'Screenshot & Screen Recording': '截屏与录屏', 'Disk Usage Analyzer': '磁盘工具',
                'System Settings (macOS Settings)…': '系统设置…', 'AirDrop…': '隔空投送…',
                'Expand Dynamic Island': '展开 Dynamic Island', 'System Vitals': '系统资源',
                'Control Center': '控制中心', 'Music Player': '音乐播放器',
                'Timer & Pomodoro': '计时器与番茄钟', 'Weather Location…': '天气位置…',
                'Collapse Dynamic Island': '收起 Dynamic Island',
                'Dynamic Island Settings…': 'Dynamic Island 设置…', 'GNOME Help': 'GNOME 帮助',
                'Keyboard Shortcuts': '键盘快捷键', 'Display Settings': '显示器设置',
                'Sound Settings': '声音设置', 'About macOS Menu Bar': '关于 macOS 菜单栏',
                'About Dynamic Island': '关于 Dynamic Island', 'Search Applications (Spotlight)…': '搜索应用程序 (Spotlight)…',
                'Search Applications…': '搜索应用程序 (Spotlight)…',
                'Control Center…': '控制中心…', 'File Manager (Nautilus)': '文件管理器 (Nautilus)',
                'Google Search on Web': '在网页上搜索 Google', 'macOS System Settings…': 'macOS 系统设置…',
            };
            for (const menu of menus) {
                menu.title = zh[menu.title] || menu.title;
                for (const item of menu.items) {
                    if (item && item.label) item.label = zh[item.label] || item.label;
                }
            }
        }

        for (const m of menus) {
            const btn = new MacMenuButton(m.title, m.items);
            const id = `mac-menu-${m.id || m.title.toLowerCase()}`;
            Main.panel.addToStatusArea(id, btn, this._leftIdx++, 'left');
            this._buttons.push(id);
        }

        // Center capsule omitted to maintain sleek, uncluttered spacing

        // 3. Clear center space so panel remains clean and open
        if (Main.panel.statusArea.dateMenu?.container) {
            Main.panel.statusArea.dateMenu.container.visible = false;
            this._hiddenIndicators.push('dateMenu');
        }

        // 4. Right Status Tray (Weather, Control Center, Clock)
        const rightTray = new MacStatusTray(extPath);
        Main.panel.addToStatusArea('mac-right-tray', rightTray, 0, 'right');
        this._buttons.push('mac-right-tray');

        this._watchLanguageConfig();
    }

    _watchLanguageConfig() {
        if (this._languageMonitor) return;
        try {
            const config = Gio.File.new_for_path(
                `${GLib.get_home_dir()}/.config/dynamic_island/config.json`
            );
            this._languageMonitor = config.monitor_file(Gio.FileMonitorFlags.NONE, null);
            this._languageMonitor.connect('changed', () => {
                const next = getAppLanguage();
                const nextShowAppName = shouldShowAppName();
                if ((next === this._language && nextShowAppName === this._showAppName) || this._languageReloadScheduled) return;
                this._languageReloadScheduled = true;
                // Recreate the panel actors on the shell main loop. This keeps
                // callbacks and popup menus in sync with the new locale and config.
                GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
                    if (!this._languageReloadScheduled) return GLib.SOURCE_REMOVE;
                    this._languageReloadScheduled = false;
                    this.disable();
                    this.enable();
                    return GLib.SOURCE_REMOVE;
                });
            });
        } catch (e) {
            console.error(`[macOS Menu Bar] Language monitor error: ${e}`);
        }
    }

    disable() {
        if (this._languageMonitor) {
            try { this._languageMonitor.cancel(); } catch (e) {}
            this._languageMonitor = null;
        }
        this._languageReloadScheduled = false;
        // Restore native OSD window manager hook
        if (this._origShowOsdWindow && Main.osdWindowManager) {
            Main.osdWindowManager._showOsdWindow = this._origShowOsdWindow;
            this._origShowOsdWindow = null;
        }

        // Restore hidden indicators
        for (const id of this._hiddenIndicators) {
            if (Main.panel.statusArea[id]?.container) {
                Main.panel.statusArea[id].container.visible = true;
            }
        }
        this._hiddenIndicators = [];

        if (this._widgetMapSignal) {
            try { global.window_manager.disconnect(this._widgetMapSignal); } catch (e) {}
            this._widgetMapSignal = null;
        }

        // Destroy added buttons
        for (const id of this._buttons) {
            if (Main.panel.statusArea[id]) {
                Main.panel.statusArea[id].destroy();
            }
        }
        this._buttons = [];
    }
}
