# Raspberry Pi Setup Guide — B.O.S.S. v3

Step-by-step instructions for getting a Raspberry Pi ready to run BOSS.

---

## 1. Flash the SD Card

### What you need
- Raspberry Pi 3B+ (or Pi 4 / Pi 5)
- microSD card (16 GB minimum, 32 GB recommended)
- A PC with [Raspberry Pi Imager](https://www.raspberrypi.com/software/) installed
- An HDMI display (1024×600 or similar) connected to the Pi
- Ethernet cable **or** Wi-Fi credentials

### Flash with Raspberry Pi Imager

1. Open **Raspberry Pi Imager** on your PC.
2. Click **Choose Device** → select your Pi model (Pi 3 / Pi 4 / Pi 5).
3. Click **Choose OS** → **Raspberry Pi OS (other)** → **Raspberry Pi OS (64-bit) with desktop**.
   - This gives you the latest Debian Trixie-based image with the desktop environment.
   - Do **not** choose "Lite" — BOSS needs a desktop for the kiosk Chromium window.
4. Click **Choose Storage** → select your microSD card.
5. Click **Next**. When prompted "Would you like to apply OS customisation settings?", click **Edit Settings**.

### OS Customisation Settings

In the **General** tab:
- **Set hostname**: `boss3`
- **Set username and password**: username `rpi`, pick a strong password
- **Configure wireless LAN**: enter your Wi-Fi SSID and password (skip if using Ethernet)
- **Set locale settings**: your timezone and keyboard layout

In the **Services** tab:
- **Enable SSH**: tick the box
- **Use password authentication** (or paste your public key for key-based auth)

Click **Save**, then **Yes** to apply and write the image.

### Boot the Pi

1. Insert the flashed SD card into the Pi.
2. Connect HDMI, Ethernet (if not using Wi-Fi), and power.
3. Wait 2–3 minutes for the first boot to complete.
4. The Pi desktop should appear on the HDMI display.

---

## 2. Connect via SSH

From your development PC:

```bash
ssh rpi@boss3.local
```

If `boss3.local` doesn't resolve, find the Pi's IP address from your router's DHCP table and use:

```bash
ssh rpi@<IP_ADDRESS>
```

Accept the host key fingerprint when prompted. Enter the password you set in Imager.

### (Optional) Set up key-based SSH

From your PC:

```bash
ssh-copy-id rpi@boss3.local
```

This lets you connect without typing a password every time.

---

## 3. System Configuration

Once connected via SSH, run `raspi-config`:

```bash
sudo raspi-config
```

Apply these settings:

| Menu Path | Setting |
|-----------|---------|
| **System Options → Boot / Auto Login** | Desktop Autologin (boot to desktop, logged in as `rpi`) |
| **Display Options → Screen Blanking** | **Disable** (prevents the screen going black after idle) |
| **Advanced Options → Wayland** | Switch to **X11** if you plan to use `unclutter` to hide the mouse cursor |
| **Interface Options → SPI** | **Disable** (SPI uses GPIO8 which BOSS needs for its switch multiplexer; enabling SPI makes the pin "busy" and prevents the app from starting; only enable if you have other SPI devices and rewire the mux to different GPIOs) |
| **Interface Options → I2C** | **Enable** (needed for TM1637 display) |

Select **Finish** and reboot when prompted:

```bash
sudo reboot
```

### System updates

After reboot, reconnect via SSH and update the system:

```bash
sudo apt update && sudo apt upgrade -y
```

### Install required system packages

```bash
sudo apt install -y git python3-venv python3-dev chromium unclutter
```

| Package | Why |
|---------|-----|
| `git` | Clone the BOSS repo |
| `python3-venv` | Create isolated Python virtual environments |
| `python3-dev` | Build native Python extensions (e.g. lgpio) |
| `chromium` | Kiosk browser for the BOSS UI (called `chromium-browser` on older Pi OS) |
| `unclutter` | Hides the mouse cursor after inactivity |

---

## 4. Clone the Project

```bash
sudo mkdir -p /opt/boss
sudo chown rpi:rpi /opt/boss
git clone https://github.com/derekbez/BOSSv3.git /opt/boss
```

### Create the virtual environment and install

```bash
cd /opt/boss
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[pi]"
```

The `--system-site-packages` flag lets the venv see system-installed libraries (e.g. `lgpio`).
The `[pi]` extra installs Raspberry Pi hardware libraries (`gpiozero`, `rpi-lgpio`, `python-tm1637`).

> **Python version:** The Pi ships with Python 3.13. The project requires Python 3.11+, so this works out of the box — no need to install a different Python.

### Verify the install

```bash
python -c "import boss; print('BOSS OK')"
```

---

## 5. Configure Secrets

API keys are stored in a secrets file on the Pi — **never committed to git**.

```bash
cp /opt/boss/secrets/secrets.sample.env /opt/boss/secrets/secrets.env
nano /opt/boss/secrets/secrets.env
```

Fill in the keys your apps need:

```dotenv
BOSS_APP_AVIATIONSTACK_API_KEY=your_key_here
BOSS_APP_EBIRD_API_KEY=your_key_here
BOSS_APP_IPGEO_API_KEY=your_key_here
BOSS_APP_LASTFM_API_KEY=your_key_here
BOSS_APP_NASA_API_KEY=your_key_here
BOSS_APP_NEWSDATA_API_KEY=your_key_here
BOSS_APP_SERPAPI_API_KEY=your_key_here
BOSS_APP_WORDNIK_API_KEY=your_key_here
BOSS_APP_WORLDTIDES_API_KEY=your_key_here
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

---

## 6. Test Run

Before setting up auto-start, verify BOSS runs:

```bash
cd /opt/boss
source .venv/bin/activate
python -m boss.main
```

On the Pi's HDMI display, open Chromium and navigate to `http://localhost:8080`. You should see the BOSS UI.

Press `Ctrl+C` in the SSH terminal to stop.

---

## 7. Install Systemd Services

Two services work together:
- **boss.service** — runs the BOSS NiceGUI server
- **boss-kiosk.service** — opens Chromium in fullscreen kiosk mode

### Create the service files

```bash
sudo cp /opt/boss/deploy/boss.service /etc/systemd/system/
sudo cp /opt/boss/deploy/boss-kiosk.service /etc/systemd/system/
sudo systemctl daemon-reload
```

> **Note:** If the `deploy/` directory doesn't have the service files yet,
> create them manually — see the templates below.

<details>
<summary><b>boss.service</b></summary>

```bash
sudo nano /etc/systemd/system/boss.service
```

```ini
[Unit]
Description=BOSS Mini-App Platform
After=network-online.target graphical.target
Wants=network-online.target

[Service]
Type=simple
User=rpi
WorkingDirectory=/opt/boss
ExecStart=/opt/boss/.venv/bin/python -m boss.main
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-/opt/boss/secrets/secrets.env
SupplementaryGroups=gpio
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/boss/logs /opt/boss/secrets
MemoryMax=512M
CPUQuota=80%

[Install]
WantedBy=graphical.target
```

</details>

<details>
<summary><b>boss-kiosk.service</b></summary>

```bash
sudo nano /etc/systemd/system/boss-kiosk.service
```

```ini
[Unit]
Description=BOSS Kiosk Browser
After=boss.service
Requires=boss.service

[Service]
Type=simple
User=rpi
Environment=DISPLAY=:0
ExecStartPre=/bin/sleep 5
ExecStart=/usr/bin/chromium --kiosk --noerrdialogs --disable-infobars --disable-session-crashed-bubble --incognito http://localhost:8080
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
```

</details>

### Enable and start

```bash
sudo systemctl enable boss boss-kiosk
sudo systemctl start boss
sudo systemctl start boss-kiosk
```

### Check status

```bash
sudo systemctl status boss
sudo systemctl status boss-kiosk
journalctl -u boss -f          # live log stream
```

---

## 8. Hide the Mouse Cursor

`unclutter` hides the cursor after a few seconds of inactivity — ideal for kiosk mode.

Add it to the Pi's autostart:

```bash
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/unclutter.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Unclutter
Exec=unclutter -idle 1 -root
EOF
```

This takes effect on next reboot.

---

## 9. Prevent Screen Blanking (Belt and Braces)

`raspi-config` should have disabled blanking, but to be safe:

```bash
# Disable DPMS (Display Power Management Signaling)
sudo bash -c 'cat > /etc/xdg/autostart/disable-dpms.desktop << EOF
[Desktop Entry]
Type=Application
Name=Disable DPMS
Exec=xset s off -dpms
EOF'
```

---

## 10. Deploying Updates

From your **development PC** (Windows/Mac), push code updates to the Pi:

### Option A: Git pull on the Pi

```bash
ssh rpi@boss3.local
cd /opt/boss
git pull
source .venv/bin/activate
pip install -e ".[pi]"
sudo systemctl restart boss boss-kiosk
```

### Option B: rsync deploy script

From your dev machine (requires `rsync` — available in WSL or Git Bash on Windows):

```bash
./deploy/deploy.sh boss3.local
```

The script syncs code and restarts services:

```bash
#!/bin/bash
PI_HOST="${1:-boss3.local}"
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
  --exclude 'secrets/secrets.env' --exclude 'logs/' \
  . rpi@${PI_HOST}:/opt/boss/
ssh rpi@${PI_HOST} 'cd /opt/boss && .venv/bin/pip install -e ".[pi]" && sudo systemctl restart boss boss-kiosk'
```

> **Important:** Secrets are excluded from rsync. Manage them manually on the Pi.

---

## Troubleshooting

### BOSS won't start
```bash
journalctl -u boss --no-pager -n 50    # last 50 log lines
```

### Chromium won't open / shows crash dialog
```bash
# Kill any leftover Chromium processes
pkill -f chromium
sudo systemctl restart boss-kiosk
```

### Can't find the Pi on the network
- Check the Pi is powered on and connected (Ethernet LED / Wi-Fi)
- Try `ping boss3.local` — if it fails, check your router for the Pi's IP
- On Windows, mDNS (`.local`) requires Bonjour. Try the raw IP instead.

### GPIO permission errors
```bash
# Add rpi to the gpio group (usually done by default)
sudo usermod -aG gpio rpi
# Reboot for group changes to take effect
sudo reboot
```

### “GPIO busy” error at startup
If `journalctl -u boss` shows a traceback ending with `lgpio.error: 'GPIO busy'`,
it means something else is holding the GPIO device (often a previous BOSS
process that didn’t exit cleanly). systemd will repeatedly restart the service,
so the kiosk browser just flashes “site can’t be reached”.

Fix the problem by stopping the service and freeing the pins (or simply
reboot the Pi):

```bash
sudo systemctl stop boss
sudo pkill -f boss.main      # kill any stray Python instance using gpio
# or, more brutally:
sudo reboot
```

If the error persists after reboot, identify the culprit with:

```bash
sudo lsof /dev/gpiomem
```

then kill the offending process. Once the pins are free, `sudo
systemctl start boss` should bring the UI back online.

### Display not detected / wrong resolution
```bash
# Check connected displays
xrandr
# Force a resolution if needed (add to /boot/firmware/config.txt)
# hdmi_group=2
# hdmi_mode=87
# hdmi_cvt=1024 600 60
```

### Updating Python dependencies
```bash
cd /opt/boss
source .venv/bin/activate
pip install -e ".[pi]" --upgrade
sudo systemctl restart boss
```

---

## Quick Reference

| Task | Command |
|------|---------|
| SSH into Pi | `ssh rpi@boss3.local` |
| Start BOSS | `sudo systemctl start boss boss-kiosk` |
| Stop BOSS | `sudo systemctl stop boss-kiosk boss` |
| Restart BOSS | `sudo systemctl restart boss boss-kiosk` |
| View logs (live) | `journalctl -u boss -f` |
| View logs (file) | `cat /opt/boss/logs/boss.log` |
| Edit secrets | `nano /opt/boss/secrets/secrets.env` |
| Update code | `cd /opt/boss && git pull && .venv/bin/pip install -e ".[pi]"` |
| Reboot Pi | `sudo reboot` |
| Shutdown Pi | `sudo shutdown -h now` |
