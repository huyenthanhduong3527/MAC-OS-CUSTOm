import UPowerGlib from "gi://UPowerGlib";
const client = new UPowerGlib.Client();
const dev = client.get_display_device();
print("ESM UPower ok, is_present:", dev.is_present);
