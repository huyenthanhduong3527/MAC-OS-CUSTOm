#!/usr/bin/env python3

with open("src/utils/i18n.py", "r", encoding="utf-8") as f:
    text = f.read()

# Fix VI
text = text.replace(
    '"airdrop_qr_scan_desc": "Mở ứng dụng <b>Camera</b> trên iPhone / iPad\nvà quét mã QR bên dưới để mở AirDrop Web ngay lập tức.",',
    '"airdrop_qr_scan_desc": "Mở ứng dụng <b>Camera</b> trên iPhone / iPad\\nvà quét mã QR bên dưới để mở AirDrop Web ngay lập tức.",'
)

# Fix EN
text = text.replace(
    '"airdrop_qr_scan_desc": "Open the <b>Camera</b> app on your iPhone / iPad\nand scan the QR code below to connect.",',
    '"airdrop_qr_scan_desc": "Open the <b>Camera</b> app on your iPhone / iPad\\nand scan the QR code below to connect.",'
)

# Fix JA
text = text.replace(
    '"airdrop_qr_scan_desc": "iPhoneまたはiPadで<b>カメラ</b>を開き、\n下のQRコードをスキャンして接続します。",',
    '"airdrop_qr_scan_desc": "iPhoneまたはiPadで<b>カメラ</b>を開き、\\n下のQRコードをスキャンして接続します。",'
)

with open("src/utils/i18n.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Fixed newlines in src/utils/i18n.py")
