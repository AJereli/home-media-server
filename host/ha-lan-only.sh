#!/bin/sh
# Keep Home Assistant's ports LAN-only. HA runs with network_mode: host and listens on every address,
# including the Pi's public IPv6, so the FritzBox would be the only thing standing in the way otherwise.
#   8123        web UI / API
#   18555       go2rtc WebRTC (camera streams)
# Installed as /usr/local/sbin/ha-lan-only.sh, run by ha-lan-only.service at boot (before Docker).
set -e
PORTS=8123,18555

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
  for proto in tcp udp; do
    $ipt -C INPUT -p $proto -m multiport --dports $PORTS -j HA-LAN-ONLY 2>/dev/null \
      || $ipt -I INPUT -p $proto -m multiport --dports $PORTS -j HA-LAN-ONLY
  done
done
