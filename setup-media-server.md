# Media Server Setup Instructions

## Directory Structure
Create the following directories before starting:

```bash
mkdir -p jellyfin/{config,cache,transcodes}
mkdir -p media/{movies,tv,music}
```

## Configuration Notes

### Jellyfin
- **Web Interface**: http://your-pi-ip:8096
- **HTTPS**: Port 8920 (if SSL configured)
- **Auto-discovery**: UDP ports 7359 and 1900
- **Hardware Acceleration**: Uses `/dev/dri` for GPU transcoding on Raspberry Pi

### Kodi (Client Setup)
- Install Kodi on your viewing devices (TV, phone, tablet, computer)
- Add Jellyfin as a source using the Jellyfin for Kodi add-on
- Connect to: http://192.168.178.99:8096

## Important Setup Steps

1. **Static IP Configuration**: Ensure your Raspberry Pi 5 has static IP 192.168.178.99
2. **User Permissions**: Both services run as user 1000:1000 - ensure media files are accessible
3. **Media Location**: Place your media files in the `./media/` directory
4. **Hardware Acceleration**: GPU access configured for both services via `/dev/dri`

## Raspberry Pi 5 Network Setup

To set static IP 192.168.178.99, edit `/etc/dhcpcd.conf`:

```bash
sudo nano /etc/dhcpcd.conf
```

Add these lines (adjust gateway/DNS as needed):
```
interface eth0
static ip_address=192.168.178.99/24
static routers=192.168.178.1
static domain_name_servers=192.168.178.1 8.8.8.8
```

Then restart networking:
```bash
sudo systemctl restart dhcpcd
```

## Starting the Services

```bash
docker-compose -f docker-compose-media.yml up -d
```

## Network Access
Both services are configured for local network access. Jellyfin will be discoverable by clients on your network.