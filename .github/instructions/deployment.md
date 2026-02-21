# Deployment

> **Full step-by-step setup guide:** [`deploy/PI_SETUP.md`](../../deploy/PI_SETUP.md)

## Target Platform

- Raspberry Pi 4 or 5
- Pi OS Desktop (64-bit) — Debian Trixie based
- HDMI display (1024×600 or similar)
- No keyboard/mouse — GPIO buttons and switches only

## Pi OS Setup (Summary)

1. Flash Pi OS Desktop (64-bit) via Raspberry Pi Imager — choose the Trixie-based image
2. In Imager OS Customisation: set hostname `boss`, enable SSH, configure Wi-Fi
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
User=pi
WorkingDirectory=/opt/boss
ExecStart=/opt/boss/.venv/bin/python -m boss.main
Restart=on-failure
RestartSec=5

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
User=pi
Environment=DISPLAY=:0
ExecStartPre=/bin/sleep 3
ExecStart=/usr/bin/chromium-browser --kiosk --noerrdialogs --disable-infobars --incognito http://localhost:8080
Restart=on-failure

[Install]
WantedBy=graphical.target
```

## Deploy Script

`deploy/deploy.sh`:

```bash
#!/bin/bash
PI_HOST="${1:-boss}"
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
  . pi@${PI_HOST}:/opt/boss/
ssh pi@${PI_HOST} 'cd /opt/boss && .venv/bin/pip install -e ".[pi]" && sudo systemctl restart boss boss-kiosk'
```

## Secrets

Copy `secrets/secrets.sample.env` to `secrets/secrets.env` on the Pi and fill in API keys.
Never rsync secrets — manage them manually on the Pi.

## Rollback

If a deploy breaks:

```bash
ssh pi@boss 'cd /opt/boss && git checkout HEAD~1 && sudo systemctl restart boss boss-kiosk'
```

Or keep a `backup/` directory and swap.
