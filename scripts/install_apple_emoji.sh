#!/usr/bin/env bash
# Script to install Apple Color Emoji on Ubuntu / Linux
# and configure fontconfig for macOS-standard emoji rendering.

set -e

FONT_DIR="${HOME}/.local/share/fonts"
FONTCONFIG_DIR="${HOME}/.config/fontconfig"
EMOJI_URL="https://github.com/samuelngs/apple-emoji-ttf/releases/download/macos-26-20260722-484daf4e/AppleColorEmoji-Linux.ttf"

echo "=========================================================="
echo "  🍎 Installing Apple Color Emoji for Ubuntu/Linux"
echo "=========================================================="

mkdir -p "${FONT_DIR}" "${FONTCONFIG_DIR}"

# 1. Download Apple Color Emoji font
if [ ! -f "${FONT_DIR}/AppleColorEmoji.ttf" ]; then
    echo "⬇️  Downloading Apple Color Emoji (macOS Edition)..."
    curl -fSL "${EMOJI_URL}" -o "${FONT_DIR}/AppleColorEmoji.ttf"
else
    echo "✅ Apple Color Emoji font already exists in ${FONT_DIR}/AppleColorEmoji.ttf"
fi

# 2. Configure fontconfig to prioritize Apple Color Emoji
echo "⚙️  Configuring ~/.config/fontconfig/fonts.conf..."
cat << 'EOF' > "${FONTCONFIG_DIR}/fonts.conf"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <!-- Default emoji family -->
  <match target="pattern">
    <test qual="any" name="family"><string>emoji</string></test>
    <edit name="family" mode="assign" binding="same">
      <string>Apple Color Emoji</string>
    </edit>
  </match>

  <alias binding="strong">
    <family>emoji</family>
    <prefer>
      <family>Apple Color Emoji</family>
    </prefer>
    <default><family>Apple Color Emoji</family></default>
  </alias>

  <!-- Replace Noto Color Emoji with Apple Color Emoji -->
  <match target="pattern">
    <test qual="any" name="family"><string>Noto Color Emoji</string></test>
    <edit name="family" mode="assign" binding="same">
      <string>Apple Color Emoji</string>
    </edit>
  </match>

  <!-- Replace Microsoft & Android emojis with Apple Color Emoji -->
  <match target="pattern">
    <test qual="any" name="family"><string>Segoe UI Emoji</string></test>
    <edit name="family" mode="assign" binding="same">
      <string>Apple Color Emoji</string>
    </edit>
  </match>
  <match target="pattern">
    <test qual="any" name="family"><string>Segoe UI Symbol</string></test>
    <edit name="family" mode="assign" binding="same">
      <string>Apple Color Emoji</string>
    </edit>
  </match>
  <match target="pattern">
    <test qual="any" name="family"><string>Twitter Color Emoji</string></test>
    <edit name="family" mode="assign" binding="same">
      <string>Apple Color Emoji</string>
    </edit>
  </match>
  <match target="pattern">
    <test qual="any" name="family"><string>Android Emoji</string></test>
    <edit name="family" mode="assign" binding="same">
      <string>Apple Color Emoji</string>
    </edit>
  </match>
  <match target="pattern">
    <test qual="any" name="family"><string>JoyPixels</string></test>
    <edit name="family" mode="assign" binding="same">
      <string>Apple Color Emoji</string>
    </edit>
  </match>

  <!-- Add Apple Color Emoji as fallback for standard font families -->
  <match target="pattern">
    <test qual="any" name="family"><string>sans-serif</string></test>
    <edit name="family" mode="append" binding="weak">
      <string>Apple Color Emoji</string>
    </edit>
  </match>
  <match target="pattern">
    <test qual="any" name="family"><string>serif</string></test>
    <edit name="family" mode="append" binding="weak">
      <string>Apple Color Emoji</string>
    </edit>
  </match>
  <match target="pattern">
    <test qual="any" name="family"><string>monospace</string></test>
    <edit name="family" mode="append" binding="weak">
      <string>Apple Color Emoji</string>
    </edit>
  </match>
</fontconfig>
EOF

# 3. Rebuild font cache
echo "🔄 Updating font cache (fc-cache)..."
fc-cache -f -v "${FONT_DIR}" >/dev/null 2>&1

echo "=========================================================="
echo "  🎉 Apple Color Emoji has been successfully installed!"
echo "  👉 Verification:"
fc-match emoji
echo "  💡 Note: Please restart your browser (Chrome/Firefox) to see changes."
echo "=========================================================="
