"""Generate the Pi dashboards (Raspberry Pi, Containers) for Grafana provisioning.

Usage: python3 monitoring/grafana/generate-dashboards.py
Grafana picks up the changed JSON within ~10 s, no restart needed. Node Exporter Full is grafana.com #1860.
"""
import json, sys, pathlib

OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).parent / "provisioning" / "dashboards"
DS = {"type": "prometheus", "uid": "prometheus"}
NODE = 'job="node-exporter",instance="raspberrypi"'
_id = 0


def nid():
    global _id
    _id += 1
    return _id


def tgt(expr, legend="", instant=False, ref=None, fmt=None):
    t = {"datasource": DS, "expr": expr, "legendFormat": legend or "__auto", "refId": ref or "A"}
    if instant:
        t.update(instant=True, range=False)
    if fmt:
        t["format"] = fmt
    return t


def thresholds(*steps):
    """steps: (color, value) pairs after the base green."""
    return {"mode": "absolute", "steps": [{"color": "green", "value": None}] + [{"color": c, "value": v} for c, v in steps]}


def stat(title, expr, x, y, w=3, h=4, unit="none", th=None, decimals=None, desc="", minv=None, maxv=None, graph=True):
    d = {"unit": unit, "thresholds": th or thresholds(), "color": {"mode": "thresholds"}}
    if desc.startswith("Needs the memory cgroup"):
        d["noValue"] = "off in kernel"
    if decimals is not None:
        d["decimals"] = decimals
    if minv is not None:
        d["min"] = minv
    if maxv is not None:
        d["max"] = maxv
    return {
        "id": nid(), "type": "stat", "title": title, "description": desc, "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [tgt(expr, ref="A")],
        "fieldConfig": {"defaults": d, "overrides": []},
        "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                    "colorMode": "value", "graphMode": "area" if graph else "none", "textMode": "auto",
                    "justifyMode": "center", "orientation": "auto", "wideLayout": True},
    }


def ts(title, targets, x, y, w=12, h=8, unit="none", stack=False, desc="", minv=None, maxv=None,
       overrides=None, fill=10, th=None, th_style=None, legend_calcs=("mean", "max", "lastNotNull")):
    custom = {"drawStyle": "line", "lineWidth": 1, "fillOpacity": fill, "showPoints": "never",
              "spanNulls": True, "stacking": {"mode": "normal" if stack else "none", "group": "A"},
              "axisSoftMin": 0}
    if th_style:
        custom["thresholdsStyle"] = {"mode": th_style}
    d = {"unit": unit, "custom": custom, "color": {"mode": "palette-classic"}}
    if "Needs the memory cgroup" in desc:
        d["noValue"] = "Needs the memory cgroup: off in the Pi kernel by default"
    if th:
        d["thresholds"] = th
    if minv is not None:
        d["min"] = minv
    if maxv is not None:
        d["max"] = maxv
    return {
        "id": nid(), "type": "timeseries", "title": title, "description": desc, "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [tgt(t[0], t[1], ref=chr(65 + i)) for i, t in enumerate(targets)],
        "fieldConfig": {"defaults": d, "overrides": overrides or []},
        "options": {"legend": {"displayMode": "table", "placement": "bottom", "calcs": list(legend_calcs)},
                    "tooltip": {"mode": "multi", "sort": "desc"}},
    }


