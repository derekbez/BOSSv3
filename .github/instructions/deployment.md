# Deployment

> **Full step-by-step setup guide:** [`deploy/PI_SETUP.md`](../../deploy/PI_SETUP.md)

## Target Platform

- Raspberry Pi 3B+ (or Pi 4 / Pi 5)
- Pi OS Desktop (64-bit) — Debian Trixie based
- HDMI display (1024×600 or similar)
- No keyboard/mouse — GPIO buttons and switches only

## Pi OS Setup (Summary)

1. Flash Pi OS Desktop (64-bit) via Raspberry Pi Imager — choose the Trixie-based image
2. In Imager OS Customisation: set hostname `boss3`, enable SSH, configure Wi-Fi
3. `sudo raspi-config`:
   - Boot → Desktop Autologin
   - Display → Disable Screen Blanking
   - Interface → Enable SPI and I2C
   - (Optional) Advanced → Switch to X11 if using `unclutter`

See `deploy/PI_SETUP.md` for complete walkthrough including secrets, kiosk, and troubleshooting.

## Systemd Services

### `deploy/boss.service`

Runs the BOSS NiceGUI server:

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

### `deploy/boss-kiosk.service`

Opens Chromium in kiosk mode:

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

## Deploy Script

`deploy/deploy.sh`:

```bash
#!/bin/bash
PI_HOST="${1:-boss}"
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
  . rpi@${PI_HOST}:/opt/boss/
ssh rpi@${PI_HOST} 'cd /opt/boss && .venv/bin/pip install -e ".[pi]" && sudo systemctl restart boss boss-kiosk'
```

## Secrets

Copy `secrets/secrets.sample.env` to `secrets/secrets.env` on the Pi and fill in API keys.
Never rsync secrets — manage them manually on the Pi.

## Rollback

If a deploy breaks:

```bash
ssh rpi@boss 'cd /opt/boss && git checkout HEAD~1 && sudo systemctl restart boss boss-kiosk'
```

Or keep a `backup/` directory and swap.
