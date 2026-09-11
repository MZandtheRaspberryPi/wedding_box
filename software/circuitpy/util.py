
from adafruit_httpserver import Server
import ipaddress
import socketpool
import time
import wifi

def setup_wifi(ssid_name: str, ssid_pass: str, default_ssid_name: str, default_ssid_pass):
    is_ap = False
    try:
        wifi.radio.connect(ssid=ssid_name,
                        password=ssid_pass,
                        timeout=3.0)
    except OSError as e:
        print(f"couldn't connect to {ssid_name}")
        is_ap = True
        print("staring ap mode")
        wifi.radio.start_ap(ssid=default_ssid_name, password=default_ssid_pass)
        print("started network")
        print(f"ap active: {wifi.radio.ap_active}")
        wifi.radio.set_ipv4_address_ap(ipv4=ipaddress.IPv4Address("10.42.0.1"), netmask=ipaddress.IPv4Address("255.255.255.0"), gateway=ipaddress.IPv4Address("10.42.0.1"))
        wifi.radio.start_dhcp_ap()
    print("Connected!")
    print("My IP address:", wifi.radio.ipv4_address)
    print(f"gateway: {wifi.radio.ipv4_gateway_ap}")
    pool = socketpool.SocketPool(wifi.radio)
    server = Server(pool, "/static")
    return server, pool, is_ap
