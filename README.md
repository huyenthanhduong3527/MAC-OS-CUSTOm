<a id="top"></a>
<div align="center">

# 🏝️ Dynamic Island & macOS System Suite for Ubuntu Linux
### 🇻🇳 Apple Dynamic Island 60 FPS, Thanh Menu macOS, Bộ Widget Desktop, Hình Nền Động 4K & macOS Terminal Động
### 🇬🇧 *Apple-Grade 60 FPS Dynamic Island, macOS Menu Bar, Desktop Widgets, 4K Live Wallpaper & Dynamic macOS Terminal*

[![Ubuntu](https://img.shields.io/badge/Ubuntu-22.04%20|%2024.04%20|%2026.04-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)](https://ubuntu.com)
[![GNOME](https://img.shields.io/badge/GNOME-Shell%2042%20--%2050-4a86cf?style=for-the-badge&logo=gnome&logoColor=white)](https://www.gnome.org)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![GTK](https://img.shields.io/badge/GUI-GTK3%20%2B%20Cairo-4B275F?style=for-the-badge)](https://www.gtk.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)

<br>

### 🌐 CHỌN NGÔN NGỮ ĐỌC / SELECT DOCUMENTATION LANGUAGE

<p align="center">
  <a href="#vietnamese-guide">
    <img src="https://img.shields.io/badge/🇻🇳%20Tài%20Liệu-Tiếng%20Việt%20(Bấm%20xem)-E95420?style=for-the-badge&logo=vietnam&logoColor=white" alt="Tiếng Việt">
  </a>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <a href="#english-guide">
    <img src="https://img.shields.io/badge/🇬🇧%20Documentation-English%20(Click%20here)-007ACC?style=for-the-badge&logo=google-translate&logoColor=white" alt="English">
  </a>
</p>

**[👉 🇻🇳 Nhấp vào đây để xem bản TIẾNG VIỆT](#vietnamese-guide)** &nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; **[👉 🇬🇧 Click here to read in ENGLISH](#english-guide)**

---

</div>

<br>

<a id="vietnamese-guide"></a>

# 🇻🇳 BẢN HƯỚNG DẪN TIẾNG VIỆT

> **Biến Ubuntu của bạn thành giao diện Apple macOS hoàn mỹ:** 100% Modular linh hoạt — Cài cái bạn muốn, xóa cái bạn không cần.

<div align="center">

[⚡ Cài Đặt](#vi-installation) • [🧩 Cài Từng Phần](#vi-modular) • [🚀 Sử Dụng](#vi-usage) • [🗑️ Gỡ Bỏ (rm)](#vi-uninstall) • [⌨️ Bảng Lệnh CLI](#vi-cli) • [🔧 Xử Lý Sự Cố](#vi-troubleshooting) • [📂 Cấu Trúc Mã Nguồn](#vi-structure) • [🇬🇧 Chuyển Sang Tiếng Anh](#english-guide)

</div>

---

## 📖 Giới Thiệu Tổng Quan (Tiếng Việt)

Hệ thống được thiết kế theo kiến trúc **Module độc lập (Standalone & Modular)** gồm 6 thành phần chính:

1. **🏝️ Dynamic Island:**
   - Đảo thông minh OLED 60 FPS vẽ mượt mà bằng Cairo và GTK, bắt nhạc MPRIS2 & PipeWire, hiển thị Visualizer sóng âm thời gian thực.
   - Theo dõi tài nguyên phần cứng (CPU, RAM, Pin, Nhiệt độ), thanh trượt âm lượng và độ sáng tự động ẩn OSD mặc định của GNOME.
   - Hẹn giờ Pomodoro, Clipboard lịch sử sao chép và trợ lý ảo thông minh Siri / Gemini AI.

2. **🍏 macOS Menu Bar:**
   - GNOME Shell Extension mang thanh menu Apple , tên ứng dụng đang mở in đậm (Active App), Global Menus (File, Edit, View, Window, Help).
   - Biểu tượng Dynamic Island ở giữa cho phép click bật/tắt nhanh đảo.
   - Khay thời tiết thực tế, Spotlight Search (🔍), đồng hồ lịch và Trung tâm điều khiển (Control Center).

3. **🖥️ Bộ Widgets Màn Hình Desktop:**
   - Kéo thả tự do trên màn hình: Lịch Dương & Âm Lịch Việt Nam (chuẩn thuật toán thiên văn Hồ Ngọc Đức), Thời Tiết Apple Weather.
   - Vòng Năng Lượng Pin 4 Thiết Bị (Laptop, AirPods, Case, Chuột), Đồng Hồ Kim macOS, Trình Phát Nhạc Apple Music, Đồng Hồ Thứ & Ngày, Khung Ảnh Ghim Màn Hình.
   - Tọa độ widget tự động lưu lại sau mỗi lần kéo thả và khởi động lại máy.

4. **📦 Bộ Ứng Dụng Chuẩn macOS:**
   - macOS Sequoia App Store (Kho ứng dụng Snap / Flatpak / APT).
   - Apple Notes (Ghi chú phong phú), Apple Photos & Trình biên tập ảnh.
   - Cài đặt Hệ thống (macOS Settings), AirDrop chia sẻ tệp nội bộ qua WiFi/LAN.
   - Photo Booth & Camera Ảo Linux (`v4l2loopback`), Trình cài đặt gói `.deb` chuẩn Apple.

5. **🎬 Hình Nền Động (Live Wallpaper Engine):**
   - Động cơ phát video nền 4K/1080p 60 FPS siêu mượt, tối ưu CPU cực thấp.
   - Hỗ trợ giao diện đồ họa chọn video bằng chuột (GUI) và đổi video tức thì.

6. **⚡ macOS Pro Terminal & Hiệu Ứng Gõ Phím Động:**
   - Giao diện Terminal Ptyxis mờ kính Tokyo Night (Frosted Glass 88% opacity), font lập trình viên `MesloLGS NF`, Shell Zsh & Oh My Zsh theme Agnoster.
   - **Hiệu ứng gõ phím Neon Cyan (`#00f0ff`):** Con trỏ đổi sang dạng thanh đứng tia sáng (I-beam) kèm nhãn `⚡ typing` động ở góc phải RPROMPT và tô màu cú pháp thời gian thực.
   - **Hiệu ứng xóa phím Ruby Red (`#ff2a6d`):** Khi bấm `Backspace`, `Delete` hoặc `Ctrl + W` / `Alt + Backspace`, con trỏ nhấp nháy khối vuông đỏ kèm nhãn `⌫ delete` hoặc `✂ cut`.
   - **Hiển thị mật khẩu sudo (`pwfeedback`):** Hiển thị các dấu sao `****` sinh động khi nhập hoặc xóa mật khẩu trong lệnh `sudo`.
   - **Màn hình chào Hacker Matrix Splash:** Hiệu ứng mưa mã số xanh Matrix lướt qua trong 0.85s cực ngầu kèm lời chào Typewriter `⚡ [SYSTEM READY] Xin chào, <Tên người dùng>!`.
   - **Fastfetch Specs:** Gõ `apple` hoặc `fetch` để hiển thị logo và thông số CPU, GPU, RAM, OS chuẩn macOS/Linux.

> [!TIP]
> **Bạn hoàn toàn làm chủ hệ thống:** Muốn cài đặt thành phần nào, chỉ cần dùng lệnh cài đặt của thành phần đó. Khi muốn xóa bỏ thành phần nào, chỉ cần dùng lệnh xóa của thành phần đó mà không làm ảnh hưởng đến các phần còn lại!

---

<a id="vi-installation"></a>

## ⚡ 1. Hướng Dẫn Cài Đặt (Tiếng Việt)

Trước tiên, mở **Terminal** (`Ctrl + Alt + T`) và tải mã nguồn về máy:

```bash
# 1. Tải repository về máy
git clone https://github.com/huyenthanhduong3527/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX.git

# 2. Di chuyển vào thư mục dự án
cd DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX

# 3. Cấp quyền thực thi cho các file kịch bản
chmod +x install.sh uninstall.sh rm.sh run.sh main.py install_theme.sh scripts/*.sh scripts/*.py
```

---

### Cách A: Cài đặt TẤT CẢ trọn gói (Khuyên Dùng)

Cài đặt toàn bộ 6 thành phần cùng lúc chỉ với 1 dòng lệnh:

```bash
./install.sh all
```
*(Nếu bạn chỉ gõ `./install.sh`, hệ thống sẽ hiển thị menu tương tác dạng số từ 1 đến 7 để bạn tùy ý lựa chọn).*

---

<a id="vi-modular"></a>

### Cách B: Cài Đặt Từng Thành Phần Riêng Lẻ (Modular)

Người dùng muốn cài đặt thành phần nào chỉ cần chạy lệnh của thành phần đó:

| Thành phần | Lệnh cài đặt | Mô tả chi tiết |
| :--- | :--- | :--- |
| **🚀 Cài TẤT CẢ** | `./install.sh all` | Cài toàn bộ 6 thành phần hoàn chỉnh với đầy đủ mọi tính năng. |
| **🏝️ Dynamic Island** | `./install.sh island` | Cài ứng dụng Đảo thông minh, icon vector, tự khởi động cùng máy, ẩn thanh âm lượng mặc định của GNOME. |
| **🍏 macOS Menu Bar** | `./install.sh menubar` | Cài đặt GNOME Shell Extension tạo thanh menu Apple , Global Menu và Control Center ở mép trên màn hình. |
| **🖥️ Widgets Desktop** | `./install.sh widgets` | Cài đặt bộ Widget Desktop (Lịch âm, Thời tiết, Pin 4 vòng, Đồng hồ, Nhạc) và cấu hình chống viền mờ vuông. |
| **📦 Các App macOS** | `./install.sh apps` | Đăng ký các ứng dụng: App Store, Ghi chú, Ảnh, Cài đặt macOS, AirDrop, Photo Booth, Trình cài `.deb`. |
| **🎬 Hình Nền Động** | `./install.sh wallpaper` | Cài đặt động cơ Live Wallpaper 60 FPS, tạo lệnh `live-wallpaper` và shortcut chọn video trong menu ứng dụng. |
| **⚡ Terminal & Typing FX** | `./install.sh terminal`<br>*(hoặc `./install_theme.sh`)* | Cài đặt Zsh, Oh My Zsh, Agnoster, Ptyxis Tokyo Night mờ kính, hiệu ứng gõ Neon Cyan & xóa Ruby Red, sao mật khẩu sudo, Matrix splash. |

---

<a id="vi-usage"></a>

## 🚀 2. Hướng Dẫn Sử Dụng Chi Tiết (Tiếng Việt)

### 1. 🏝️ Dynamic Island (Đảo Thông Minh)

#### Cách khởi chạy:
- **Từ Menu ứng dụng:** Nhấn phím `Super` (Windows) -> tìm **Dynamic Island** -> Nhấp để mở.
- **Từ Terminal:** `./run.sh`
- **Khởi động cùng máy:** Tự động mở mỗi khi bạn bật máy hoặc đăng nhập.

#### Thao tác chuột trực quan:
- **Click chuột trái vào viên thuốc:** Mở rộng thành **Hub điều khiển đa năng** (Media, Vitals, Controls, Timer, Notifications, Settings, AI Siri/Gemini, Clipboard).
- **Click chuột trái vào mép trên Hub:** Thu nhỏ đảo trở lại dạng viên thuốc gọn gàng.
- **Click chuột phải vào viên thuốc:** Mở menu ngữ cảnh nhanh để nhảy thẳng vào từng tab hoặc thoát ứng dụng.
- **Nhấn phím Volume hoặc Chuyển bài:** Viên thuốc tự động mở rộng hiển thị Capsule âm lượng/bài hát rồi tự thu nhỏ sau 3.5 giây.

---

### 2. 🍏 macOS Menu Bar (Thanh Menu Trên Cùng)

Sau khi chạy `./install.sh menubar` (hoặc `all`):
- **Đăng xuất (Log Out) và Đăng nhập lại** tài khoản Ubuntu để GNOME Shell kích hoạt Extension.
- **Các thành phần trên thanh Menu:**
  - ** Apple Menu (Góc trái):** Thông tin hệ thống (About), Cài đặt hệ thống, Khóa màn hình, Sleep, Khởi động lại, Tắt máy.
  - **Active App Menu & Global Menus:** Tên ứng dụng đang mở in đậm kèm File, Edit, View, Window, Help.
  - **🏝️ Island Icon (Ở giữa):** Click chuột trái để xem phím tắt; click chuột phải để Bật / Tắt ẩn hiện Dynamic Island nhanh chóng.
  - **Khay trạng thái (Góc phải):** Thời tiết thực tế, Spotlight Search (🔍), Đồng hồ & Lịch macOS, Trung tâm điều khiển (Control Center).

---

### 3. 🖥️ Bộ Widgets Màn Hình Desktop

Các widget có thể hiển thị tự động cùng Dynamic Island hoặc khởi chạy riêng lẻ:

```bash
# Khởi chạy toàn bộ widget lên Desktop
./run.sh --widgets

# Khởi chạy riêng lẻ từng widget độc lập:
./run.sh --calendar        # Widget Lịch & Âm Lịch Việt Nam (Lunar Calendar)
./run.sh --weather         # Widget Thời Tiết Apple Weather
./run.sh --battery         # Widget Pin 4 Vòng Thiết Bị (4-Ring Battery Gauge)
./run.sh --clock           # Widget Đồng Hồ Kim macOS (Analog Clock)
./run.sh --music-widget    # Widget Trình Phát Nhạc Apple Music
./run.sh --photo           # Widget Khung Ảnh Ghim Màn Hình (Pinned Photo)
./run.sh --weekday-clock   # Widget Đồng Hồ Thứ & Ngày (Weekday Clock)
```

> [!TIP]
> **Kéo thả tự do:** Dùng chuột kéo thả widget đến bất kỳ vị trí nào trên Desktop. Vị trí sẽ tự động được lưu lại cho các lần khởi động tiếp theo!

---

### 4. 📦 Các App Chuẩn macOS

Mở trực tiếp từ menu ứng dụng Ubuntu hoặc qua dòng lệnh Terminal:

```bash
./run.sh --appstore        # macOS Sequoia App Store (Kho ứng dụng)
./run.sh --notes           # Apple Notes (Ghi chú phong phú)
./run.sh --photos          # Apple Photos & Trình biên tập ảnh
./run.sh --settings        # macOS System Settings (Cài đặt hệ thống)
./run.sh --airdrop         # Apple AirDrop (Chia sẻ tệp qua mạng LAN/WiFi)
./run.sh --photobooth      # Photo Booth & Camera Ảo
./run.sh --install-deb app.deb   # Trình cài đặt gói .deb chuẩn Apple
```

---

### 5. 🎬 Hình Nền Động (Live Wallpaper Engine)

Hỗ trợ phát video 1080p / 4K với tần số quét 60 FPS:

```bash
# Khởi động hình nền động chạy ngầm
live-wallpaper start
# Hoặc lệnh python:
python3 scripts/live_wallpaper.py start

# Dừng hình nền động (quay về hình nền tĩnh của Ubuntu)
live-wallpaper stop

# Xem trạng thái đang chạy hay tắt
live-wallpaper status

# Mở hộp thoại chọn video trực quan bằng chuột
live-wallpaper choose

# Đặt video tùy thích theo đường dẫn
live-wallpaper set assets/wallpapers/sakura_torii_4k_live.mp4

# Mở thư mục chứa các video có sẵn
live-wallpaper dir
```

---

### 6. ⚡ macOS Pro Terminal & Hiệu Ứng Gõ Phím Động

Terminal được thiết kế tối ưu cho lập trình viên với phong cách Apple macOS hiện đại:

#### Các tính năng thị giác nổi bật:
- 🎨 **Giao diện mờ kính Tokyo Night (Ptyxis Terminal):** Độ trong suốt mờ kính (opacity 0.88), bảng màu Tokyo Night mượt mà, font lập trình viên `MesloLGS NF` hiển thị sắc nét biểu tượng Git, nhánh và mũi tên phân cấp chuẩn theme Agnoster.
- ⚡ **Hiệu ứng gõ phím Neon Cyan (`#00f0ff`):** Khi nhập phím, con trỏ đổi sang dạng thanh đứng tia sáng (I-beam) phát sáng xanh Neon kèm nhãn trạng thái `⚡ typing` động ở góc phải (RPROMPT) và hệ thống tô màu cú pháp thời gian thực (Syntax Highlighting).
- ⌫ **Hiệu ứng xóa phím Ruby Red (`#ff2a6d`):** Khi bấm `Backspace`, `Delete` hoặc phím tắt xóa nguyên từ (`Ctrl + W` / `Alt + Backspace`), con trỏ lập tức đổi sang khối vuông đỏ Ruby Red nhấp nháy kèm nhãn `⌫ delete` hoặc `✂ cut`.
- 🔑 **Hiển thị dấu sao mật khẩu sudo (`pwfeedback`):** Tự động hiển thị các dấu sao `****` sinh động khi nhập hoặc xóa mật khẩu trong lệnh `sudo`, giải quyết triệt để cảm giác gõ trong bóng tối trên Linux.
- 🌧️ **Hacker Matrix Rain Splash:** Khi mở bất kỳ cửa sổ Terminal mới, hiệu ứng mưa mã số xanh Matrix lướt qua trong 0.85 giây cực ngầu kèm dòng chào Typewriter `⚡ [SYSTEM READY] Xin chào, <Tên người dùng>!`.
- 📊 **Fastfetch Logo & Specs:** Gõ `fetch` hoặc `apple` để hiển thị logo và thông số CPU, GPU, RAM, OS chuẩn macOS/Linux.

#### Lệnh quản lý hiệu ứng:
```bash
typing-fx on        # Bật hiệu ứng gõ và xóa phím
typing-fx off       # Tắt hiệu ứng, trả về con trỏ mặc định
typing-fx test      # Chạy kiểm tra các màu sắc hiệu ứng con trỏ
typing-fx status    # Xem trạng thái hoạt động hiện tại của hiệu ứng
fetch               # Hoặc 'apple' - Xem thông số hệ thống Fastfetch
hacker              # Hoặc 'matrix' - Chạy mưa số Matrix toàn màn hình
cls                 # Hoặc 'c' - Xóa nhanh màn hình terminal
ll                  # Liệt kê tệp tin chi tiết có màu sắc trực quan (ls -lah)
```

---

<a id="vi-uninstall"></a>

## 🗑️ 3. Lệnh Xóa / Gỡ Bỏ — Uninstallation (rm) (Tiếng Việt)

Khi muốn xóa bỏ một thành phần nào đó hoặc gỡ toàn bộ hệ thống, bạn có 2 lựa chọn:

### Phương Pháp 1: Gỡ Bằng Script Nhanh

```bash
# Menu tương tác:
./uninstall.sh
# Hoặc lệnh tắt:
./rm.sh
```

Hoặc truyền trực tiếp tham số:

| Thành phần muốn xóa | Lệnh xóa | Lệnh tắt | Mô tả chi tiết |
| :--- | :--- | :--- | :--- |
| **Gỡ TOÀN BỘ sạch sẽ** | `./uninstall.sh all` | `./rm.sh all` | Gỡ bỏ toàn bộ 6 thành phần, xóa sạch cấu hình, khôi phục Ubuntu gốc. |
| **Chỉ xóa Dynamic Island** | `./uninstall.sh island` | `./rm.sh island` | Tắt tiến trình, xóa launcher, autostart, icon và khôi phục Mutter liveness. |
| **Chỉ xóa macOS Menu Bar** | `./uninstall.sh menubar` | `./rm.sh menubar` | Tắt và xóa GNOME Shell Extension thanh menu Apple. |
| **Chỉ tắt & xóa Widgets** | `./uninstall.sh widgets` | `./rm.sh widgets` | Tắt tiến trình widgets, xóa shortcut và tắt cấu hình widget. |
| **Chỉ xóa các App macOS** | `./uninstall.sh apps` | `./rm.sh apps` | Xóa các file `.desktop` của App Store, Notes, Photos, Settings, AirDrop, Photo Booth. |
| **Chỉ dừng & xóa Live Wallpaper** | `./uninstall.sh wallpaper` | `./rm.sh wallpaper` | Dừng video nền, xóa PID/log, xóa shortcut và khôi phục hình nền GNOME. |
| **Chỉ gỡ Terminal & Typing FX** | `./uninstall.sh terminal` | `./rm.sh terminal` | Gỡ bỏ hiệu ứng gõ phím, khôi phục Shell Bash mặc định, tắt pwfeedback của sudo. |

---

### Phương Pháp 2: Lệnh Xóa Thủ Công Bằng Tay

Dành cho người dùng muốn tự tay kiểm soát từng dòng lệnh:

#### 1. Xóa riêng Dynamic Island:
```bash
./main.py quit 2>/dev/null || pkill -f "python3.*main.py"
rm -f ~/.local/share/applications/dynamic-island.desktop
rm -f ~/.config/autostart/dynamic-island.desktop
rm -f ~/.local/share/icons/hicolor/scalable/apps/dynamic-island.svg
gsettings set org.gnome.mutter check-alive-timeout 5000 2>/dev/null || true
update-desktop-database ~/.local/share/applications
gtk-update-icon-cache ~/.local/share/icons/hicolor
```

#### 2. Xóa riêng macOS Menu Bar Extension:
```bash
gnome-extensions disable macos-menu-bar@Nguyenthanhtam 2>/dev/null || true
rm -rf ~/.local/share/gnome-shell/extensions/macos-menu-bar@Nguyenthanhtam
rm -f ~/.local/share/dynamic-island
# Đăng xuất và đăng nhập lại để thanh panel trên trở về mặc định của Ubuntu
```

#### 3. Xóa và Tắt Widgets Desktop:
```bash
pkill -f "desktop_widgets" 2>/dev/null || true
rm -f ~/.local/share/applications/macos-widgets.desktop
python3 -c "from src.config import config; [config.set(f'enable_desktop_{k}', False) for k in ['calendar','weather','battery','clock','music','photo','weekday','macbook']]" 2>/dev/null || true
```

#### 4. Xóa riêng Các Ứng Dụng macOS:
```bash
rm -f ~/.local/share/applications/macos-notes.desktop
rm -f ~/.local/share/applications/macos-photos.desktop
rm -f ~/.local/share/applications/macos-settings.desktop
rm -f ~/.local/share/applications/macos-airdrop.desktop
rm -f ~/.local/share/applications/macos-photobooth.desktop
rm -f ~/.local/share/applications/snap-store_snap-store.desktop
rm -f ~/.local/share/applications/macos-deb-installer.desktop
update-desktop-database ~/.local/share/applications
```

#### 5. Dừng & Xóa Hình Nền Động:
```bash
python3 scripts/live_wallpaper.py stop 2>/dev/null || pkill -f "live_wallpaper"
rm -f /tmp/live_wallpaper.pid /tmp/live_wallpaper.log
rm -f ~/.local/share/applications/live-wallpaper.desktop
rm -f ~/.config/autostart/live-wallpaper.desktop
rm -f ~/.local/bin/live-wallpaper
gsettings reset org.gnome.desktop.background picture-uri 2>/dev/null || true
gsettings reset org.gnome.desktop.background picture-uri-dark 2>/dev/null || true
```

#### 6. Gỡ bỏ riêng Terminal Effects & Khôi phục Bash:
```bash
rm -f ~/.oh-my-zsh/custom/typing_effects.zsh
rm -f ~/.local/bin/hacker_splash
sudo rm -f /etc/sudoers.d/pwfeedback 2>/dev/null || true
chsh -s $(which bash) $USER 2>/dev/null || true
```

---

<a id="vi-cli"></a>

## ⌨️ 4. Bảng Lệnh CLI (Tiếng Việt)

Bạn có thể chạy các lệnh này từ Terminal hoặc gán phím tắt tùy chỉnh trong `Settings -> Keyboard -> Keyboard Shortcuts -> Custom Shortcuts`:

| Lệnh Dòng Lệnh | Chức năng chi tiết |
| :--- | :--- |
| `./main.py toggle` | Bung mở hoặc thu nhỏ Dynamic Island |
| `./main.py expand` | Mở rộng Hub điều khiển của đảo |
| `./main.py collapse` | Thu nhỏ đảo về dạng viên thuốc tĩnh |
| `./main.py tab media` | Mở ngay Tab Trình phát nhạc & Visualizer sóng âm |
| `./main.py tab vitals` | Mở ngay Tab Theo dõi tải CPU, RAM và Pin |
| `./main.py tab controls` | Mở ngay Tab Thanh trượt âm lượng & độ sáng |
| `./main.py tab timer` | Mở ngay Tab Đồng hồ đếm ngược Pomodoro |
| `./main.py tab notifs` | Mở ngay Tab Lịch sử thông báo hệ thống |
| `./main.py tab settings` | Mở ngay Tab Tùy chỉnh kích thước & giao diện |
| `./main.py theme` | Chuyển đổi Dark Mode 🌙 / Light Mode ☀️ |
| `./main.py calendar` | Bật / Tắt nhanh Widget Lịch & Âm Lịch |
| `./main.py weather` | Bật / Tắt nhanh Widget Thời Tiết |
| `./main.py battery` | Bật / Tắt nhanh Widget Vòng Pin 4 Thiết Bị |
| `./main.py size 260 42` | Đổi nhanh kích thước viên thuốc (Dài x Cao) |
| `./main.py wallpaper choose` | Mở giao diện chọn video hình nền động |
| `./main.py quit` | Thoát hoàn toàn Dynamic Island |
| `typing-fx on` / `off` | Bật hoặc Tắt hiệu ứng gõ Neon Cyan & xóa Ruby Red |
| `typing-fx test` | Thử nghiệm hiển thị các màu sắc con trỏ Terminal |
| `typing-fx status` | Xem trạng thái hiệu ứng gõ phím hiện tại |
| `fetch` / `apple` | Hiển thị thông số phần cứng & logo Fastfetch |
| `hacker` / `matrix` | Chạy hiệu ứng mưa mã số Matrix toàn màn hình |

---

<a id="vi-troubleshooting"></a>

## 🔧 5. Khắc Phục Sự Cố Phổ Biến (Tiếng Việt)

### 1. Thanh Menu macOS chưa hiện lên sau khi cài đặt?
- Do cơ chế bảo mật của GNOME Shell trên Wayland, các extension mới kích hoạt cần khởi động lại phiên làm việc: Bạn chỉ cần **Đăng xuất (Log Out)** và **Đăng nhập lại**. Hoặc mở ứng dụng **Extensions** (hoặc **Extension Manager**) và kiểm tra công tắc tiện ích **macOS Menu Bar** đã được Bật (`ON`).

---

### 2. Bị hiện đè 2 thanh âm lượng khi bấm phím Volume?
- Script cài đặt đã tự động chèn CSS vô hiệu hóa thanh OSD mặc định của GNOME để chỉ hiển thị độc quyền trên Dynamic Island. Nếu bạn vừa đổi theme GNOME Shell mới, chỉ cần chạy lại: `./install.sh island`, sau đó Đăng xuất và Đăng nhập lại.

---

### 3. Có bao giờ bị hiện lỗi "Main.py Is Not Responding" không?
- **Không bao giờ!** Dự án bảo vệ ứng dụng bằng cách gỡ bỏ cờ `_NET_WM_PING` khỏi thuộc tính cửa sổ X11 và cấu hình `gsettings set org.gnome.mutter check-alive-timeout 0`. Cửa sổ Dynamic Island được GNOME công nhận là Desktop Dock tĩnh mượt mà 60 FPS.

---

### 4. Làm sao chỉnh Dynamic Island dịch lên sát mép trên hoặc xuống dưới?
- **Cách 1 (Giao diện đồ họa):** Click vào viên thuốc để mở Hub -> Chọn tab **Cài đặt (⚙️)** -> Kéo thanh trượt **Top Offset (Y Margin)** để căn chỉnh theo ý bạn trong thời gian thực.
- **Cách 2 (File cấu hình):** Chỉnh trực tiếp trong file cấu hình `~/.config/dynamic_island/config.json` tại mục `"y_offset"`.

---

<a id="vi-structure"></a>

## 📂 Cấu Trúc Mã Nguồn Dự Án (Tiếng Việt)

```
DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/
├── main.py                     # Entrypoint & Quản lý IPC CLI Hotkey / Dispatcher
├── run.sh                      # Script khởi chạy tổng hợp (X11 & Wayland)
├── install.sh                  # Trình cài đặt Modular (Tất cả hoặc riêng lẻ)
├── uninstall.sh                # Trình gỡ cài đặt Modular thông minh
├── rm.sh                       # Lệnh gỡ tắt nhanh tương đương uninstall.sh
├── install_theme.sh            # Cài đặt Zsh, Oh My Zsh, Agnoster, Ptyxis & hiệu ứng gõ phím
├── dynamic-island.desktop      # Desktop launcher & Cấu hình Autostart
├── requirements.txt            # Danh sách thư viện Python & GTK
├── README.md                   # Tài liệu song ngữ Tiếng Việt & English
│
├── extensions/
│   └── macos-menu-bar@Nguyenthanhtam/   # GNOME Shell Extension (Thanh Menu Apple)
│       ├── extension.js        # Logic tích hợp vào GNOME Shell Top Bar
│       ├── menu.js             # Menu Apple, Active App & Hook chặn OSD
│       ├── stylesheet.css      # Giao diện kính mờ Frosted Glass
│       └── metadata.json       # Tương thích GNOME Shell 42 - 50
│
├── scripts/
│   ├── live_wallpaper.py       # Động cơ phát video hình nền động 60 FPS / Live Wallpaper
│   ├── typing_effects.zsh      # Hiệu ứng gõ Neon Cyan & xóa Ruby Red cho Terminal
│   ├── setup_terminal_effects.sh # Bật dấu sao mật khẩu sudo (Defaults pwfeedback)
│   ├── hacker_splash.py        # Hiệu ứng mở đầu Matrix Rain & lời chào Typewriter
│   ├── setup_hacker_fetch.py   # Cấu hình Fastfetch hiển thị thông số hệ thống
│   └── install_apple_emoji.sh  # Cài đặt Apple Color Emoji cho Terminal & toàn hệ thống
│
├── assets/
│   ├── wallpapers/             # Bộ video hình nền động 1080p & 4K
│   └── app_icons/              # Bộ biểu tượng ứng dụng vector & PNG
│
└── src/
    ├── window.py               # Vòng lặp vật lý & vẽ Cairo chống răng cưa
    ├── ipc.py                  # Unix socket IPC server nhận lệnh CLI
    ├── modules/                # Bắt nhạc MPRIS2, Âm thanh, Vitals, Hẹn giờ
    └── ui/
        ├── desktop_widgets/    # Lịch âm, Thời tiết, Pin 4 vòng, Đồng hồ, Nhạc
        ├── macos_notes_window.py     # Ứng dụng Ghi chú chuẩn Apple Notes
        ├── macos_photos_window.py    # Thư viện Ảnh & Trình chỉnh sửa ảnh
        ├── macos_settings_window.py  # Cài đặt Hệ thống macOS
        ├── macos_appstore_window.py  # macOS Sequoia App Store
        ├── macos_airdrop_window.py   # AirDrop chia sẻ tệp nội bộ qua WiFi/LAN
        └── macos_photobooth_window.py# Photo Booth & Camera Ảo
```

<div align="center">

**[🔝 Lên đầu trang](#top)** &nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; **[👉 Chuyển sang Tiếng Anh (English)](#english-guide)**

</div>

<br>
<hr style="height: 3px; border: none; background: linear-gradient(90deg, #00f0ff, #ff2a6d, #7aa2f7);">
<br>

<a id="english-guide"></a>

# 🇬🇧 ENGLISH DOCUMENTATION

> *Transform your Ubuntu desktop into a flawless Apple macOS experience: 100% Modular — Install what you want, remove what you don't.*

<div align="center">

[⚡ Installation](#en-installation) • [🧩 Modular Installation](#en-modular) • [🚀 Usage Guide](#en-usage) • [🗑️ Uninstallation (rm)](#en-uninstall) • [⌨️ CLI Reference](#en-cli) • [🔧 Troubleshooting](#en-troubleshooting) • [📂 Project Structure](#en-structure) • [🇻🇳 Switch to Vietnamese](#vietnamese-guide)

</div>

---

## 📖 Architecture Overview (English)

The system is engineered as **6 standalone, independent modules**:

1. **🏝️ Dynamic Island:**
   - 60 FPS OLED smart pill overlay rendered with Cairo and GTK.
   - MPRIS2 & PipeWire media integration with a live real-time sound wave visualizer.
   - Hardware vital monitors (CPU, RAM, Battery, Thermal) and Apple volume/brightness HUD (suppresses native GNOME popups).
   - Built-in Pomodoro timer, persistent Clipboard history, and Siri/Gemini AI voice assistant.

2. **🍏 macOS Menu Bar:**
   - Native GNOME Shell Extension bringing the Apple  menu, active application title, and global menus (File, Edit, View, Window, Help).
   - Center Dynamic Island quick-toggle badge.
   - Live Apple Weather tray, macOS Spotlight Search (🔍), System Clock & Calendar, and native macOS Control Center.

3. **🖥️ Desktop Widgets:**
   - Draggable Apple-style widgets: Vietnamese Lunar & Solar Calendar (Ho Ngoc Duc astronomical algorithm), Apple Weather, 4-Ring Battery Gauge (Laptop, AirPods, Case, Mouse), Analog Clock, Music Player, Weekday Clock, and Pinned Photo Frame.
   - Position persistence: Drag and place them anywhere on your desktop; coordinates persist across reboots.

4. **📦 macOS Native App Suite:**
   - macOS Sequoia App Store (Snap/Flatpak/APT software center).
   - Apple Notes clone with rich notes storage.
   - Apple Photos & image editor.
   - macOS System Settings panel.
   - Apple AirDrop local WiFi/LAN file transfer.
   - Photo Booth & Linux Virtual Camera (`v4l2loopback`).
   - Apple-style `.deb` Package Installer.

5. **🎬 Live Wallpaper Engine:**
   - Ultra-smooth 60 FPS video wallpaper engine optimized for 1080p and 4K loops with low CPU usage.
   - Interactive GUI video chooser and instant wallpaper switcher.

6. **⚡ macOS Pro Terminal & Dynamic Typing FX:**
   - Frosted glass Tokyo Night Ptyxis terminal profile (88% opacity), `MesloLGS NF` Nerd Font, Zsh shell & Oh My Zsh Agnoster theme.
   - Real-time **Neon Cyan (`#00f0ff`)** typing glow with I-beam cursor and live `⚡ typing` status in RPROMPT.
   - Real-time **Ruby Red (`#ff2a6d`)** deletion flash with block pulsing and `⌫ delete` / `✂ cut` HUD on Backspace, Delete, and Ctrl+W.
   - Interactive `sudo` password asterisks `****` (`pwfeedback`) for visual feedback during privilege escalation.
   - 0.85s **Hacker Matrix Rain** terminal launch intro with typewriter greeting `⚡ [SYSTEM READY] Xin chào, <User>!`, and Fastfetch Apple system specs.

> [!TIP]
> **Complete Modular Freedom:** Install only what you desire with its specific install command. Remove any individual module whenever you want with its specific removal command, leaving the rest of your system untouched!

---

<a id="en-installation"></a>

## ⚡ 1. Installation (English)

First, open your **Terminal** (`Ctrl + Alt + T`) and clone the repository:

```bash
# 1. Clone the repository
git clone https://github.com/huyenthanhduong3527/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX.git

# 2. Enter the project directory
cd DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX

# 3. Make scripts executable
chmod +x install.sh uninstall.sh rm.sh run.sh main.py install_theme.sh scripts/*.sh scripts/*.py
```

---

### Option A: All-in-One Full Installation (Recommended)

Installs all 6 components simultaneously with a single command:

```bash
./install.sh all
```
*(Running `./install.sh` without arguments opens an interactive numeric selection menu from 1 to 7).*

---

<a id="en-modular"></a>

### Option B: Modular Installation (English)

Install only the specific components you want:

| Component | Install Command | Description |
| :--- | :--- | :--- |
| **🚀 Install ALL** | `./install.sh all` | Installs all 6 components with full features. |
| **🏝️ Dynamic Island** | `./install.sh island` | Installs Dynamic Island, vector icon, autostart entry, and suppresses native GNOME volume OSD. |
| **🍏 macOS Menu Bar** | `./install.sh menubar` | Installs GNOME Shell Extension for Apple  menu, Global Menus, and Control Center. |
| **🖥️ Desktop Widgets** | `./install.sh widgets` | Installs desktop widgets and configures blur-my-shell exclusion. |
| **📦 macOS App Suite** | `./install.sh apps` | Registers macOS App Store, Notes, Photos, Settings, AirDrop, Photo Booth & `.deb` installer. |
| **🎬 Live Wallpaper** | `./install.sh wallpaper` | Installs 60 FPS Live Wallpaper engine, CLI command, and app menu launcher. |
| **⚡ Terminal & Typing FX** | `./install.sh terminal`<br>*(or `./install_theme.sh`)* | Installs Zsh, Oh My Zsh, Agnoster theme, Tokyo Night frosted Ptyxis, Neon Cyan/Ruby Red typing FX, sudo pwfeedback & Matrix splash. |

---

<a id="en-usage"></a>

## 🚀 2. Post-Install Usage Guide (English)

### 1. 🏝️ Dynamic Island

#### How to Launch:
- **Application Grid:** Press `Super` (Windows key) -> search for **Dynamic Island** -> click to open.
- **Terminal CLI:** `./run.sh`
- **Autostart:** Automatically launches upon system startup and login.

#### Interactive Controls:
- **Left Click on the Pill:** Expands into the full **Multi-purpose Control Hub** (Media, Vitals, Controls, Timer, Notifications, Settings, AI Siri/Gemini, Clipboard).
- **Left Click on the Top Header:** Collapses the hub back to the compact pill.
- **Right Click on the Pill:** Opens a quick context menu to jump directly to any tab or exit the application.
- **Volume & Media Hotkeys:** The pill expands into a capsule displaying the current volume level or song title, then automatically collapses after 3.5 seconds.

---

### 2. 🍏 macOS Menu Bar

After running `./install.sh menubar` (or `all`):
- **Log Out and Log back in** to your Ubuntu session to activate the GNOME Shell Extension.
- **Menu Bar Features:**
  - ** Apple Menu (Top-Left):** About This Mac/PC, System Settings, Lock Screen, Sleep, Restart, Shut Down.
  - **Active App & Global Menus:** Displays the foreground application name in bold with File, Edit, View, Window, Help.
  - **🏝️ Island Icon (Center):** Left click to view keyboard shortcuts; right click to toggle Dynamic Island visibility.
  - **Status Tray (Top-Right):** Real-time Weather, Spotlight Search (🔍), macOS Clock & Calendar, and Control Center.

---

### 3. 🖥️ Desktop Widgets

Widgets can launch automatically with Dynamic Island or be run independently:

```bash
# Launch all desktop widgets
./run.sh --widgets

# Or launch individual widgets standalone:
./run.sh --calendar        # Vietnamese Lunar & Solar Calendar
./run.sh --weather         # Apple Weather widget
./run.sh --battery         # 4-Ring Battery Gauge
./run.sh --clock           # Analog Clock widget
./run.sh --music-widget    # Apple Music desktop player
./run.sh --photo           # Pinned Photo Frame widget
./run.sh --weekday-clock   # Weekday & Date Clock widget
```

> [!TIP]
> **Drag & Drop:** Click and drag any widget across the desktop. Its coordinates will automatically persist across reboots!

---

### 4. 📦 macOS Native App Suite

Launch applications directly from Ubuntu's Application Grid or via Terminal:

```bash
./run.sh --appstore        # macOS Sequoia App Store
./run.sh --notes           # Apple Notes
./run.sh --photos          # Apple Photos & Photo Editor
./run.sh --settings        # macOS System Settings
./run.sh --airdrop         # Apple AirDrop (LAN/WiFi local transfer)
./run.sh --photobooth      # Photo Booth & Virtual Camera
./run.sh --install-deb app.deb   # macOS-style .deb Package Installer
```

---

### 5. 🎬 Live Wallpaper Engine

Supports high-refresh 1080p and 4K video loops:

```bash
# Start the live wallpaper daemon in background
live-wallpaper start
# Or using python script directly:
python3 scripts/live_wallpaper.py start

# Stop live wallpaper (restores static background)
live-wallpaper stop

# Check status
live-wallpaper status

# Open GUI video chooser dialog
live-wallpaper choose

# Set a specific video file
live-wallpaper set assets/wallpapers/sakura_torii_4k_live.mp4

# Open wallpaper directory
live-wallpaper dir
```

---

### 6. ⚡ macOS Pro Terminal & Dynamic Typing FX

A sleek developer-focused terminal experience styled after modern Apple macOS with interactive visual typing physics:

#### Key Visual Features:
- 🎨 **Frosted Glass Tokyo Night Profile (Ptyxis Terminal):** High-definition Tokyo Night palette with 88% frosted glass opacity and crisp `MesloLGS NF` Nerd Font for Agnoster branch icons and prompt arrows.
- ⚡ **Neon Cyan Typing Glow (`#00f0ff`):** As you type, the cursor transforms into a glowing neon I-beam with real-time `⚡ typing` status in the right prompt (RPROMPT) and syntax highlighting.
- ⌫ **Ruby Red Deletion Flash (`#ff2a6d`):** On `Backspace`, `Delete`, or kill-word shortcuts (`Ctrl + W` / `Alt + Backspace`), the cursor flashes into a pulsating red block with live `⌫ delete` or `✂ cut` status.
- 🔑 **Interactive Sudo Password Asterisks (`pwfeedback`):** Displays animated asterisks `****` when typing or erasing `sudo` passwords, eliminating blind typing in Linux terminal.
- 🌧️ **Hacker Matrix Rain Splash:** Every time a new terminal window is spawned, a 0.85-second digital green Matrix rain animation flashes by, followed by an animated typewriter greeting `⚡ [SYSTEM READY] Xin chào, <User>!`.
- 📊 **Fastfetch Logo & Specs:** Run `fetch` or `apple` to display system specifications with macOS/Linux branding.

#### Terminal CLI Commands:
```bash
typing-fx on        # Turn ON dynamic typing and deleting effects
typing-fx off       # Turn OFF effects and restore default cursor
typing-fx test      # Test cursor color modes and transitions
typing-fx status    # Show current typing FX configuration
fetch               # Or 'apple' - Display Fastfetch system specs
hacker              # Or 'matrix' - Run full-screen Matrix rain
cls                 # Or 'c' - Clear terminal screen
ll                  # Colorized long list directory contents (ls -lah)
```

---

<a id="en-uninstall"></a>

## 🗑️ 3. Uninstallation / Removal (rm) (English)

You can uninstall individual components or remove everything cleanly using either the interactive script or manual commands:

### Method 1: Quick Script Uninstall

```bash
# Interactive menu:
./uninstall.sh
# Or shortcut:
./rm.sh
```

Or pass target arguments directly:

| Target | Uninstaller Command | Short Command | Description |
| :--- | :--- | :--- | :--- |
| **Clean Uninstall ALL** | `./uninstall.sh all` | `./rm.sh all` | Removes all 6 modules, cleans configurations, and restores default Ubuntu. |
| **Dynamic Island Only** | `./uninstall.sh island` | `./rm.sh island` | Terminates process, removes launcher, autostart, icon & restores Mutter timeout. |
| **macOS Menu Bar Only** | `./uninstall.sh menubar` | `./rm.sh menubar` | Disables and deletes GNOME Shell top bar extension. |
| **Desktop Widgets Only** | `./uninstall.sh widgets` | `./rm.sh widgets` | Kills widget processes, removes launcher, disables widget config. |
| **macOS Apps Only** | `./uninstall.sh apps` | `./rm.sh apps` | Removes desktop entries for all macOS apps from App Grid. |
| **Live Wallpaper Only** | `./uninstall.sh wallpaper` | `./rm.sh wallpaper` | Stops live wallpaper, cleans PID/log, restores default GNOME background. |
| **Terminal & Typing FX** | `./uninstall.sh terminal` | `./rm.sh terminal` | Removes typing effects, restores default Bash shell, disables sudo pwfeedback. |

---

### Method 2: Manual Terminal Commands

For users who prefer running terminal commands manually:

#### 1. Remove Dynamic Island Only:
```bash
./main.py quit 2>/dev/null || pkill -f "python3.*main.py"
rm -f ~/.local/share/applications/dynamic-island.desktop
rm -f ~/.config/autostart/dynamic-island.desktop
rm -f ~/.local/share/icons/hicolor/scalable/apps/dynamic-island.svg
gsettings set org.gnome.mutter check-alive-timeout 5000 2>/dev/null || true
update-desktop-database ~/.local/share/applications
gtk-update-icon-cache ~/.local/share/icons/hicolor
```

#### 2. Remove macOS Menu Bar Extension Only:
```bash
gnome-extensions disable macos-menu-bar@Nguyenthanhtam 2>/dev/null || true
rm -rf ~/.local/share/gnome-shell/extensions/macos-menu-bar@Nguyenthanhtam
rm -f ~/.local/share/dynamic-island
# Log out and log back in to restore Ubuntu's default top panel
```

#### 3. Remove Desktop Widgets Only:
```bash
pkill -f "desktop_widgets" 2>/dev/null || true
rm -f ~/.local/share/applications/macos-widgets.desktop
python3 -c "from src.config import config; [config.set(f'enable_desktop_{k}', False) for k in ['calendar','weather','battery','clock','music','photo','weekday','macbook']]" 2>/dev/null || true
```

#### 4. Remove macOS Apps Only:
```bash
rm -f ~/.local/share/applications/macos-notes.desktop
rm -f ~/.local/share/applications/macos-photos.desktop
rm -f ~/.local/share/applications/macos-settings.desktop
rm -f ~/.local/share/applications/macos-airdrop.desktop
rm -f ~/.local/share/applications/macos-photobooth.desktop
rm -f ~/.local/share/applications/snap-store_snap-store.desktop
rm -f ~/.local/share/applications/macos-deb-installer.desktop
update-desktop-database ~/.local/share/applications
```

#### 5. Remove Live Wallpaper Only:
```bash
python3 scripts/live_wallpaper.py stop 2>/dev/null || pkill -f "live_wallpaper"
rm -f /tmp/live_wallpaper.pid /tmp/live_wallpaper.log
rm -f ~/.local/share/applications/live-wallpaper.desktop
rm -f ~/.config/autostart/live-wallpaper.desktop
rm -f ~/.local/bin/live-wallpaper
gsettings reset org.gnome.desktop.background picture-uri 2>/dev/null || true
gsettings reset org.gnome.desktop.background picture-uri-dark 2>/dev/null || true
```

#### 6. Remove Terminal Effects & Restore Bash Only:
```bash
rm -f ~/.oh-my-zsh/custom/typing_effects.zsh
rm -f ~/.local/bin/hacker_splash
sudo rm -f /etc/sudoers.d/pwfeedback 2>/dev/null || true
chsh -s $(which bash) $USER 2>/dev/null || true
```

---

<a id="en-cli"></a>

## ⌨️ 4. Command Line (CLI) Reference (English)

Run these commands in Terminal or bind them to custom shortcuts in `Settings -> Keyboard -> Keyboard Shortcuts -> Custom Shortcuts`:

| CLI Command | Description |
| :--- | :--- |
| `./main.py toggle` | Toggle expand/collapse of the island |
| `./main.py expand` | Expand into full card hub |
| `./main.py collapse` | Collapse back to compact pill |
| `./main.py tab media` | Open Media Player & Live Visualizer tab |
| `./main.py tab vitals` | Open Hardware Vitals monitoring tab |
| `./main.py tab controls` | Open Volume & Display Controls tab |
| `./main.py tab timer` | Open Timer & Pomodoro tab |
| `./main.py tab notifs` | Open Notifications history tab |
| `./main.py tab settings` | Open Island Settings tab |
| `./main.py theme` | Toggle Dark Mode 🌙 / Light Mode ☀️ |
| `./main.py calendar` | Toggle Vietnamese Lunar & Solar Calendar widget |
| `./main.py weather` | Toggle Apple Weather widget |
| `./main.py battery` | Toggle 4-Ring Battery Gauge widget |
| `./main.py size 260 42` | Set compact pill dimensions (Width x Height) |
| `./main.py wallpaper choose` | Open Live Wallpaper file chooser |
| `./main.py quit` | Completely terminate Dynamic Island |
| `typing-fx on` / `off` | Enable or disable Neon Cyan & Ruby Red typing FX |
| `typing-fx test` | Test terminal cursor colors and animations |
| `typing-fx status` | Check dynamic typing effects status |
| `fetch` / `apple` | Display system specs & Fastfetch logo |
| `hacker` / `matrix` | Launch full-screen Matrix digital rain effect |

---

<a id="en-troubleshooting"></a>

## 🔧 5. Troubleshooting & FAQ (English)

<details>
<summary><b>1. macOS Menu Bar is not showing after installation?</b></summary>
<br>

Due to GNOME Shell security policies on Wayland, newly installed extensions require a session reload: Simply **Log Out** and **Log back in**. Alternatively, open the **Extension Manager** application and verify that **macOS Menu Bar** is switched **ON**.
</details>

<details>
<summary><b>2. Dual volume OSD popups appearing when pressing Volume keys?</b></summary>
<br>

The installer automatically injects CSS rules to suppress GNOME's native OSD. If you recently switched your GNOME Shell theme, re-run: `./install.sh island`, then log out and log back in.
</details>

<details>
<summary><b>3. Is there any "Main.py Is Not Responding" modal crash?</b></summary>
<br>

**Never!** We protect the application by removing the `_NET_WM_PING` protocol from the X11 window attributes and setting `gsettings set org.gnome.mutter check-alive-timeout 0`. Dynamic Island is treated by GNOME as a smooth 60 FPS static desktop dock.
</details>

<details>
<summary><b>4. How to adjust the Dynamic Island top position (Y-offset)?</b></summary>
<br>

- **Via GUI:** Click the pill to expand into the Hub -> Go to the **Settings (⚙️)** tab -> Drag the **Top Offset (Y Margin)** slider in real time.
- **Via Config File:** Directly edit `"y_offset"` in `~/.config/dynamic_island/config.json`.
</details>

---

<a id="en-structure"></a>

## 📂 Project Structure (English)

```
DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/
├── main.py                     # Entrypoint & CLI/IPC Command Dispatcher
├── run.sh                      # Unified runner script (X11 / Wayland overlay)
├── install.sh                  # Modular installer (All or specific components)
├── uninstall.sh                # Modular uninstaller (All or specific components)
├── rm.sh                       # Quick shortcut wrapper for uninstall.sh
├── install_theme.sh            # One-click Zsh, Oh My Zsh, Agnoster, Ptyxis & typing FX installer
├── dynamic-island.desktop      # Desktop launcher & Autostart config
├── requirements.txt            # System dependencies list
├── README.md                   # Unified Bilingual documentation (Tiếng Việt & English)
│
├── extensions/
│   └── macos-menu-bar@Nguyenthanhtam/   # GNOME Shell Extension (Top Menu Bar)
│       ├── extension.js        # GNOME Shell integration logic
│       ├── menu.js             # Apple menu & OSD suppression hooks
│       ├── stylesheet.css      # Frosted glass styling for GNOME Top Bar
│       └── metadata.json       # Compatibility manifest (GNOME 42 - 50)
│
├── scripts/
│   ├── live_wallpaper.py       # 60 FPS 4K/1080p Live Video Wallpaper Engine
│   ├── typing_effects.zsh      # Dynamic Neon Cyan typing and Ruby Red deleting FX
│   ├── setup_terminal_effects.sh # Enable sudo password asterisks (Defaults pwfeedback)
│   ├── hacker_splash.py        # Hacker Matrix Rain splash intro & Typewriter greeting
│   ├── setup_hacker_fetch.py   # Fastfetch system specs config with custom logo
│   └── install_apple_emoji.sh  # Apple Color Emoji installer for Terminal & apps
│
├── assets/
│   ├── wallpapers/             # High-resolution video loops (1080p & 4K)
│   └── app_icons/              # High-resolution vector & PNG application icons
│
└── src/
    ├── window.py               # Cairo anti-aliased window & physics event loop
    ├── ipc.py                  # Unix socket IPC server for CLI hotkey control
    ├── modules/                # Media MPRIS2, Audio, System Vitals, Timer, Notifs
    └── ui/
        ├── desktop_widgets/    # Lunar Calendar, Weather, Battery, Clock, Music
        ├── macos_notes_window.py     # Native Apple Notes clone
        ├── macos_photos_window.py    # Apple Photos & image editor
        ├── macos_settings_window.py  # macOS System Settings dialog
        ├── macos_appstore_window.py  # macOS Sequoia App Store
        ├── macos_airdrop_window.py   # AirDrop local network transfer
        └── macos_photobooth_window.py# Photo Booth & Virtual Camera
```

---

## 📄 License

Distributed under the open-source **[MIT License](LICENSE)**. Feel free to fork, customize, and share!

<div align="center">

⭐ <i>Nếu bạn yêu thích dự án, hãy tặng 1 sao (Star) trên GitHub nhé! / If you enjoy this project, consider giving it a Star on GitHub!</i> ⭐

<br>

**[🔝 Lên đầu trang / Back to Top](#top)** &nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; **[🇻🇳 Tiếng Việt](#vietnamese-guide)** &nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; **[🇬🇧 English](#english-guide)**

</div>
