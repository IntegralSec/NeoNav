#!/usr/bin/env python3

import time
import subprocess
import os
from PIL import Image, ImageDraw, ImageFont

# Import Waveshare driver
import sys
sys.path.append('/home/pi/e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd')
from waveshare_epd import epd2in13_V3

def get_ip_address():
    try:
        ip = subprocess.getoutput("hostname -I").split()[0]
    except:
        ip = "No IP"
    return ip

def get_wifi_status():
    ssid = subprocess.getoutput("iwgetid -r")
    return ssid if ssid else "disconnected"

def get_service_status(service):
    status = subprocess.getoutput(f"systemctl is-active {service}")
    return status

def get_cpu_load():
    load1, load5, load15 = os.getloadavg()
    return f"{load1:.2f} {load5:.2f} {load15:.2f}"

def get_cpu_temp():
    temp = subprocess.getoutput("vcgencmd measure_temp")
    return temp.replace("temp=", "")

def get_disk_usage():
    disk = subprocess.getoutput("df -h / | awk 'NR==2 {print $5}'")
    return disk

def get_mem_usage():
    mem = subprocess.getoutput("free -m | awk 'NR==2 {printf \"%.0f%%\", $3*100/$2 }'")
    return mem

def get_uptime():
    uptime = subprocess.getoutput("uptime -p")
    return uptime

def update_display(epd, lines):
    image = Image.new('1', (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    y = 0
    for line in lines:
        draw.text((0, y), line, font=font, fill=0)
        y += 12  # line height
    epd.display(epd.getbuffer(image))

def main():
    epd = epd2in13_V3.EPD()
    epd.init()
    epd.Clear(0xFF)

    try:
        while True:
            ip = get_ip_address()
            wifi = get_wifi_status()
            flask_status = get_service_status("flaskrobot.service")
            nginx_status = get_service_status("nginx")
            cpu_load = get_cpu_load()
            cpu_temp = get_cpu_temp()
            disk_usage = get_disk_usage()
            mem_usage = get_mem_usage()
            uptime = get_uptime()

            lines = [
                f"IP: {ip}",
                f"WLAN: {wifi}",
                f"Flask: {flask_status}",
                f"nginx: {nginx_status}",
                f"Load: {cpu_load}",
                f"Temp: {cpu_temp}",
                f"Disk: {disk_usage}",
                f"Mem: {mem_usage}",
                f"Up: {uptime}"
            ]

            update_display(epd, lines)
            time.sleep(30)

    except KeyboardInterrupt:
        print("Interrupted, clearing display...")
        epd.init()
        epd.Clear(0xFF)
        epd.sleep()

if __name__ == "__main__":
    main()
