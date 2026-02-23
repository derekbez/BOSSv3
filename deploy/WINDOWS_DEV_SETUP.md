# Windows Development Setup — B.O.S.S. v3

This guide covers exactly what is required to run BOSS locally on Windows,
including how to start, stop, and restart the app in dev mode.

---

## 1) Prerequisites

- Windows 10/11
- Python 3.11+
- Git
- PowerShell

Check versions:

```powershell
python --version
git --version
```

---

## 2) Clone and create venv

```powershell
git clone https://github.com/derekbez/BOSSv3.git
cd BOSSv3
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

> BOSS expects the project-local `.venv` to be active for development commands.
pytho
---

## 3) Run the app (dev environment)

```powershell
.\.venv\Scripts\Activate.ps1
python -m boss.main
```

If activation is blocked with `PSSecurityException` (`running scripts is disabled`),
use one of these options:

```powershell
# temporary for current PowerShell session only (recommended)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Or skip activation entirely and call the venv Python directly:

```powershell
.\.venv\Scripts\python.exe -m boss.main
```

Open:
- http://localhost:8080

What to expect in Windows dev mode:
- Uses mock hardware backend (not GPIO)
- Shows on-screen **Dev Panel** with simulated switches/buttons/Go control

---

## 4) Stop the app

### If running in the foreground terminal
Press:
- `Ctrl+C`

### If running in the background / orphaned process
Kill whatever is listening on port `8080`:

```powershell
$ids = netstat -ano |
  Select-String ":8080" |
  Select-String "LISTENING" |
  ForEach-Object { ($_ -split '\s+')[-1] } |
  Select-Object -Unique

foreach ($procId in $ids) {
  taskkill /F /PID $procId
}
```

Verify it is stopped:

```powershell
netstat -ano | Select-String ":8080" | Select-String "LISTENING"
```

No output means it is stopped.

---

## 5) Restart the app

```powershell
# stop stale process first (if needed)
$ids = netstat -ano |
  Select-String ":8080" |
  Select-String "LISTENING" |
  ForEach-Object { ($_ -split '\s+')[-1] } |
  Select-Object -Unique
foreach ($procId in $ids) { taskkill /F /PID $procId }

# run again
.\.venv\Scripts\Activate.ps1
python -m boss.main
```

---

## 6) Optional: local secrets for network apps

Some apps require API keys. If unset, startup warnings are expected.

Create local secrets file:

```powershell
copy .\secrets\secrets.sample.env .\secrets\secrets.env
notepad .\secrets\secrets.env
```

Add any keys you want to test. Missing keys only affect those specific apps.

---

## 7) Troubleshooting

### Port 8080 already in use
Use the stop commands above, then run again.

### Dev panel not visible
The panel only appears when mock hardware is in use (Windows/macOS or
when `dev_mode` is `True`).

Because the screen container is sized to the viewport height, the panel
may sit just below the fold on tall monitors; use the scrollbar or mouse
wheel to scroll the page.  On real kiosks the scrollbar is hidden to keep
the UI clean.

### Import errors
Ensure `.venv` is active and dependencies installed:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

If activation is blocked by execution policy, run:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### Run tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
```
