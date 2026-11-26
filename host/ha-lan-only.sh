#!/bin/sh
# Keep Home Assistant's ports LAN-only. HA runs with network_mode: host and listens on every address,
# including the Pi's public IPv6, so the FritzBox would be the only thing standing in the way otherwise.
#   8123        web UI / API
#   18555       go2rtc WebRTC (camera streams)
#   1900, 5353  SSDP / mDNS answers (discovery is meant for the home network only; also covers
#               avahi, kino-mdns and Jellyfin's SSDP on the same ports)
# Installed as /usr/local/sbin/ha-lan-only.sh, run by ha-lan-only.service at boot (before Docker).
set -e
PORTS=8123,18555,1900,5353

for ipt in iptables ip6tables; do
  $ipt -N HA-LAN-ONLY 2>/dev/null || $ipt -F HA-LAN-ONLY
  $ipt -A HA-LAN-ONLY -i lo -j RETURN
done

iptables -A HA-LAN-ONLY -s 192.168.178.0/24 -j RETURN
iptables -A HA-LAN-ONLY -j DROP

ip6tables -A HA-LAN-ONLY -s fd00::/8 -j RETURN            # home network ULA (stable, never routed outside)
ip6tables -A HA-LAN-ONLY -s fe80::/10 -j RETURN           # link-local
ip6tables -A HA-LAN-ONLY -j DROP

for ipt in iptables ip6tables; do
  # drop jumps left by an older port list, then add the current ones
  $ipt -S INPUT | grep -- '-j HA-LAN-ONLY' | sed 's/^-A //' | while read -r rule; do $ipt -D INPUT $rule; done
  for proto in tcp udp; do
    $ipt -I INPUT -p $proto -m multiport --dports $PORTS -j HA-LAN-ONLY
  done
done
