"""App runner — executes a single mini-app in a daemon thread with timeout."""

from __future__ import annotations

import importlib.util
import logging
import sys
import threading
from pathlib import Path
from typing import Any

from boss.core.app_api import AppAPI
from boss.core.event_bus import EventBus
from boss.core import events
from boss.core.models.manifest import AppManifest

_log = logging.getLogger(__name__)


class AppRunner:
    """Runs one mini-app at a time in a daemon thread.

    Lifecycle events (``system.app.started``, ``system.app.finished``,
    ``system.app.error``) are published on the event bus.

    Args:
        event_bus: The global async event bus.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._app_name: str | None = None
        self._timer: threading.Timer | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def run_app(
        self,
        app_name: str,
        app_dir: Path,
        manifest: AppManifest,
        api: AppAPI,
    ) -> None:
        """Launch *app_name* in a daemon thread.

        If an app is already running, it is stopped first (cooperative).
        Blocks until the old app has exited (or the join timeout expires)
        to guarantee sequential execution.
        """
        if self.is_running:
            _log.warning("Stopping current app %s before launching %s", self._app_name, app_name)
            self.stop()

            # Double-check: if the old thread is still alive after stop(),
            # wait a little longer.  This prevents two app threads from
            # overlapping.
            if self._thread is not None and self._thread.is_alive():
                _log.warning(
                    "Old app thread still alive after stop() — waiting 2s more"
                )
                self._thread.join(timeout=2.0)
                if self._thread.is_alive():
                    _log.error(
                        "App %s refused to stop — launching %s anyway (old thread is daemon)",
                        self._app_name,
                        app_name,
                    )

        self._app_name = app_name
        self._stop_event = threading.Event()

        self._thread = threading.Thread(
            target=self._run_wrapper,
            args=(app_name, app_dir, manifest, api, self._stop_event),
            name=f"app-{app_name}",
            daemon=True,
        )
        self._thread.start()

        # Start timeout monitor
        timeout = manifest.timeout_seconds
        self._timer = threading.Timer(timeout, self._on_timeout, args=(app_name,))
        self._timer.daemon = True
        self._timer.name = f"timeout-{app_name}"
        self._timer.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Cooperatively stop the running app."""
        if not self.is_running:
            return
        _log.info("Requesting stop for app %s", self._app_name)
        self._cancel_timer()
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                _log.warning("App %s did not stop within %.1fs", self._app_name, timeout)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_wrapper(
        self,
        app_name: str,
        app_dir: Path,
        manifest: AppManifest,
        api: AppAPI,
        stop_event: threading.Event,
    ) -> None:
        """Thread target: import & invoke the app's ``run()`` function."""
        self._event_bus.publish_threadsafe(
            events.APP_STARTED,
            {
                "app_name": app_name,
                "display_name": manifest.effective_display_name,
                "switch_value": 0,
            },
        )
        try:
            entry = app_dir / manifest.entry_point
            run_func = self._load_run_func(entry)
            run_func(stop_event, api)
            reason = "timeout" if stop_event.is_set() else "normal"
            self._event_bus.publish_threadsafe(
                events.APP_FINISHED,
                {"app_name": app_name, "reason": reason},
            )
        except Exception as exc:
            _log.exception("App %s raised an exception", app_name)
            self._event_bus.publish_threadsafe(
                events.APP_ERROR,
                {"app_name": app_name, "error": str(exc)},
            )
        finally:
            self._cancel_timer()
            api._cleanup()

    def _on_timeout(self, app_name: str) -> None:
        if self._app_name == app_name and self.is_running:
            _log.warning("App %s hit timeout — setting stop_event", app_name)
            self._stop_event.set()

    def _cancel_timer(self) -> None:
        """Cancel the running timeout timer, if any."""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    @staticmethod
    def _load_run_func(entry_path: Path) -> Any:
        """Dynamically import the app module and return its ``run`` function.

        Before loading, any previously cached ``boss.apps.*`` modules are
        evicted from ``sys.modules`` so that helper libraries (e.g.
        ``boss.apps._lib``) are also re-read from disk.  This means
        developers can edit app code **and** shared helpers and see
        changes take effect on the next Go-button press — no server
        restart required.
        """
        # Evict cached app/helper modules so edits are picked up.
        stale = [k for k in sys.modules if k.startswith("boss.apps.")]
        for key in stale:
            del sys.modules[key]

        spec = importlib.util.spec_from_file_location("_boss_app_module", entry_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load app module: {entry_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        run_func = getattr(module, "run", None)
        if run_func is None:
            raise AttributeError(f"App module {entry_path} has no 'run' function")
        return run_func
