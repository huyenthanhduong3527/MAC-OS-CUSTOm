import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';

export default class MacOSMenuBarExtension extends Extension {
    async enable() {
        const uri = `${this.dir.get_uri()}/menu.js?t=${Date.now()}`;
        const module = await import(uri);
        this._handler = new module.MenuHandler(this);
        this._handler.enable();
    }

    disable() {
        if (this._handler) {
            this._handler.disable();
            this._handler = null;
        }
    }
}
