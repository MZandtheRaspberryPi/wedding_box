"""
This script intitializes the RGB MAtrix with HUB75 protocol and starts a wireless network operating in AP mode to allow other computers to connect to the network. It offers an HTTP server to control the lights, switching between an automatic mode that scrolls through color gradients and a manual mode that allows pixel-level control. The manual mode must specify the color of each pixel as an array with length equal to the number of pixels, where the color is an integer that corresponds to a sampled color in HSV space.

Some example requests are below.
This sets the mode to manual. 0 for Mode would be the color gradient:
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"mode":1}' \
  http://10.42.0.1:5000/mode

# this sets the screen to be all one color
json_array=$(printf '243,%.0s' $(seq 1 4095))
json_array="${json_array}243"
curl --header "Content-Type: application/json" \
  --request POST \
  --data "{\"pixels\":[${json_array}]}" \
  http://10.42.0.1:5000/manual
"""
import adafruit_display_text.label
import adafruit_fancyled.adafruit_fancyled as fancy
from adafruit_httpserver import Server, Request, Response, POST, GET, Status, JSONResponse, Route
import board
import displayio
import framebufferio
import microcontroller
import os
import rgbmatrix
import terminalio
import time
import wifi

from constants import (MODE_GRADIENT_SCROLL, MODE_MANUAL, MODES, BIT_DEPTH_VALUE, UNIT_WIDTH,
                       UNIT_HEIGHT, NUM_COLORS, GRADIENT_CYCLE_TIME, WLAN_DEFAULT_SSID, WLAN_DEFAULT_PASS,
                       HTTP_MODE_ROUTE, HTTP_MODE_ROUTE, HTTP_JSON_MODE_KEY, HTTP_PIXEL_KEY,
                       N_PIXELS, HTTP_PORT, MANUAL_MODE_LOOP_TIME, HTTP_MANUAL_ROUTE, HTTP_ROUTE_WLAN,
                       HTTP_SSID_KEY, HTTP_PASS_KEY
                       )
from util import setup_wifi