def row(title, y):
    return {"id": nid(), "type": "row", "title": title, "collapsed": False, "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []}


def negative_y(regex):
    return {"matcher": {"id": "byRegexp", "options": regex},
            "properties": [{"id": "custom.transform", "value": "negative-Y"}]}


def dashboard(uid, title, panels, tags, links):
    return {
        "uid": uid, "title": title, "tags": tags, "timezone": "browser", "editable": True,
        "schemaVersion": 39, "version": 1, "refresh": "30s", "time": {"from": "now-6h", "to": "now"},
        "fiscalYearStartMonth": 0, "graphTooltip": 1, "liveNow": False,
        "templating": {"list": []}, "annotations": {"list": []},
        "links": links, "panels": panels,
    }


LINKS = [{"type": "dashboards", "tags": ["pi"], "asDropdown": False, "title": "Dashboards", "includeVars": False,
          "keepTime": True, "icon": "external link", "targetBlank": False}]

# ---------------------------------------------------------------- Raspberry Pi
CPU_BUSY = f'100 * (1 - avg(rate(node_cpu_seconds_total{{{NODE},mode="idle"}}[$__rate_interval])))'
CORES = f'count(count by (cpu) (node_cpu_seconds_total{{{NODE}}}))'
MEM_USED = f'100 * (1 - node_memory_MemAvailable_bytes{{{NODE}}} / node_memory_MemTotal_bytes{{{NODE}}})'
SWAP_USED = f'100 * (1 - node_memory_SwapFree_bytes{{{NODE}}} / node_memory_SwapTotal_bytes{{{NODE}}})'
CPU_TEMP = f'max(node_thermal_zone_temp{{{NODE},type="cpu-thermal"}})'
def fs_used(mp):
    return (f'100 * (1 - node_filesystem_avail_bytes{{{NODE},mountpoint="{mp}"}}'
            f' / node_filesystem_size_bytes{{{NODE},mountpoint="{mp}"}})')
DISKS = 'device=~"mmcblk0|sda"'
NICS = 'device=~"eth0|wlan0"'
REAL_FS = 'mountpoint=~"/|/mnt/media|/boot/firmware"'

pct = thresholds(("orange", 75), ("red", 90))
y = 0
pi = [
    stat("Uptime", f'time() - node_boot_time_seconds{{{NODE}}}', 0, y, unit="s", decimals=1, graph=False),
    stat("CPU", CPU_BUSY, 3, y, unit="percent", th=pct, decimals=0, minv=0, maxv=100),
    stat("Load (1 min)", f'node_load1{{{NODE}}}', 6, y, th=thresholds(("orange", 3), ("red", 4)), decimals=2,
         desc="Average number of runnable/waiting processes. The Pi has 4 cores: above 4 means work is queuing (often waiting for the SD card)."),
    stat("RAM used", MEM_USED, 9, y, unit="percent", th=pct, decimals=0, minv=0, maxv=100),
    stat("Swap used", SWAP_USED, 12, y, unit="percent", decimals=0, minv=0, maxv=100,
         th={"mode": "absolute", "steps": [{"color": "blue", "value": None}]},
         desc="Swap is zram (compressed RAM, 2 GB). A full swap alone is harmless: idle pages parked there. "
              "What hurts is constant traffic, see the Swap traffic panel."),
    stat("CPU temperature", CPU_TEMP, 15, y, unit="celsius", th=thresholds(("orange", 70), ("red", 80)), decimals=1,
         desc="The Pi 5 starts throttling at about 85 °C."),
    stat("SD card used", fs_used("/"), 18, y, unit="percent", th=pct, decimals=0, minv=0, maxv=100, graph=False,
         desc="System disk (/). When it fills up, Docker and Prometheus stop working."),
    stat("HDD used", fs_used("/mnt/media"), 21, y, unit="percent", th=pct, decimals=0, minv=0, maxv=100, graph=False,
         desc="Media drive (/mnt/media): films, series, downloads."),
]
y += 4
pi += [row("CPU & memory", y)]
y += 1
pi += [
    ts("CPU usage by type", [
        (f'100 * sum by (mode) (rate(node_cpu_seconds_total{{{NODE},mode!="idle"}}[$__rate_interval])) / scalar({CORES})', "{{mode}}"),
    ], 0, y, unit="percent", stack=True, minv=0, maxv=100, fill=40,
       desc="iowait = the CPU is idle because it waits for a disk. High iowait usually means the SD card is struggling."),
    ts("Load average", [
        (f'node_load1{{{NODE}}}', "1 min"), (f'node_load5{{{NODE}}}', "5 min"), (f'node_load15{{{NODE}}}', "15 min"),
        (CORES, "cores"),
    ], 12, y, minv=0, fill=0, overrides=[
        {"matcher": {"id": "byName", "options": "cores"},
         "properties": [{"id": "custom.lineStyle", "value": {"fill": "dash", "dash": [10, 10]}},
                        {"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}}]}],
       desc="Above the red line (number of cores) processes are waiting."),
]
y += 8
pi += [
    ts("Memory", [
        (f'node_memory_MemTotal_bytes{{{NODE}}} - node_memory_MemAvailable_bytes{{{NODE}}}', "used"),
        (f'node_memory_Buffers_bytes{{{NODE}}} + node_memory_Cached_bytes{{{NODE}}}', "cache (freed when needed)"),
        (f'node_memory_MemFree_bytes{{{NODE}}}', "free"),
        (f'node_memory_SwapTotal_bytes{{{NODE}}} - node_memory_SwapFree_bytes{{{NODE}}}', "swap used"),
    ], 0, y, w=8, unit="bytes", minv=0, overrides=[
        {"matcher": {"id": "byName", "options": "swap used"},
         "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}}, {"id": "custom.fillOpacity", "value": 0}]}]),
    ts("Swap traffic", [
        (f'rate(node_vmstat_pswpin{{{NODE}}}[$__rate_interval]) * 4096', "in"),
        (f'rate(node_vmstat_pswpout{{{NODE}}}[$__rate_interval]) * 4096', "out"),
    ], 8, y, w=8, unit="Bps", minv=0,
       desc="Pages moved between RAM and swap (zram). Short bursts are fine; sustained traffic means RAM is too tight.",
       th=thresholds(("red", 5 * 1024 * 1024)), th_style="line"),
    ts("Temperature", [
        (CPU_TEMP, "CPU"),
    ], 16, y, w=8, unit="celsius", fill=20, th=thresholds(("orange", 70), ("red", 80)), th_style="line"),
]
y += 8
pi += [row("Disks", y)]
y += 1
pi += [
    {
        "id": nid(), "type": "bargauge", "title": "Disk space used", "datasource": DS,
        "gridPos": {"x": 0, "y": y, "w": 8, "h": 8},
        "targets": [tgt(f'100 * (1 - node_filesystem_avail_bytes{{{NODE},{REAL_FS}}} / node_filesystem_size_bytes{{{NODE},{REAL_FS}}})',
                        "{{mountpoint}}", instant=True, ref="A")],
        "fieldConfig": {"defaults": {"unit": "percent", "min": 0, "max": 100, "decimals": 0, "thresholds": pct,
                                     "color": {"mode": "thresholds"}}, "overrides": []},
        "options": {"orientation": "horizontal", "displayMode": "gradient", "showUnfilled": True,
                    "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}, "valueMode": "color",
                    "namePlacement": "top", "sizing": "auto"},
    },
    {
        "id": nid(), "type": "table", "title": "Free space", "datasource": DS,
        "gridPos": {"x": 0, "y": y + 8, "w": 8, "h": 5},
        "targets": [
            tgt(f'node_filesystem_avail_bytes{{{NODE},{REAL_FS}}}', instant=True, ref="A", fmt="table"),
            tgt(f'node_filesystem_size_bytes{{{NODE},{REAL_FS}}}', instant=True, ref="B", fmt="table"),
        ],
        "transformations": [
            {"id": "merge", "options": {}},
            {"id": "organize", "options": {
                "excludeByName": {"Time": True, "__name__": True, "instance": True, "job": True, "fstype": True, "device": True},
                "indexByName": {"mountpoint": 0, "Value #A": 1, "Value #B": 2},
                "renameByName": {"mountpoint": "Mount", "device": "Device", "Value #A": "Free", "Value #B": "Size"}}},
        ],
        "fieldConfig": {"defaults": {"unit": "bytes", "decimals": 1}, "overrides": []},
        "options": {"showHeader": True, "cellHeight": "sm", "footer": {"show": False}},
    },
    ts("Disk throughput (read up / write down)", [
        (f'rate(node_disk_read_bytes_total{{{NODE},{DISKS}}}[$__rate_interval])', "{{device}} read"),
        (f'rate(node_disk_written_bytes_total{{{NODE},{DISKS}}}[$__rate_interval])', "{{device}} write"),
    ], 8, y, w=16, h=7, unit="Bps", overrides=[negative_y(".*write")],
       desc="mmcblk0 = SD card (system, Docker), sda = media HDD."),
    ts("Disk busy time", [
        (f'100 * rate(node_disk_io_time_seconds_total{{{NODE},{DISKS}}}[$__rate_interval])', "{{device}}"),
    ], 8, y + 7, w=16, h=6, unit="percent", minv=0, maxv=100, fill=20,
       th=thresholds(("red", 90)), th_style="line",
       desc="Share of time the disk was busy. An SD card stuck near 100% is what freezes the Pi."),
]
y += 13
pi += [row("Network", y)]
y += 1
pi += [
    ts("Network traffic (in up / out down)", [
        (f'rate(node_network_receive_bytes_total{{{NODE},{NICS}}}[$__rate_interval]) * 8', "{{device}} in"),
        (f'rate(node_network_transmit_bytes_total{{{NODE},{NICS}}}[$__rate_interval]) * 8', "{{device}} out"),
    ], 0, y, unit="bps", overrides=[negative_y(".* out")],
       desc="Physical interfaces of the Pi. Torrent traffic is included here (encrypted, inside the VPN tunnel)."),
    ts("Network errors & drops", [
        (f'rate(node_network_receive_errs_total{{{NODE},{NICS}}}[$__rate_interval])', "{{device}} rx errors"),
        (f'rate(node_network_transmit_errs_total{{{NODE},{NICS}}}[$__rate_interval])', "{{device}} tx errors"),
        (f'rate(node_network_receive_drop_total{{{NODE},{NICS}}}[$__rate_interval])', "{{device}} rx drops"),
    ], 12, y, unit="pps", minv=0, fill=0),
]

# ---------------------------------------------------------------- Containers
C = 'name!=""'
# These run on the host network, so cAdvisor reports the whole Pi's traffic for them.
CN = 'name!="",name!~"node-exporter|movies-downloader-bot-bot-1"'
# Raspberry Pi OS boots with cgroup_disable=memory: no per-container memory, and SD writes can't be
# attributed to containers. Such panels show this text until cgroup_enable=memory is set (+ reboot).
NO_MEMCG = "Needs the memory cgroup (off in the Pi kernel by default)"
RUNNING = f'time() - container_last_seen{{{C}}} < 60'
y = 0
cont = [
    stat("Running containers", f'count({RUNNING})', 0, y, w=4, graph=False),
    stat("CPU used by containers", f'100 * sum(rate(container_cpu_usage_seconds_total{{{C}}}[$__rate_interval])) / scalar(count(count by (cpu) (node_cpu_seconds_total{{{NODE}}})))',
         4, y, w=5, unit="percent", th=pct, decimals=1, desc="Share of the whole Pi (all 4 cores)."),
    stat("RAM used by containers", f'sum(container_memory_working_set_bytes{{{C}}}) > 0', 9, y, w=5, unit="bytes", decimals=1,
         desc=NO_MEMCG),
    {
        "id": nid(), "type": "stat", "title": "Monitoring targets", "datasource": DS,
        "gridPos": {"x": 14, "y": y, "w": 10, "h": 4},
        "targets": [tgt("up", "{{job}}", ref="A")],
        "fieldConfig": {"defaults": {
            "mappings": [{"type": "value", "options": {"0": {"text": "DOWN", "color": "red"}, "1": {"text": "UP", "color": "green"}}}],
            "thresholds": thresholds(), "color": {"mode": "thresholds"}}, "overrides": []},
        "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                    "colorMode": "background", "graphMode": "none", "textMode": "value_and_name", "justifyMode": "center"},
    },
]
y += 4

def col(name, unit, decimals=1, gauge=False, maxv=None):
    props = [{"id": "unit", "value": unit}, {"id": "decimals", "value": decimals}]
    if gauge:
        props += [{"id": "custom.cellOptions", "value": {"type": "gauge", "mode": "basic", "valueDisplayMode": "text"}},
                  {"id": "min", "value": 0}]
        if maxv:
            props.append({"id": "max", "value": maxv})
    return {"matcher": {"id": "byName", "options": name}, "properties": props}

cont.append({
    "id": nid(), "type": "table", "title": "Containers now", "datasource": DS,
    "description": "Transmission runs inside gluetun's network, so torrent traffic is shown on the gluetun row. Memory and SD writes: " + NO_MEMCG,
    "gridPos": {"x": 0, "y": y, "w": 24, "h": 12},
    "targets": [
        # cAdvisor gives the container's creation time; containers restarted at boot would look years old,
        # so never count from before the last boot.
        tgt(f'time() - ((max by (name, image) (container_start_time_seconds{{{C}}}) > scalar(node_boot_time_seconds{{{NODE}}}))'
            f' or (0 * max by (name, image) (container_start_time_seconds{{{C}}}) + scalar(node_boot_time_seconds{{{NODE}}})))',
            instant=True, ref="A", fmt="table"),
        tgt(f'100 * sum by (name) (rate(container_cpu_usage_seconds_total{{{C}}}[5m]))', instant=True, ref="B", fmt="table"),
        tgt(f'sum by (name) (container_memory_working_set_bytes{{{C}}}) > 0', instant=True, ref="C", fmt="table"),
        tgt(f'sum by (name) (rate(container_network_receive_bytes_total{{{CN}}}[5m]))', instant=True, ref="D", fmt="table"),
        tgt(f'sum by (name) (rate(container_network_transmit_bytes_total{{{CN}}}[5m]))', instant=True, ref="E", fmt="table"),
        tgt(f'sum by (name) (rate(container_fs_writes_bytes_total{{{C}}}[5m])) and on() (sum(container_memory_working_set_bytes{{{C}}}) > 0)', instant=True, ref="F", fmt="table"),
    ],
    "transformations": [
        {"id": "merge", "options": {}},
        {"id": "organize", "options": {
            "excludeByName": {"Time": True},
            "indexByName": {"name": 0, "Value #A": 1, "Value #B": 2, "Value #C": 3, "Value #D": 4, "Value #E": 5, "Value #F": 6, "image": 7},
            "renameByName": {"name": "Container", "image": "Image", "Value #A": "Up for", "Value #B": "CPU (% of 1 core)",
                             "Value #C": "Memory", "Value #D": "Net in", "Value #E": "Net out", "Value #F": "SD writes"}}},
        {"id": "sortBy", "options": {"sort": [{"field": "CPU (% of 1 core)", "desc": True}]}},
    ],
    "fieldConfig": {"defaults": {"custom": {"align": "auto", "cellOptions": {"type": "auto"}}}, "overrides": [
        col("Up for", "s", 1), col("CPU (% of 1 core)", "percent", 1, gauge=True, maxv=100),
        col("Memory", "bytes", 0, gauge=True, maxv=1.5e9), col("Net in", "Bps", 1), col("Net out", "Bps", 1),
        col("SD writes", "Bps", 1),
        {"matcher": {"id": "byRegexp", "options": "Memory|SD writes"}, "properties": [{"id": "noValue", "value": "n/a"}]}]},
    "options": {"showHeader": True, "cellHeight": "sm", "footer": {"show": False}},
})
y += 12
cont += [
    ts("CPU per container (% of one core)", [
        (f'100 * sum by (name) (rate(container_cpu_usage_seconds_total{{{C}}}[$__rate_interval]))', "{{name}}"),
    ], 0, y, unit="percent", minv=0, fill=0),
    ts("Memory per container", [
        (f'sum by (name) (container_memory_working_set_bytes{{{C}}}) > 0', "{{name}}"),
    ], 12, y, unit="bytes", minv=0, fill=0, desc=NO_MEMCG),
]
y += 8
cont += [
    ts("Network per container (in up / out down)", [
        (f'sum by (name) (rate(container_network_receive_bytes_total{{{CN}}}[$__rate_interval]))', "{{name}} in"),
        (f'sum by (name) (rate(container_network_transmit_bytes_total{{{CN}}}[$__rate_interval]))', "{{name}} out"),
    ], 0, y, unit="Bps", fill=0, overrides=[negative_y(".* out")],
       desc="Torrents show up as movies-downloader-bot-gluetun-1 (Transmission shares its network). node-exporter and the bot use the host network and are left out (see the Raspberry Pi dashboard)."),
    ts("SD card writes per container", [
        (f'sum by (name) (rate(container_fs_writes_bytes_total{{{C}}}[$__rate_interval])) and on() (sum(container_memory_working_set_bytes{{{C}}}) > 0)', "{{name}}"),
    ], 12, y, unit="Bps", minv=0, fill=0,
       desc="Who writes to the SD card. Writes to the media HDD are not counted here. " + NO_MEMCG),
]

OUT.mkdir(parents=True, exist_ok=True)
for name, d in [("pi-overview", dashboard("pi", "Raspberry Pi", pi, ["pi"], LINKS)),
                ("containers", dashboard("containers", "Containers", cont, ["pi"], LINKS))]:
    (OUT / f"{name}.json").write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    print(name, len(d["panels"]), "panels")
