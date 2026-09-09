"""
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"mode":1}' \
  http://10.42.0.1:5000/mode


json_array=$(printf '243,%.0s' $(seq 1 4095))
json_array="${json_array}243"
curl --header "Content-Type: application/json" \
  --request POST \
  --data "{\"pixels\":[${json_array}]}" \
  http://10.42.0.1:5000/manual
"""

from adafruit_httpserver import Server, Request, Response, POST, Status
from adafruit_httpserver import Route, POST, GET, Request, Response, JSONResponse
import time
import os
import board
import displayio
import framebufferio
import rgbmatrix
import adafruit_fancyled.adafruit_fancyled as fancy
import ipaddress
import wifi
import socketpool

# 0 is color gradient
# 1 is manual
MODE = 0

def setup_wifi(ssid_name: str, ssid_pass: str):
    wifi.radio.start_ap(ssid=ssid_name, password=ssid_pass)
    print("started network")
    print(f"ap active: {wifi.radio.ap_active}")
    wifi.radio.set_ipv4_address_ap(ipv4=ipaddress.IPv4Address("10.42.0.1"), netmask=ipaddress.IPv4Address("255.255.255.0"), gateway=ipaddress.IPv4Address("10.42.0.1"))
    wifi.radio.start_dhcp_ap()
    print(f"gateway: {wifi.radio.ipv4_gateway_ap}")
    pool = socketpool.SocketPool(wifi.radio)
    server = Server(pool, "/static")
    return server, pool

def get_mode(request: Request):
    print(request.json())
    return JSONResponse(request, {"mode": MODE})
    
def set_mode(request: Request):
    global MODE
    print(request.json())
    resp_json = request.json()
    if "mode" not in resp_json.keys():
        return JSONResponse(request, status=Status(400, "no mode key"), data={})
    new_mode = resp_json["mode"]
    if new_mode not in [0, 1]:
        return JSONResponse(request, status=Status(400, "mode must be 0 or 1"), data={})
    MODE = new_mode
    return JSONResponse(request, data={"mode": MODE})


# ------------------------------------------------
# REQUIRED → clear any previous display buses
# ------------------------------------------------
displayio.release_displays()

bit_depth_value = 4
unit_width = 64
unit_height = 64

matrix = rgbmatrix.RGBMatrix(
    width = unit_width,
    height = unit_height,
    bit_depth = bit_depth_value,
    # (R1,G1,B1,R2,G2,B2...)
    rgb_pins = [board.GP0, board.GP1, board.GP2, board.GP3, board.GP4, board.GP5],
    # (A,B,C,D...)
    addr_pins = [board.GP6, board.GP7, board.GP8, board.GP9, board.GP10],
    clock_pin = board.GP11,
    latch_pin = board.GP12,
    output_enable_pin = board.GP13,
    tile = 1,
    serpentine = True,
    doublebuffer = True,
)

DISPLAY = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)


# Create a palette with RGB color order
# we take one for black, the first...
NUM_COLORS = 256
# Create a bitmap for the RGB matrix
bitmap = displayio.Bitmap(unit_width, unit_height, NUM_COLORS)

palette = displayio.Palette(NUM_COLORS)

# Create a TileGrid to render the bitmap on the display
tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)

# Create a Group and add the TileGrid to it
group = displayio.Group()
group.append(tile_grid)
DISPLAY.root_group = group

colors = []
cur_interp = 0.0
step = 1/(NUM_COLORS - 1)
colors.append(fancy.CHSV(0, 0, 0).pack())
for i in range(NUM_COLORS-1):
    color = fancy.CHSV(i*step)  # 0 to 1.0
    colors.append(color.pack())
    
for i in range(0, NUM_COLORS):
    palette[i] = colors[i]
    
def set_manual(request: Request):
    global bitmap
    resp_json = request.json()
    if "pixels" not in resp_json.keys():
        return JSONResponse(request, status=Status(400, "no pixels key"), data={})
    pixels = resp_json["pixels"]
    expected_len = unit_width * unit_height
    if len(pixels) != expected_len:
        return JSONResponse(request, status=Status(400, f"expected {expected_len} pixels"), data={})
    for i in range(expected_len):
        row_idx = i // unit_height
        col_idx = i % unit_width
        bitmap[row_idx, col_idx] = pixels[i]
    return JSONResponse(request, data={})

cur_idx = 0
cycle_time = 20.0

server, pool = setup_wifi("light_box", "light_box")
server.add_routes([
            Route("/mode", [POST], set_mode),
            Route("/manual", [POST], set_manual),
            Route("/mode", [GET], get_mode)
        ])

print("starting server..")
# startup the server
try:
    server.start(str(wifi.radio.ipv4_gateway_ap), port=5000)
    print(f"Listening on http://{wifi.radio.ipv4_gateway_ap}:{server.port}")
    #  if the server fails to begin, restart the pico w
except OSError:
    time.sleep(5)
    print("restarting..")
    microcontroller.reset()



while True:
    
    if MODE == 0:
        for i in range(unit_width):
            for j in range(unit_height):
                color_idx = (i + cur_idx) % (NUM_COLORS - 1)
                bitmap[j, i] = color_idx + 1
        
        if cur_idx < (NUM_COLORS - 1):
            cur_idx += 1 
        else:
            cur_idx = 0
        time.sleep(cycle_time/NUM_COLORS)
    elif MODE == 1:
        pass
    DISPLAY.refresh()
    
    try:
        server.poll()
    except ValueError as e: # for unparseable requests
        print("caught value error in server.poll")
    
    
    
    


