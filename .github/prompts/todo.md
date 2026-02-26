BOSS Admin
- "App Config" card only applies to Countdown to event.  It can be removed as we should be able to set this in the App Management by updating the Manifest Config.

- the App Management bindings seems broken again.  changing app does not change the switch and manifest.

- The design is not responsive and does not function well on a small screen.

- there should be an indication if the Admin is offline.  

- there should not be a "back to BOSS" link on the Admin page because Admin should be used on a different device.



WiFi Configuration
- Message "Press any button to return.  this message is irrelevant and should be removed.

- message "WiFi management requires a Raspberry Pi with nmcli." is correct on Windows/Dev environemnt.  



Log error
  File "D:\dev\BOSSv3\src\boss\ui\dev_panel.py", line 213, in handle_key
    elif key.lower() == "r":
         ^^^^^^^^^
AttributeError: 'KeyboardKey' object has no attribute 'lower'
2026-02-26 19:23:43 [ERROR] nicegui: 'KeyboardKey' object has no attribute 'lower'
Traceback (most recent call last):
  File "D:\dev\BOSSv3\.venv\Lib\site-packages\nicegui\events.py", line 431, in handle_event
    result = cast(Callable[[EventT], Any], handler)(arguments)
  File "D:\dev\BOSSv3\src\boss\ui\dev_panel.py", line 213, in handle_key
    elif key.lower() == "r":
         ^^^^^^^^^

No App at....
Is there is no App configured for a specific number, then run app 0 "List All Apps", but with a message on the status bar "no app at ...."

Dev Mode
The dev panel should be directly below the screen.  Currently there is a large gap which forces scrolling to see the dev panel.
The screen can be a little smaller.
The buttons and LEDs represented on the dev Panel should match the colour of the Led / button.
When changing switches, the Display should update in real time.
