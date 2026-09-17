<div align="center">

# 🏝️ Dynamic Island & macOS Menu Bar for GNOME
### Giao diện Dynamic Island & Thanh Menu macOS Tahoe / Sequoia cao cấp cho Linux Ubuntu

[![Ubuntu](https://img.shields.io/badge/Ubuntu-22.04%20|%2024.04%20|%2026.04-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)](https://ubuntu.com)
[![GNOME](https://img.shields.io/badge/GNOME-Shell%2045%20--%2050-4a86cf?style=for-the-badge&logo=gnome&logoColor=white)](https://www.gnome.org)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![GTK](https://img.shields.io/badge/GUI-GTK3%20%2B%20Cairo-4B275F?style=for-the-badge)](https://www.gtk.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)

*Mang trải nghiệm Apple Dynamic Island mượt mà chuẩn 60 FPS cùng thanh Top Bar macOS đẳng cấp lên chiếc máy tính Linux của bạn.*

[Cài Đặt Nhanh](#-cài-đặt-nhanh-1-bước) • [Tính Năng](#-tính-năng-nổi-bật) • [Chế Độ Sáng/Tối](#-chuyển-đổi-giao-diện-sáng--tối-dark--light-mode) • [Phím Tắt CLI](#-điều-khiển-bằng-dòng-lệnh-cli--ipc) • [Cấu Trúc Dự Án](#-cấu-trúc-thư-mục)

---

</div>

## ⚡ Cài Đặt Nhanh (1 Bước)

Mở **Terminal** và dán đoạn lệnh sau để cài đặt trọn gói tất cả thành phần:

```bash
git clone https://github.com/huyenthanhduong3527/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX.git
cd DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX
./install.sh
```

> **`install.sh` sẽ tự động:**
> 1. Đăng ký biểu tượng vector chất lượng cao vào hệ thống.
> 2. Cài đặt file chạy (`dynamic-island.desktop`) vào danh sách ứng dụng GNOME.
> 3. Kích hoạt chế độ **tự động khởi động cùng hệ thống** (Autostart).
> 4. Cài đặt và bật tiện ích **macOS Menu Bar** cho GNOME Shell.

Sau khi cài đặt xong, bạn có thể khởi chạy ngay bằng lệnh:
```bash
./run.sh
```

---

## ✨ Tính Năng Nổi Bật

### 1. 🏝️ Dynamic Island Hub (Python GTK3 + Cairo)

| Tính năng | Mô tả chi tiết |
| :--- | :--- |
| **🪐 Vũ Trụ Orbit (Solar App Launcher)** | **Hiệu ứng thiên hà 3D độc nhất**: 6 hành tinh thiên thể (Chrome, Terminal, VS Code, Music, Files, Settings) chuyển động quỹ đạo elip quanh đảo Dynamic Island. Click hành tinh để khởi chạy ứng dụng kèm sóng xung kích, rê chuột để xem huy hiệu kính mờ và hỗ trợ Click-Through xuyên thấu vào cửa sổ bên dưới. |
| **Vật lý lò xo 60 FPS** | Đồ họa OLED đen tuyền, bóng đổ mờ tự nhiên cùng hiệu ứng lò xo (*Spring physics*) bung mở siêu mượt. |
| **Compact Idle Pill** | Viên thuốc thu nhỏ tinh tế trên đỉnh màn hình, hiển thị đồng hồ, icon trạng thái hoặc dải sóng âm mini. |
| **Expanded Hub** | Bung mở đối xứng từ tâm thành bảng điều khiển đa năng chia theo các tab chức năng tiện lợi. |
| **🎵 Trình phát nhạc MPRIS2** | Tự động kết nối **Spotify, YouTube trên trình duyệt, VLC, Amberol, Rhythmbox...** với thanh tua bài hát và điều khiển Play/Pause/Next. |
| **Live Audio Visualizer** | 10 cột sóng âm nhảy nhịp nhàng theo giai điệu bài hát theo thời gian thực. |
| **⚡ Giám sát tài nguyên (Vitals)**| Đo tải **CPU**, dung lượng **RAM** và tình trạng **Pin (UPower)** thời gian thực. |
| **🎛️ Bảng điều khiển nhanh** | Kéo chỉnh âm lượng Master (PipeWire / WirePlumber), nút Mute, chụp ảnh màn hình và khóa máy nhanh. |
| **⏱️ Đếm giờ & Pomodoro** | Đếm ngược 1m, 5m, 15m, 25m (Pomodoro) và đồng hồ bấm giờ 1/10s. Tự động hiển thị thời gian trên viên thuốc khi thu nhỏ. |
| **🔔 Dynamic Event Popups** | Tự động bung viên thuốc báo âm lượng khi bấm phím volume, báo tên bài hát khi chuyển nhạc, và hiển thị thông báo ứng dụng. |

---

### 2. 🍏 macOS Menu Bar (GNOME Shell Extension)

Thay thế thanh GNOME panel mặc định thành thanh Menu chuẩn Apple macOS Tahoe / Sequoia:

- ** Apple Menu**: Truy cập nhanh Thông tin máy (*About This Mac*), Cài đặt hệ thống, Tắt máy, Khởi động lại, Khóa màn hình.
- **Active App Menu**: Tên ứng dụng in đậm (**Dynamic Island**) bên cạnh logo Táo với các tác vụ nhanh.
- **Thanh Menu toàn cầu**: File, Edit, View, Go, Window, Tools, Settings, Help, Search.
- **🏝️ Dynamic Island Capsule ở giữa**: Viên thuốc OLED đặt ngay tâm thanh panel:
  - **Nhấp chuột trái**: Bung mở hoặc thu nhỏ đảo.
  - **Nhấp chuột phải**: Menu truy cập nhanh các tab chức năng.
- **Khay trạng thái đầy đủ (Right Status Tray)**:
  - **☀️ Thời tiết trực tiếp**: Icon thời tiết + nhiệt độ thời gian thực (ví dụ: `☀️ 29°C`).
  - **🎵 Now Playing**: Nút điều khiển nhanh trình nghe nhạc.
  - **🔋 Pin & Sạc**: Biểu tượng pin kèm % chính xác từ phần cứng.
  - **🔊 Âm lượng**: Icon loa tự đổi theo mức volume thực tế.
  - **📶 Wi-Fi & Bluetooth**: Cường độ tín hiệu và trạng thái kết nối.
  - **🌗 Nút đổi Sáng/Tối**: Đổi giao diện toàn hệ thống chỉ với 1 click chuột.
  - **🎛️ Control Center**: Mở nhanh bảng Quick Settings của GNOME.
  - **📅 Đồng hồ & Lịch**: Thứ, ngày tháng và giờ (`Th 4 17/09 11:45 AM`), bấm để xem lịch.
  - **🔍 Spotlight Search**: Mở nhanh công cụ tìm kiếm ứng dụng.

---

## 🌗 Chuyển Đổi Giao Diện Sáng / Tối (Dark / Light Mode)

Bạn có thể dễ dàng chuyển đổi giao diện Dark/Light mode bằng bất kỳ cách nào sau đây:

1. **Trên thanh Menu Bar (Góc phải)**: Nhấp trực tiếp vào icon **Mặt Trời ☀️ / Mặt Trăng 🌙** trên khay trạng thái.
2. **Trong Dynamic Island Hub**:
   - Tab **Controls (🎛️)**: Bấm nút **`[ 🌗 Dark Mode / Light Mode ]`**.
   - Tab **Settings (⚙️)**: Gạt công tắc **`Dark Mode (Giao diện Tối)`**.
3. **Từ Menu Apple `` hoặc Menu Capsule**: Chọn **`🌗 Chuyển Giao diện Sáng / Tối`**.
4. **Bằng dòng lệnh Terminal**:
   ```bash
   ./main.py theme
   ```

*Hệ thống sẽ tự động đồng bộ giá trị `color-scheme` (`prefer-dark` ↔ `default`) và tự động kích hoạt bộ theme GTK macOS tương ứng (`MacTahoe-Dark` ↔ `MacTahoe-Light`).*

---

## 🎮 Thao Tác Chuột & Điều Khiển

- **Click chuột trái vào viên thuốc**: Bung mở đảo thành Hub chi tiết.
- **Click chuột trái vào thanh trên của Hub**: Thu nhỏ đảo về viên thuốc.
- **Click chuột phải vào đảo**: Mở menu ngữ cảnh để nhảy nhanh đến bất kỳ tab nào hoặc thoát ứng dụng.
- **Kéo chuột (Hover)**: Có thể bật chế độ rê chuột tự mở đảo trong tab Cài đặt (*Settings*).

---

## ⌨️ Điều Khiển Bằng Dòng Lệnh (CLI / IPC)

Bạn có thể tạo phím tắt hệ thống hoặc điều khiển Dynamic Island từ bất kỳ đâu qua terminal:

```bash
./main.py toggle         # Bung mở hoặc thu nhỏ đảo
./main.py cosmos         # Bật/tắt hiệu ứng Vũ trụ Orbit (Solar App Launcher)
./main.py theme          # Chuyển đổi giao diện Sáng / Tối
./main.py collapse       # Thu nhỏ đảo về viên thuốc
./main.py expand         # Bung mở đảo thành Hub

# Mở trực tiếp từng tab chức năng:
./main.py tab media      # Tab Trình nghe nhạc
./main.py tab vitals     # Tab Tài nguyên máy tính (CPU/RAM/Pin)
./main.py tab controls   # Tab Bảng điều khiển & Âm lượng
./main.py tab timer      # Tab Đồng hồ đếm giờ Pomodoro
./main.py tab notifs     # Tab Lịch sử thông báo
./main.py tab settings   # Tab Cài đặt giao diện

./main.py quit           # Thoát ứng dụng
```

---

## 📂 Cấu Trúc Thư Mục

Mã nguồn được cấu trúc sạch sẽ, module hóa rõ ràng, sẵn sàng để phát triển và đóng góp:

```
Dynamic_island/
├── main.py                     # Khởi chạy chính và điều khiển IPC CLI
├── run.sh                      # Script khởi chạy (GDK_BACKEND=x11)
├── install.sh                  # Bộ cài đặt tự động 1 bước
├── dynamic-island.desktop      # File launcher cho GNOME Grid & Autostart
├── requirements.txt            # Thư viện hệ thống
├── .gitignore                  # Cấu hình bỏ qua file rác / cache
├── README.md                   # Tài liệu hướng dẫn sử dụng
│
├── extensions/
│   └── macos-menu-bar@Nguyenthanhtam/
│       ├── extension.js        # Logic GNOME Shell Extension (ESM)
│       ├── stylesheet.css      # CSS giao diện Top Bar & Menus
│       ├── metadata.json       # Metadata tương thích GNOME 45 - 50
│       └── apple-symbolic.svg  # Logo Apple vector
│
└── src/
    ├── config.py               # Quản lý cấu hình JSON (~/.config/dynamic_island/)
    ├── animator.py             # Bộ tính toán chuyển động lò xo vật lý (Spring 60fps)
    ├── window.py               # Cửa sổ chính Cairo trong suốt & phân luồng sự kiện
    ├── ipc.py                  # Socket IPC giao tiếp tiến trình cục bộ
    ├── modules/
    │   ├── media.py            # Kết nối D-Bus MPRIS2 & Demo player
    │   ├── audio.py            # Điều khiển PipeWire / WirePlumber (wpctl)
    │   ├── system.py           # Giám sát phần cứng CPU, RAM, Pin (UPower)
    │   ├── timer.py            # Bộ đếm giờ Pomodoro & bấm giờ
    │   └── notification.py     # Lắng nghe thông báo D-Bus hệ thống
    ├── ui/
    │   ├── styles.css          # CSS phong cách Apple OLED Dark Glassmorphism
    │   ├── cosmic_orbit.py     # Động cơ Vũ trụ Orbit 3D, hành tinh thiên thể & sóng xung kích
    │   ├── compact_view.py     # Giao diện viên thuốc thu nhỏ
    │   ├── expanded_view.py    # Giao diện Hub mở rộng chia Tab
    │   ├── event_banner.py     # Capsule thông báo nổi tự động
    │   └── tabs/
    │       ├── media_tab.py    # Tab nghe nhạc & sóng âm Visualizer
    │       ├── vitals_tab.py   # Tab tài nguyên phần cứng
    │       ├── controls_tab.py # Tab phím tắt nhanh & nút đổi Sáng/Tối
    │       ├── timer_tab.py    # Tab đếm ngược & bấm giờ
    │       ├── notifications_tab.py # Tab lịch sử thông báo
    │       └── settings_tab.py # Tab tinh chỉnh vị trí Y & thông số đảo
    └── utils/
        ├── icons.py            # Thư viện icon SVG vector tích hợp
        ├── theme.py            # Bộ xử lý chuyển đổi theme Dark/Light mode
        ├── artwork.py          # Bộ xử lý ảnh bìa album nhạc
        └── visualizer.py       # Thuật toán sóng âm âm nhạc
```

---

## ❓ Câu Hỏi Thường Gặp (FAQ)

<details>
<summary><b>1. Tôi cài đặt xong nhưng thanh Top Bar chưa hiển thị giao diện macOS?</b></summary>
<br>
Do cơ chế của GNOME Shell trên Wayland, các extension mới cần khởi động lại session để áp dụng toàn diện. Bạn chỉ cần <b>Đăng xuất (Log Out)</b> và <b>Đăng nhập lại</b> là thanh Menu Bar mới sẽ xuất hiện đầy đủ.
</details>

<details>
<summary><b>2. Làm sao để chỉnh Dynamic Island nằm sát mép trên màn hình hơn?</b></summary>
<br>
Nhấp vào Dynamic Island để bung mở Hub -> Chuyển sang tab <b>Cài đặt (⚙️)</b> -> Kéo thanh <b>Top Offset (Y Margin)</b> từ 0px đến 120px tùy theo sở thích và độ phân giải màn hình của bạn.
</details>

<details>
<summary><b>3. Ứng dụng có tự động bắt nhạc từ trình duyệt web không?</b></summary>
<br>
Có! Mọi trình duyệt hiện đại (Google Chrome, Firefox, Brave, Edge...) khi phát YouTube/SoundCloud/ZingMP3 đều phát tín hiệu MPRIS2 qua D-Bus và Dynamic Island sẽ tự động hiển thị tên bài hát, nghệ sĩ và dải sóng âm.
</details>

---

## 📄 Bản Quyền & Giấy Phép

Dự án được phát hành mã nguồn mở dưới giấy phép **[MIT License](LICENSE)**. Bạn hoàn toàn tự do sử dụng, chỉnh sửa và chia sẻ cho cộng đồng người dùng Linux!

<div align="center">
⭐ <i>Nếu bạn thấy dự án hữu ích, hãy tặng 1 sao (Star) trên GitHub nhé!</i> ⭐
</div>
