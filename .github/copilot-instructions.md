# B.O.S.S. v3 — Copilot Instruction Index

This file serves as a minimal index pointing to focused guidance documents
under `.github/instructions/`. Each topic is isolated for clarity.

> **IMPORTANT: Mandatory Virtual Environment**
> Always run Python inside the project-local `.venv`. All commands assume an active venv.

## Core Topics

- Architecture & Principles: `.github/instructions/architecture.md`
- Mini-App Authoring & Lifecycle: `.github/instructions/app_authoring.md`
- Hardware Abstraction & Parity: `.github/instructions/hardware.md`
- Event Bus & Logging: `.github/instructions/event_bus.md`
- Configuration & Secrets: `.github/instructions/configuration.md`
- NiceGUI UI Layer: `.github/instructions/ui.md`
- Testing Strategy: `.github/instructions/testing.md`
- Deployment: `.github/instructions/deployment.md`

## Quick Start

```powershell
cd BOSSv3
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m boss.main
```

Open `http://localhost:8080` in browser.

## When Adding New Functionality

- Update only the relevant instruction file.
- Keep cross-references minimal; single authoritative location per concept.
- After adding/modifying apps: run `python scripts/validate_manifests.py`.
- Before commits: ensure tests pass (`pytest`).