class DisplayBox:
    def __init__(self):
        self.cur_mode = MODE_GRADIENT_SCROLL
        displayio.release_displays()
        self.matrix = rgbmatrix.RGBMatrix(
                width = UNIT_WIDTH,
                height = UNIT_HEIGHT,
                bit_depth = BIT_DEPTH_VALUE,
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
        self.display = framebufferio.FramebufferDisplay(self.matrix, auto_refresh=False)
        self.bitmap = displayio.Bitmap(UNIT_WIDTH, UNIT_HEIGHT, NUM_COLORS)
        self.palette = displayio.Palette(NUM_COLORS)
        self.tile_grid = displayio.TileGrid(self.bitmap, pixel_shader=self.palette)

        # creating our colors in HSV space and assigning to the color pallette
        # self.colors will hold packed colors RRGGBB or something like that
        self.colors = []
        # we step from 0.0 to 1.0 so that we have NUM_COLORS - 1 colors (black is reserved, hence the -1)
        self.step = 1/(NUM_COLORS - 1)
        # add black
        self.colors.append(fancy.CHSV(0, 0, 0))
        for i in range(NUM_COLORS-1):
            color = fancy.CHSV(i*self.step)  # 0 to 1.0
            self.colors.append(color)

        for i in range(0, NUM_COLORS):
            self.palette[i] = self.colors[i].pack()

        # counter for gradient scrolling to go through colors
        self.cur_idx = 0

        self.server, self.pool, self.is_ap = setup_wifi(os.getenv('CIRCUITPY_WIFI_SSID'),
                                            os.getenv('CIRCUITPY_WIFI_PASSWORD'),
                                            WLAN_DEFAULT_SSID, WLAN_DEFAULT_PASS )
        self.server.add_routes([
            Route(HTTP_MODE_ROUTE, [POST], self.set_mode),
            Route(HTTP_MANUAL_ROUTE, [POST], self.set_manual),
            Route(HTTP_MODE_ROUTE, [GET], self.get_mode),
            Route(HTTP_ROUTE_WLAN, [POST], self.set_wlan_details)
        ])

        print("starting server..")
        self.ip_addr_for_server = wifi.radio.ipv4_address if not self.is_ap else wifi.radio.ipv4_gateway_ap
        # startup the server
        try:
            self.server.start(str(self.ip_addr_for_server), port=HTTP_PORT)
            print(f"Listening on http://{self.ip_addr_for_server}:{self.server.port}")
            #  if the server fails to begin, restart the pico w
        except OSError:
            time.sleep(5)
            print("restarting..")
            microcontroller.reset()

        # show ip address
        ip_addr = str(self.ip_addr_for_server)
        ip_addr_list = ip_addr.split(".")
        ip_addr_l1 = ".".join(ip_addr_list[:2])+"."
        ip_addr_l2 = ".".join(ip_addr_list[2:])

        listen_str = f"{ip_addr_l1}\n{ip_addr_l2}\n{self.server.port}"
        line1 = adafruit_display_text.label.Label(
            terminalio.FONT,
            color=0xff0000,
            text=listen_str)
        line1.x = 0
        line1.y = 8

        # Put each line of text into a Group, then show that group.
        g = displayio.Group()
        g.append(line1)
        self.display.root_group = g

        self.refresh_display()

        time.sleep(8.0)

        # Create a Group and add the TileGrid to it
        self.group = displayio.Group()
        self.group.append(self.tile_grid)
        self.display.root_group = self.group

        print("colors:")
        for i in range(NUM_COLORS):
            color = self.colors[i]
            rgb = fancy.CRGB(color)
            print(f"{i}: HSV: ({color.hue}, {color.saturation}, {color.value}) RGB: ({rgb.red}, {rgb.green}, {rgb.blue})")

    def set_wlan_details(self, request: Request):
        req_json = request.json()
        for k in [HTTP_SSID_KEY, HTTP_PASS_KEY]:
            if k not in req_json.keys():
                return JSONResponse(request, status=Status(400, f"no key: {k}"), data={})
        wlan_ssid = req_json[HTTP_SSID_KEY]
        wlan_pass = req_json[HTTP_PASS_KEY]
        for v in [wlan_ssid, wlan_pass]:
            if type(v) != str:
                return JSONResponse(request, status=Status(400, f"expected {v} to be str"), data={})
        if len(wlan_pass) < 8 or len(wlan_pass) > 64:
            return JSONResponse(request, status=Status(400, f"expected password to be between 8 and 64 characters"), data={})
        # write to disk
        contents = f'''CIRCUITPY_WIFI_SSID = "{wlan_ssid}"
CIRCUITPY_WIFI_PASSWORD = "{wlan_pass}"'''
        with open("settings.toml", "w") as file_handle:
            file_handle.write(contents)
        return JSONResponse(request, data={})

    def get_mode(self, request: Request):
        return JSONResponse(request, {HTTP_JSON_MODE_KEY: self.cur_mode})

    def set_mode(self, request: Request):
        resp_json = request.json()
        if HTTP_JSON_MODE_KEY not in resp_json.keys():
            return JSONResponse(request, status=Status(400, f"no mode key: {HTTP_JSON_MODE_KEY}"), data={})
        new_mode = resp_json[HTTP_JSON_MODE_KEY]
        if new_mode not in MODES:
            return JSONResponse(request, status=Status(400, f"mode must be in {MODES}"), data={})
        self.cur_mode = new_mode
        return JSONResponse(request, data={HTTP_JSON_MODE_KEY: self.cur_mode})

    def set_manual(self, request: Request):
        print("setting manual")
        resp_json = request.json()

        if self.cur_mode != MODE_MANUAL:
            print("not manual mode")
            return JSONResponse(request, status=Status(400, f"not in manual mode {MODE_MANUAL}, cur mode is: {self.cur_mode}"), data={})

        if HTTP_PIXEL_KEY not in resp_json.keys():
            print("no pixels")
            return JSONResponse(request, status=Status(400, f"no pixels key: {HTTP_PIXEL_KEY}"), data={})
        pixels = resp_json[HTTP_PIXEL_KEY]
        if len(pixels) != N_PIXELS:
            print("expected more pixels")
            return JSONResponse(request, status=Status(400, f"expected {N_PIXELS} pixels"), data={})
        for i in range(N_PIXELS):
            if type(pixels[i]) != int:
                print("expect ints")
                return JSONResponse(request, status=Status(400, f"expected {i} pixel to be int"), data={})
            if pixels[i] > NUM_COLORS - 1 or pixels[i] < 0:
                print("pixel greater")
                return JSONResponse(request, status=Status(400, f"expected {i} pixel pixel to be 0 or greater / {NUM_COLORS-1} or less"), data={})
            row_idx = i // UNIT_HEIGHT
            col_idx = i % UNIT_WIDTH
            self.bitmap[col_idx, row_idx] = pixels[i]
        self.refresh_display()
        print("set manual")
        return JSONResponse(request, data={})

    def refresh_display(self):
        self.display.refresh()

    def update_color_gradient(self):
        for i in range(UNIT_WIDTH):
            for j in range(UNIT_HEIGHT):
                color_idx = (i + self.cur_idx) % (NUM_COLORS - 1)
                self.bitmap[j, i] = color_idx + 1

        if self.cur_idx < (NUM_COLORS - 1):
            self.cur_idx += 1
        else:
            self.cur_idx = 0
        # push the frame buffer to the display
        self.refresh_display()
        # control the time we spin for
        time.sleep(GRADIENT_CYCLE_TIME/NUM_COLORS)

    def handle_manual_loop(self):
        time.sleep(MANUAL_MODE_LOOP_TIME)

    def spin(self):
        # handle requests from http server
        try:
            self.server.poll()
        except ValueError as e: # for unparseable requests
            print("caught value error in server.poll")

        # if gradient mode, scroll
        if self.cur_mode == MODE_GRADIENT_SCROLL:
            self.update_color_gradient()
        # if manual mode it'll update the frame buffer in the http callback
        elif self.cur_mode == MODE_MANUAL:
            self.handle_manual_loop()


def main():

    display_box = DisplayBox()
    while True:
        display_box.spin()

main()
