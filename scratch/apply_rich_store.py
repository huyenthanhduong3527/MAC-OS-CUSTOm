import re

target_file = "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/src/ui/macos_appstore_window.py"
with open(target_file, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update _build_discover_page with multiple rich sections
old_discover_func = '''    def _build_discover_page(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_start(28)
        box.set_margin_end(28)
        box.set_margin_bottom(36)
        scrolled.add(box)

        # Hero Banner
        hero_apps = [a for a in APP_CATALOG if a.get("hero")]
        if hero_apps:
            hero_card = self._create_hero_card(hero_apps[0])
            box.pack_start(hero_card, False, False, 4)

        # Essential Apps
        sec_title = Gtk.Label(label="Essential Mac Apps")
        sec_title.get_style_context().add_class("mac-section-title")
        sec_title.set_xalign(0.0)
        box.pack_start(sec_title, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)

        for i, app in enumerate(APP_CATALOG[:6]):
            card = AppCardWidget(app, self.show_app_detail, self.handle_install_or_launch)
            grid.attach(card, i % 2, i // 2, 1, 1)

        box.pack_start(grid, False, False, 0)
        self.stack.add_named(scrolled, "discover")'''

new_discover_func = '''    def _create_app_grid_section(self, title: str, subtitle: Optional[str], app_list: List[Dict[str, Any]]) -> Gtk.Box:
        sec_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        sec_box.set_margin_top(8)

        lbl_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        sec_title = Gtk.Label(label=title)
        sec_title.get_style_context().add_class("mac-section-title")
        sec_title.set_xalign(0.0)
        lbl_box.pack_start(sec_title, False, False, 0)

        if subtitle:
            sec_sub = Gtk.Label(label=subtitle)
            sec_sub.get_style_context().add_class("mac-app-subtitle")
            sec_sub.set_xalign(0.0)
            lbl_box.pack_start(sec_sub, False, False, 0)

        sec_box.pack_start(lbl_box, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)

        for i, app in enumerate(app_list):
            card = AppCardWidget(app, self.show_app_detail, self.handle_install_or_launch)
            grid.attach(card, i % 2, i // 2, 1, 1)

        sec_box.pack_start(grid, False, False, 0)
        return sec_box

    def _build_discover_page(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_margin_start(28)
        box.set_margin_end(28)
        box.set_margin_bottom(48)
        scrolled.add(box)

        # 1. Hero Banner
        hero_apps = [a for a in APP_CATALOG if a.get("hero")]
        if hero_apps:
            hero_card = self._create_hero_card(hero_apps[0])
            box.pack_start(hero_card, False, False, 4)

        # Helper mapping by ID
        app_map = {a["id"]: a for a in APP_CATALOG}

        # 2. Essential Mac Apps (8 apps)
        essential_ids = ["code", "google-chrome", "telegram-desktop", "spotify", "discord", "vlc", "obsidian", "postman"]
        essential_apps = [app_map[aid] for aid in essential_ids if aid in app_map]
        if essential_apps:
            box.pack_start(self._create_app_grid_section("Essential Mac Apps", "Must-have applications for your everyday workflow", essential_apps), False, False, 0)

        # 3. Trending & Popular (8 apps)
        trending_ids = ["blender", "gimp", "steam", "inkscape", "kdenlive", "audacity", "brave", "beekeeper-studio"]
        trending_apps = [app_map[aid] for aid in trending_ids if aid in app_map]
        if trending_apps:
            box.pack_start(self._create_app_grid_section("Trending & Popular", "Great apps loved by Linux and Mac users worldwide", trending_apps), False, False, 0)

        # 4. Creative Studio & Design (6 apps)
        creative_ids = ["blender", "krita", "inkscape", "darktable", "shotcut", "freecad"]
        creative_apps = [app_map[aid] for aid in creative_ids if aid in app_map]
        if creative_apps:
            box.pack_start(self._create_app_grid_section("Creative Studio & Design", "Pro tools for digital art, 3D modeling and video editing", creative_apps), False, False, 0)

        # 5. Developer Power Tools (6 apps)
        dev_ids = ["cursor", "pycharm-community", "docker", "android-studio", "sublime-text", "dbeaver-ce"]
        dev_apps = [app_map[aid] for aid in dev_ids if aid in app_map]
        if dev_apps:
            box.pack_start(self._create_app_grid_section("Developer Tools", "Code faster, debug smarter, build better with top IDEs", dev_apps), False, False, 0)

        # 6. Productivity & Collaboration (6 apps)
        prod_ids = ["libreoffice", "notion-snap-reborn", "slack", "zoom-client", "bitwarden", "keepassxc"]
        prod_apps = [app_map[aid] for aid in prod_ids if aid in app_map]
        if prod_apps:
            box.pack_start(self._create_app_grid_section("Productivity & Collaboration", "Keep work organized, stay focused, and collaborate with your team", prod_apps), False, False, 0)

        # 7. Games & Entertainment (6 apps)
        game_ids = ["steam", "0ad", "supertuxkart", "retroarch", "clementine", "vlc"]
        game_apps = [app_map[aid] for aid in game_ids if aid in app_map]
        if game_apps:
            box.pack_start(self._create_app_grid_section("Games & Entertainment", "Sit back, play high-speed racing & strategy games, or enjoy lossless music", game_apps), False, False, 0)

        self.stack.add_named(scrolled, "discover")'''

if old_discover_func in text:
    text = text.replace(old_discover_func, new_discover_func, 1)
    print("1. Replaced _build_discover_page successfully")
else:
    print("WARNING: old_discover_func not found!")

# 2. Update _build_category_pages with richer app selections
old_cat_pages = '''        categories = [
            ("arcade", "Arcade", ["steam"]),
            ("create", "Create", ["blender", "gimp", "inkscape", "kdenlive"]),
            ("work", "Work", ["trello", "omnifocus", "noted", "slack", "obsidian"]),
            ("develop", "Develop", ["code", "cursor", "pycharm-community", "docker", "postman", "dbeaver-ce"]),
            ("play", "Play", ["spotify", "vlc", "steam", "discord"]),
        ]'''

new_cat_pages = '''        categories = [
            ("arcade", "Arcade", ["steam", "0ad", "supertuxkart", "retroarch"]),
            ("create", "Create", ["blender", "gimp", "inkscape", "krita", "kdenlive", "audacity", "shotcut", "freecad", "darktable"]),
            ("work", "Work", ["libreoffice", "obsidian", "notion-snap-reborn", "slack", "zoom-client", "trello", "joplin-desktop", "thunderbird", "postman"]),
            ("develop", "Develop", ["code", "cursor", "pycharm-community", "docker", "postman", "dbeaver-ce", "android-studio", "sublime-text", "beekeeper-studio"]),
            ("play", "Play", ["spotify", "vlc", "discord", "steam", "clementine", "audacity"]),
        ]'''

if old_cat_pages in text:
    text = text.replace(old_cat_pages, new_cat_pages, 1)
    print("2. Replaced categories list in _build_category_pages")
else:
    print("WARNING: old_cat_pages not found!")

# 3. Update _on_category_clicked to asynchronously fetch real snapd apps for any category
old_cat_clicked = '''    def _on_category_clicked(self, cat_id: str, cat_name: str):
        matched = [a for a in EDITORS_CHOICE_APPS + APP_CATALOG if a.get("category") == cat_id or cat_id in a.get("category", "")]
        if not matched:
            matched = [a for a in APP_CATALOG if a.get("category") == cat_id]
        if not matched:
            matched = APP_CATALOG[:8]
        self._show_filtered_category_view(cat_id, cat_name, matched)'''

new_cat_clicked = '''    def _on_category_clicked(self, cat_id: str, cat_name: str):
        matched = [a for a in EDITORS_CHOICE_APPS + APP_CATALOG if a.get("category") == cat_id or cat_id in a.get("category", "")]
        if not matched:
            matched = [a for a in APP_CATALOG if a.get("category") == cat_id]
        if not matched:
            matched = [a for a in APP_CATALOG if cat_id in a.get("category_name", "").lower() or cat_id in a.get("subtitle", "").lower()]
        if not matched:
            matched = APP_CATALOG[:8]
        self._show_filtered_category_view(cat_id, cat_name, matched)

        # Asynchronously fetch real packages from local snapd socket
        snapd_sec = CAT_TO_SNAPD_SECTION.get(cat_id)
        if snapd_sec:
            def _fetch():
                extra_apps = query_snapd_apps(section=snapd_sec, limit=16)
                if extra_apps:
                    GLib.idle_add(self._append_category_apps, cat_id, extra_apps)
            threading.Thread(target=_fetch, daemon=True).start()

    def _append_category_apps(self, cat_id: str, extra_apps: List[Dict[str, Any]]):
        if not hasattr(self, "category_subpage_grid"):
            return
        existing_ids = {a.get("id") for a in self.current_category_apps}
        idx = len(self.current_category_apps)
        for app in extra_apps:
            if app["id"] in existing_ids:
                continue
            existing_ids.add(app["id"])
            self.current_category_apps.append(app)
            card = AppCardWidget(app, self.show_app_detail, self.handle_install_or_launch)
            card.show_all()
            self.category_subpage_grid.attach(card, idx % 2, idx // 2, 1, 1)
            idx += 1'''

if old_cat_clicked in text:
    text = text.replace(old_cat_clicked, new_cat_clicked, 1)
    print("3. Replaced _on_category_clicked and added _append_category_apps")
else:
    print("WARNING: old_cat_clicked not found!")

# Also update _show_filtered_category_view to store category_subpage_grid and current_category_apps
old_subpage_grid = '''        grid = Gtk.Grid()
        grid.set_column_spacing(24)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)

        for i, app in enumerate(apps):
            card = AppCardWidget(app, self.show_app_detail, self.handle_install_or_launch)
            grid.attach(card, i % 2, i // 2, 1, 1)

        self.category_subpage_box.pack_start(grid, False, False, 0)'''

new_subpage_grid = '''        grid = Gtk.Grid()
        grid.set_column_spacing(24)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)
        self.category_subpage_grid = grid
        self.current_category_apps = list(apps)

        for i, app in enumerate(apps):
            card = AppCardWidget(app, self.show_app_detail, self.handle_install_or_launch)
            grid.attach(card, i % 2, i // 2, 1, 1)

        self.category_subpage_box.pack_start(grid, False, False, 0)'''

if old_subpage_grid in text:
    text = text.replace(old_subpage_grid, new_subpage_grid, 1)
    print("4. Replaced grid setup in _show_filtered_category_view")
else:
    print("WARNING: old_subpage_grid not found!")

# 4. Update handle_install_or_launch to support classic confinement retry and web_url launcher creation
old_install_handler = '''        def _do_install():
            success = False
            snap_name = app.get("snap")
            apt_name = app.get("apt")

            if snap_name:
                try:
                    res = subprocess.run(["pkexec", "snap", "install", snap_name], capture_output=True, text=True)
                    if res.returncode == 0:
                        success = True
                except Exception:
                    pass

            if not success and apt_name:
                try:
                    res = subprocess.run(["pkexec", "apt", "install", "-y", apt_name], capture_output=True, text=True)
                    if res.returncode == 0:
                        success = True
                except Exception:
                    pass

            if not success and not snap_name and not apt_name:
                time.sleep(1.5)
                success = True

            GLib.idle_add(self._on_install_finished, app, card_widget, success)'''

new_install_handler = '''        def _do_install():
            success = False
            snap_name = app.get("snap")
            apt_name = app.get("apt")
            web_url = app.get("web_url")

            if snap_name:
                try:
                    cmd = ["pkexec", "snap", "install"]
                    if app.get("classic") or app.get("confinement") == "classic":
                        cmd.append("--classic")
                    cmd.append(snap_name)
                    res = subprocess.run(cmd, capture_output=True, text=True)
                    if res.returncode == 0:
                        success = True
                    elif "--classic" in res.stderr and "--classic" not in cmd:
                        res2 = subprocess.run(["pkexec", "snap", "install", "--classic", snap_name], capture_output=True, text=True)
                        if res2.returncode == 0:
                            success = True
                except Exception:
                    pass

            if not success and apt_name:
                try:
                    res = subprocess.run(["pkexec", "apt", "install", "-y", apt_name], capture_output=True, text=True)
                    if res.returncode == 0:
                        success = True
                except Exception:
                    pass

            if not success and web_url:
                try:
                    app_id = app.get("id")
                    name = app.get("name")
                    icon_path = os.path.join(APP_ICONS_DIR, f"{app_id}.png")
                    desktop_path = os.path.expanduser(f"~/.local/share/applications/{app_id}.desktop")
                    exec_str = f"google-chrome --app={web_url}" if shutil.which("google-chrome") else f"xdg-open {web_url}"
                    desktop_content = f"""[Desktop Entry]
Name={name}
Comment={app.get('subtitle', name)}
Exec={exec_str}
Icon={icon_path}
Terminal=false
Type=Application
Categories=Network;WebBrowser;
StartupWMClass={app_id}
"""
                    with open(desktop_path, "w") as f:
                        f.write(desktop_content)
                    os.chmod(desktop_path, 0o755)
                    subprocess.run(["update-desktop-database", os.path.expanduser("~/.local/share/applications/")], capture_output=True)
                    success = True
                except Exception:
                    pass

            GLib.idle_add(self._on_install_finished, app, card_widget, success)'''

if old_install_handler in text:
    text = text.replace(old_install_handler, new_install_handler, 1)
    print("5. Replaced handle_install_or_launch with real installer and web-app launcher")
else:
    print("WARNING: old_install_handler not found!")

with open(target_file, "w", encoding="utf-8") as f:
    f.write(text)

print("ALL RICH STORE ENHANCEMENTS APPLIED SUCCESSFULLY!")
