"""Well-known event type constants.

Defined centrally so publishers and subscribers reference the same strings.
"""

# --- Input events (hardware → system) ------------------------------------

SWITCH_CHANGED = "input.switch.changed"
BUTTON_PRESSED = "input.button.pressed"
BUTTON_RELEASED = "input.button.released"
GO_BUTTON_PRESSED = "input.go_button.pressed"

# --- Output events (system → hardware / UI) ------------------------------

LED_STATE_CHANGED = "output.led.state_changed"
DISPLAY_UPDATED = "output.display.updated"
SCREEN_UPDATED = "output.screen.updated"

# --- System lifecycle events ---------------------------------------------

SYSTEM_STARTED = "system.started"
SHUTDOWN_REQUESTED = "system.shutdown.requested"
SHUTDOWN_INITIATED = "system.shutdown.initiated"

# --- App lifecycle events -------------------------------------------------

APP_LAUNCH_REQUESTED = "system.app.launch.requested"
APP_STARTED = "system.app.started"
APP_FINISHED = "system.app.finished"
APP_ERROR = "system.app.error"
