#!/usr/bin/python3
"""Publish the Pi's LAN names via mDNS: kino.local (Jellyfin), logs.local (Grafana), home.local (Home Assistant).

Each name gets A (Ethernet IPv4, else Wi-Fi) + AAAA (stable LAN-only ULA IPv6), plus an HTTP service.
Both point at nginx on port 80, which picks the site by Host header.

The AAAA record matters: without it macOS waits ~5 s for an IPv6 answer on every lookup.
Only ULA (fd00::/8) addresses are published — they stay fixed, unlike the ISP-assigned global prefix.
"""
import ipaddress, signal, socket, subprocess, time
from zeroconf import IPVersion, ServiceInfo, Zeroconf

SITES = [("kino.local.", "Kino (Jellyfin)"), ("logs.local.", "Logs (Grafana)"), ("home.local.", "Home (Home Assistant)")]

def iface_ip(iface):
    out = subprocess.run(["ip", "-4", "-o", "addr", "show", iface], capture_output=True, text=True).stdout
    return out.split()[3].split("/")[0] if out.strip() else None

def iface_ula(iface):
    out = subprocess.run(["ip", "-6", "-o", "addr", "show", iface, "scope", "global", "-temporary"],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        addr = ipaddress.ip_address(line.split()[3].split("/")[0])
        if addr in ipaddress.ip_network("fd00::/8"):
            return str(addr)
    return None

# Prefer the cable; fall back to Wi-Fi. A NetworkManager dispatcher hook restarts this on link changes.
iface = "eth0" if iface_ip("eth0") else "wlan0"
ip4, ip6 = iface_ip(iface), iface_ula(iface)
addrs = [socket.inet_pton(socket.AF_INET, ip4)] + ([socket.inet_pton(socket.AF_INET6, ip6)] if ip6 else [])
infos = [ServiceInfo("_http._tcp.local.", f"{title}._http._tcp.local.", addresses=addrs, port=80, server=host)
         for host, title in SITES]
zc = Zeroconf(interfaces=[ip4] + ([ip6] if ip6 else []), ip_version=IPVersion.All if ip6 else IPVersion.V4Only)
for info in infos:
    zc.register_service(info, allow_name_change=True)
print(", ".join(h.rstrip(".") for h, _ in SITES) + f" -> {ip4}" + (f", {ip6}" if ip6 else ""), flush=True)

def stop(*_):
    for info in infos:
        zc.unregister_service(info)
    zc.close()
    exit(0)

signal.signal(signal.SIGTERM, stop)
while True:
    time.sleep(3600)
