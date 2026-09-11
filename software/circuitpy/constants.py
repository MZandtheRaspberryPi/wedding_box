
MODE_GRADIENT_SCROLL = 0
MODE_MANUAL = 1
MODES = [MODE_GRADIENT_SCROLL, MODE_MANUAL]
BIT_DEPTH_VALUE = 4
UNIT_WIDTH = 64
UNIT_HEIGHT = 64
N_PIXELS = UNIT_WIDTH * UNIT_HEIGHT
# number of colors in our pallatte to pick from when displaying
# we will sample linearly in HSV space by going from h=0.0 to h=1.0 with NUM_COLORS-1 steps (we take 1 color for off/black)
NUM_COLORS = 256
GRADIENT_CYCLE_TIME = 20.0
MANUAL_MODE_LOOP_TIME = 1 / 100
WLAN_SSID = "light_box"
WLAN_PASS = "light_box"

HTTP_MODE_ROUTE = "/mode"
HTTP_MANUAL_ROUTE = "/manual"
HTTP_JSON_MODE_KEY = "mode"
HTTP_PIXEL_KEY = "pixels"
HTTP_PORT = 5000
