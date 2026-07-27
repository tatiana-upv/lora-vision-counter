from lora import *
from time import sleep_ms

lora = Lora(band=BAND_EU868, poll_ms=1000, debug=False)

appEui = "00000000000000AA"
appKey = "24D83E922BE80ECD38F85B1FAD696C77"

print("Firmware:", lora.get_fw_version())
print("Device EUI:", lora.get_device_eui())

try:
    lora.join_OTAA(appEui, appKey, timeout=60000)
    sleep_ms(3000)
except Exception as e:
    print("Join error:", e)

if lora.get_join_status():
    lora.set_port(3)
    try:
        if lora.send_data("Hello world!", False):
            print("Hello world enviado.")
        else:
            print("No se pudo enviar.")
    except Exception as e:
        print("Send error:", e)
else:
    print("No unido, no se envía.")

while True:
    sleep_ms(1000)
